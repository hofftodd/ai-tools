# llama-config

Generator that turns the GGUFs under `~/models/` into a [llama-swap](https://github.com/mostlygeek/llama-swap)
config and repoints every client (opencode, pi, oh-my-pi, Claude Code) at the
single llama-swap endpoint.

llama-swap is one proxy in front of `llama-server`: it reads the `model` field on
each request, starts the right backend on demand, and unloads idle ones after a
TTL. So you no longer choose *which servers to run* — every model is always
addressable by name and RAM is reclaimed automatically. What you pick here is
which models stay **resident** (pinned hot, never unloaded).

> **History:** llama-config used to run one `llama-server@<alias>.service` systemd
> instance per model with sticky ports. That approach forced manual RAM juggling
> (only ~2 models fit at once) and needed `ccr` to translate for Claude Code.
> It's now a config *generator* for llama-swap. See git history for the old flow;
> the per-model `~/.config/llama-server/instances/*.env` files are left in place
> as a rollback path.

## Architecture

```
clients ──▶ llama-swap :8080 (0.0.0.0, LAN)  ──▶ llama-server backends :5800+ (127.0.0.1)
  opencode / pi / omp  → /v1/chat/completions        started on demand, TTL-unloaded
  Claude Code          → /v1/messages  (native)      resident group stays hot
```

Because `llama-server` (build ≥ ~10000) answers the Anthropic Messages API
(`/v1/messages`) natively, **Claude Code talks to llama-swap directly — no
claude-code-router.**

## Usage

```bash
llama-config                          # regenerate, keeping the current resident set
llama-config ornith-35b gpt-oss-20b   # pin these two resident, regenerate everything
```

On each run it: discovers models, writes `~/.config/llama-swap/config.yaml`,
rewrites the client configs (backing up the old ones to `*.bak`), writes the
`claude-local` wrapper, restarts the `llama-swap` systemd user service, and
health-checks `http://127.0.0.1:8080/v1/models`.

The resident set defaults to CLI args; with no args it reads the existing
`groups.resident.members` from `config.yaml` (needs `yq`), else empty.

## What it writes

- **`~/.config/llama-swap/config.yaml`** — one `models:` entry per GGUF, a
  shared `macros.server` command, `ttl: 0` for resident models (else 900s), a
  non-exclusive persistent `groups.resident` that keeps the pinned models
  co-loaded, and a `hooks.on_startup.preload` for them. Per-model extras: models
  with MTP weights get `--spec-type draft-mtp` (self-speculative decode) — baked
  into the GGUF for Ornith, or as a sibling `mtp-*.gguf` head passed with
  `--model-draft` for Qwen3.8; vision models get `--mmproj`; models needing a
  forked llama.cpp (e.g. Bonsai ternary) are emitted `unlisted: true` so they're
  hidden from clients until buildable.
  Per-model `--device` and `--ctx-size` come from
  `~/.config/llama-config/models.conf` (see below).
- **`~/.config/opencode/opencode.json`** — one `llama-<id>` provider per model,
  all pointing at `http://127.0.0.1:8080/v1`; top-level `model` / `small_model`
  set to the resident main / small pick. Non-provider keys preserved.
- **`~/.pi/agent/models.json`** / **`~/.omp/agent/models.yml`** — same, with
  per-family `compat.thinkingFormat` and `input` (text, or text+image with mmproj).
- **`~/.local/bin/claude-local`** — wrapper that runs `claude` with
  `ANTHROPIC_BASE_URL=http://127.0.0.1:8080`, `ANTHROPIC_MODEL=<resident main>`,
  `ANTHROPIC_SMALL_FAST_MODEL=<resident small>`. Replaces `ccr code`.
- **`~/.config/llama-server/examples/`** — LAN-IP copies of the opencode / pi /
  omp configs plus a `claude-code.env` for driving Claude Code from another host.

Multi-quant families are disambiguated by filename (e.g.
`gemma-4-26b-a4b-it-ud-q4_k_m`); single-file families keep the short dir alias
(`ornith-35b`). Projector files (`*mmproj*.gguf`), MTP draft heads
(`mtp-*.gguf`), and non-first shards are never listed as models.

## Per-model overrides (`~/.config/llama-config/models.conf`)

Seeded on first run. Whitespace-separated, one line per model:

```
# <alias>                            <device>  <ctx>    [extra llama-server flags...]
qwen3-coder-30b-a3b-instruct-q4_k_m  egpu      -        --parallel 1
gpt-oss-20b                          igpu      -
qwen3.8-27b                          Vulkan1   98304
```

- **device** — `egpu` (first discrete/external GPU), `igpu` (integrated),
  `auto`, or a raw backend id (`Vulkan0` / `Vulkan1`). Unknown ids are rejected
  rather than passed through to a command that would fail at load. Models with
  no entry get no `--device` flag at all, leaving llama.cpp's own choice intact.
- **ctx** — overrides `LLAMA_CTX` for this model, and propagates to the
  `contextWindow` / `limit.context` the generated client configs advertise.
- Anything after the third field is appended to that model's command verbatim.

Use `-` to keep the default for either field — for `ctx` that means accepting the computed fit.

Device roles are detected by matching RADV's APU codenames (`LLAMA_IGPU_MATCH`)
against `llama-server --list-devices`; llama-config prints what it resolved on
every run.

### Context is fitted to the card

Context size is computed per model rather than fixed, because llama-config
passes `--n-gpu-layers 99`, which disables llama.cpp's own auto-fit. Over
budget, llama.cpp does not fail -- it silently spills into host RAM over PCIe.
Measured on a 32 GB Radeon AI PRO R9700: **~134 tok/s resident vs ~12 tok/s
spilled**, same model, same card, context the only difference.

`gguf-fit.py` reads each GGUF's header and solves

```
weights + companions + kv_bytes_per_token * ctx + compute  <=  VRAM - margin
```

for `ctx`, rounded down to a multiple of 4096 and capped at the model's trained
context. Companions (`mmproj`, MTP draft head) and every shard of a multi-shard
set count against the budget. It handles three KV shapes: plain GQA, Gemma-style
sliding-window layers (which hold only `sliding_window` tokens regardless of
context, so they cost almost nothing per token), and Nemotron-style hybrids
where SSM layers carry no per-token KV at all.

Validated against two measured loads: estimates came in +2.7% and +1.2% over
observed usage -- conservative, which is the direction that keeps you off the
cliff. Note that the `mem_info_vram_used` / `mem_info_gtt_used` sysfs counters
lag badly and read high even when a model is fully resident; throughput is the
reliable signal.

The target is whichever card the model will actually land on -- the pinned
device, or the discrete GPU llama.cpp prefers on its own. Each generated entry
records which rule applied:

```yaml
  qwen3-coder-30b-a3b-instruct-q4_k_m:
    # fitted to Vulkan1 (32624 MiB, 2048 MiB margin)
    cmd: "${server} --model ... --ctx-size 245760 --alias ... --device Vulkan1 --parallel 1"
  qwen3-coder-next:
    # DOES NOT FIT on Vulkan1 (32624 MiB) - will spill to host RAM
```

Models too large for the target keep `LLAMA_CTX` and are reported on stderr,
naming the other card when the model would fit there instead.

Splitting one model across both GPUs (`--split-mode layer` over an eGPU + iGPU)
sends per-layer traffic across PCIe and lands in the same slow regime -- pin one
model per device instead.

## Requirements

- `llama-swap` on `PATH` (release binary → `~/.local/bin/llama-swap`) and a
  `~/.config/systemd/user/llama-swap.service` unit listening on `0.0.0.0:8080`.
- `llama-server` at `~/.local/bin/llama-server` (build new enough for
  `/v1/messages` and `--spec-type`).
- `jq` on `PATH`; `yq` for the omp config and reading the resident set.
- `python3` for `gguf-fit.py` (GGUF header parsing; stdlib only).
- GGUFs organized as `~/models/<family-dir>/<file>.gguf`.

## Claude Code (no ccr)

```bash
claude-local        # launches Claude Code against your local models
```

Main tasks route to the resident main model, small/fast tasks to the resident
small model. Switch models in-session with Claude Code's `/model` command using
any listed model ID.

## Thinking-format detection (pi/omp)

| Alias contains | thinkingFormat |
| --- | --- |
| `qwen` / `ornith` | `qwen-chat-template` |
| `deepseek` | `deepseek` |
| `glm` / `zai` / `chatglm` | `zai` |
| anything else | omitted |

## Environment overrides

| Variable | Default |
| --- | --- |
| `LLAMA_MODELS_ROOT` | `~/models` |
| `LLAMA_SWAP_CONFIG` | `~/.config/llama-swap/config.yaml` |
| `LLAMA_SERVER_BIN` | `~/.local/bin/llama-server` |
| `LLAMA_SWAP_PORT` | `8080` |
| `LLAMA_SWAP_START_PORT` | `5800` |
| `LLAMA_TTL` | `900` (non-resident idle unload, seconds) |
| `LLAMA_CTX` | `131072` |
| `LLAMA_NGL` | `99` |
| `LLAMA_THREADS` | `$(nproc)` |
| `LLAMA_COMMON_FLAGS` | `--flash-attn auto --jinja --cache-type-k q8_0 --cache-type-v q8_0` |
| `OPENCODE_CONFIG` / `PI_CONFIG` / `OMP_CONFIG` | standard client paths |
| `CLAUDE_LOCAL` | `~/.local/bin/claude-local` |
| `LLAMA_EXAMPLES_DIR` | `~/.config/llama-server/examples` |
| `LLAMA_OVERRIDES` | `~/.config/llama-config/models.conf` |
| `LLAMA_FIT` | `1` (`0` disables VRAM fitting) |
| `LLAMA_FIT_MARGIN` | `2048` (MiB held back per device) |
| `LLAMA_FIT_COMPUTE` | `512` (MiB estimate for compute buffers) |
| `LLAMA_IGPU_MATCH` | RADV APU codenames (`PHOENIX\|RENOIR\|...`) |

## Security

llama-swap listens on `0.0.0.0:8080` with no auth. On an untrusted network, bind
it to localhost/Tailscale or front it with an authenticating reverse proxy.
