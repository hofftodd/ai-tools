#!/usr/bin/env python3
"""Largest context window that keeps a GGUF fully resident in a device's VRAM.

llama-config passes --n-gpu-layers 99, which disables llama.cpp's own auto-fit.
When weights + KV cache + compute buffers exceed the card, llama.cpp does not
fail -- it spills into host RAM over PCIe, measured at roughly a 10x throughput
loss. This estimates the ceiling so the generated config stays under it.

    VRAM ~= weights + companions + kv_bytes_per_token * ctx + compute

Validated against two measured loads on a 32 GB Radeon AI PRO R9700
(Qwen3-Coder-30B-A3B): estimates ran +2.7% and +1.2% versus observed usage, i.e.
slightly conservative, which is the direction that keeps you off the cliff.

Prints the fitted context (multiple of 4096), or the model's trained context if
that is smaller. Prints 0 if the weights alone do not fit.
"""
import argparse, os, struct, sys

_SCALAR = {0: 'B', 1: 'b', 2: 'H', 3: 'h', 4: 'I', 5: 'i',
           6: 'f', 7: '?', 10: 'Q', 11: 'q', 12: 'd'}


def read_header(path):
    """Minimal GGUF key/value reader -- metadata only, never the tensor data."""
    with open(path, 'rb') as f:
        if f.read(4) != b'GGUF':
            raise ValueError(f'not a GGUF file: {path}')
        struct.unpack('<I', f.read(4))                      # version
        struct.unpack('<Q', f.read(8))                      # tensor count
        n_kv = struct.unpack('<Q', f.read(8))[0]

        def rstr():
            n = struct.unpack('<Q', f.read(8))[0]
            return f.read(n).decode('utf-8', 'replace')

        def rval(t):
            if t == 8:
                return rstr()
            if t == 9:                                       # array
                et = struct.unpack('<I', f.read(4))[0]
                n = struct.unpack('<Q', f.read(8))[0]
                return [rval(et) for _ in range(n)]
            fmt = _SCALAR[t]
            return struct.unpack('<' + fmt, f.read(struct.calcsize(fmt)))[0]

        kv = {}
        for _ in range(n_kv):
            k = rstr()
            t = struct.unpack('<I', f.read(4))[0]
            try:
                kv[k] = rval(t)
            except Exception:
                break                                        # truncated; use what we have
        return kv


def kv_bytes_per_token(kv, bytes_per_elem, window_tokens):
    """KV-cache bytes per token of context.

    Handles three shapes seen in practice:
      * plain GQA -- scalar head_count_kv
      * sliding-window (Gemma) -- per-layer head_count_kv plus a
        sliding_window_pattern; windowed layers hold only `sliding_window`
        tokens no matter how large the context, so they cost ~nothing per token
      * hybrid SSM (Nemotron) -- layers with 0 KV heads are Mamba blocks whose
        state is constant per sequence, not per token
    """
    arch = kv.get('general.architecture', '')

    def g(*names, default=None):
        for n in names:
            for key in (f'{arch}.{n}', n):
                if key in kv:
                    return kv[key]
        return default

    n_layer = g('block_count')
    hkv = g('attention.head_count_kv')
    k_len = g('attention.key_length')
    v_len = g('attention.value_length', default=k_len)
    if k_len is None:                                        # derive from embedding width
        emb, n_head = g('embedding_length'), g('attention.head_count')
        if emb and isinstance(n_head, int) and n_head:
            k_len = v_len = emb // n_head
    if not (n_layer and hkv is not None and k_len):
        return None, None

    k_swa = g('attention.key_length_swa', default=k_len)
    v_swa = g('attention.value_length_swa', default=v_len)
    swa_pattern = g('attention.sliding_window_pattern')
    swa_window = g('attention.sliding_window')

    per_layer = hkv if isinstance(hkv, list) else [hkv] * n_layer
    per_token = 0.0       # elements per token of context
    fixed = 0.0           # elements independent of context (windowed layers)
    for i in range(min(n_layer, len(per_layer))):
        heads = per_layer[i]
        if not heads:                                        # SSM / non-attention layer
            continue
        windowed = bool(swa_pattern[i]) if (isinstance(swa_pattern, list)
                                            and i < len(swa_pattern)) else False
        if windowed and swa_window:
            fixed += heads * (k_swa + v_swa) * min(swa_window, window_tokens)
        else:
            per_token += heads * (k_len + v_len)
    return per_token * bytes_per_elem, fixed * bytes_per_elem


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('model')
    ap.add_argument('--vram-mib', type=int, required=True)
    ap.add_argument('--margin-mib', type=int, default=2048)
    ap.add_argument('--compute-mib', type=int, default=512)
    ap.add_argument('--kv-bytes-per-elem', type=float, default=1.0625)  # q8_0
    ap.add_argument('--companion', action='append', default=[],
                    help='mmproj / MTP draft head loaded alongside the model')
    ap.add_argument('--max-ctx', type=int, default=0, help='hard cap (0 = trained ctx)')
    args = ap.parse_args()

    MiB = 2 ** 20
    try:
        kv = read_header(args.model)
    except Exception as e:
        print(f'gguf-fit: {e}', file=sys.stderr)
        return 1

    weights = os.path.getsize(args.model)
    base = os.path.basename(args.model)
    if '-of-' in base:                                       # sum every shard of the set
        stem = base.rsplit('-', 3)[0]
        d = os.path.dirname(args.model)
        weights = sum(os.path.getsize(os.path.join(d, f)) for f in os.listdir(d)
                      if f.startswith(stem) and f.endswith('.gguf') and '-of-' in f)
    for c in args.companion:
        if c and os.path.exists(c):
            weights += os.path.getsize(c)

    trained = kv.get(f"{kv.get('general.architecture','')}.context_length") or 0
    cap = args.max_ctx or trained or 1 << 20

    per_tok, fixed = kv_bytes_per_token(kv, args.kv_bytes_per_elem, cap)
    if per_tok is None:
        print(0)                                             # unknown shape: caller falls back
        return 0

    budget = (args.vram_mib - args.margin_mib - args.compute_mib) * MiB \
        - weights - (fixed or 0)
    if budget <= 0:
        print(0)
        return 0
    ctx = int(budget / per_tok) if per_tok > 0 else cap
    ctx = min(ctx, cap)
    print(max(0, (ctx // 4096) * 4096))
    return 0


if __name__ == '__main__':
    sys.exit(main())
