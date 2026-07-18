# llama-pick

Generator that turns the GGUFs under `~/models/` into a [llama-swap](https://github.com/mostlygeek/llama-swap)
config and repoints every client (opencode, pi, oh-my-pi, Claude Code) at the
single llama-swap endpoint.

llama-swap is one proxy in front of `llama-server`: it reads the `model` field on
each request, starts the right backend on demand, and unloads idle ones after a
TTL. So you no longer choose *which servers to run* — every model is always
addressable by name and RAM is reclaimed automatically. What you pick here is
which models stay **resident** (pinned hot, never unloaded).

> **History:** llama-pick used to run one `llama-server@<alias>.service` systemd
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
llama-pick                          # regenerate, keeping the current resident set
llama-pick ornith-35b gpt-oss-20b   # pin these two resident, regenerate everything
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
  co-loaded, and a `hooks.on_startup.preload` for them. Per-model extras: Ornith
  gets `--spec-type draft-mtp` (MTP self-speculative decode); vision models get
  `--mmproj`; models needing a forked llama.cpp (e.g. Bonsai ternary) are emitted
  `unlisted: true` so they're hidden from clients until buildable.
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
(`ornith-35b`). Projector files (`*mmproj*.gguf`) and non-first shards are never
listed as models.

## Requirements

- `llama-swap` on `PATH` (release binary → `~/.local/bin/llama-swap`) and a
  `~/.config/systemd/user/llama-swap.service` unit listening on `0.0.0.0:8080`.
- `llama-server` at `~/.local/bin/llama-server` (build new enough for
  `/v1/messages` and `--spec-type`).
- `jq` on `PATH`; `yq` for the omp config and reading the resident set.
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

## Security

llama-swap listens on `0.0.0.0:8080` with no auth. On an untrusted network, bind
it to localhost/Tailscale or front it with an authenticating reverse proxy.
