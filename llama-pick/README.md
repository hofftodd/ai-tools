# llama-pick

Interactive multi-instance switcher for the local `llama-server` setup. Lists
every GGUF under `~/models/`, lets you pick one or more, runs each as its own
`llama-server@<alias>.service` systemd user instance, and rewrites the client
configs (opencode, pi, oh-my-pi) so they point at whatever is running.

Each model family gets a stable alias and a sticky port, so ports don't shuffle
between runs and you can have several models serving at once.

## What it touches

- `~/.config/llama-server/instances/<alias>.env` — one file per instance with
  `ALIAS`, `MODEL`, `MMPROJ`, `HOST`, `PORT`, `CTX`, `NGL`, `THREADS`, and
  `EXTRA_ARGS`. Consumed by the `llama-server@.service` systemd template unit.
- `~/.config/opencode/opencode.json` — rebuilds the `provider` map (one
  `llama-<alias>` entry per running instance) and sets the top-level `model` /
  `small_model` to the first pick. Non-provider keys are preserved.
- `~/.pi/agent/models.json` — replaces `.providers` with the `llama-<alias>`
  set, including `compat.thinkingFormat` (by alias) and `input` (text, or
  text+image when an mmproj is present).
- `~/.omp/agent/models.yml` — same provider schema as pi, in YAML. Only updated
  if its parent dir exists and `yq` is on `PATH`; any non-`llama-*` providers
  you've configured are preserved.
- `~/.claude-code-router/config.json` — lets [Claude Code](https://github.com/musistudio/claude-code-router)
  talk to the local instances (ccr proxies Claude Code's Anthropic Messages API
  to our OpenAI-compatible endpoints). Only updated if `ccr` is on `PATH`. Builds
  a `Providers[]` entry per instance and points `Router.default`/`think`/
  `longContext` at the first pick, with `background` routed to a small model
  (`*oss*`/`*nano*`/`*mini*`/…) when one is running. Non-`llama-*` providers and
  other top-level / `Router` keys are preserved.
- `~/.config/llama-server/examples/` — remote-friendly copies of the opencode /
  pi / omp configs with `127.0.0.1` swapped for this host's LAN IP, for copying
  onto another machine that talks to this server.

After writing the instance env files it stops dropped instances
(`systemctl --user disable --now`), starts/restarts the picked ones, and polls
each `/health` endpoint (up to 60×2s) before updating the client configs.

## Requirements

- A `llama-server@.service` systemd user template unit that reads
  `~/.config/llama-server/instances/<alias>.env`.
- `jq` on `PATH` (`yq` too, if you want the omp config / example written).
- GGUFs organized as `~/models/<family-dir>/<file>.gguf`. The directory name
  (lowercased, non-`[a-z0-9._-]` → `-`) becomes the alias, e.g.
  `~/models/qwen3.6-35b-a3b/…` → alias `qwen3.6-35b-a3b`. A GGUF sitting
  directly in the models root uses its basename instead.
- `mmproj-F16.gguf` (or `BF16` / `F32`) as a sibling of the model file enables
  vision automatically — `MMPROJ=` is set and the client `input` becomes
  `["text", "image"]`.
- Multi-shard GGUFs (`<base>-00001-of-00005.gguf`, …) are handled: only the
  first shard is listed (its size column sums the whole set), and `MODEL=` points
  at that first shard — llama.cpp loads the remaining shards automatically.

## Install

The script lives in this directory and is symlinked from `~/.local/bin/`:

```bash
ln -s "$PWD/llama-pick" ~/.local/bin/llama-pick
```

## Usage

```bash
llama-pick
```

Output looks like:

```
Currently running:
  [8080] gemma-4-26b-a4b           gemma-4-26b-a4b/gemma-4-26B-A4B-it-UD-Q5_K_XL.gguf

Available models in /home/thoffman/models:

   1) 16G    gemma-4-26b-a4b/gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf
 * 2) 20G    gemma-4-26b-a4b/gemma-4-26B-A4B-it-UD-Q5_K_XL.gguf
   3) 21G    qwen3.6-35b-a3b/Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf
   ...

Select model numbers (space- or comma-separated).
  Leading '*' marks a model currently active for its family.
  Pick at most one model per family.
  '*' on its own means: keep all currently running. Combine with numbers
      to add more (e.g. '* 5').
  Enter — no change (keep current set).
  q     — cancel.

Selection:
```

`*` in the listing marks a currently-active model. In the prompt, `*` expands to
all running instances — so `* 3` keeps everything running and adds model 3. You
can only pick one model per family; picking nothing (Enter) leaves the set
unchanged, `q` cancels.

After you confirm the plan, it stops/starts the relevant services, waits for
health, rewrites the client configs, and prints the active instances with both
their local (`127.0.0.1`) and LAN URLs.

If a running instance's configured model file has gone missing on disk, a
warning is printed — the service may still be live but won't survive a restart.

## Claude Code (via claude-code-router)

Claude Code speaks the Anthropic Messages API, not OpenAI, so it can't hit
`llama-server` directly — [claude-code-router](https://github.com/musistudio/claude-code-router)
(`ccr`) sits in between and translates. Once `ccr` is installed
(`npm install -g @musistudio/claude-code-router`), `llama-pick` writes its config
automatically on each run. Then:

```bash
ccr restart      # pick up the regenerated config
ccr code         # launch Claude Code routed at your local models
```

The first selected model becomes the `default` route, so Claude Code uses it
with no further action. Switch models in-session with ccr's `/model` command:

```
/model llama-qwen3-coder-next,qwen3-coder-next
```

Note: tool-calling reliability and prompt caching are weaker than hosted Claude;
coder-tuned models (e.g. Qwen3-Coder-Next) fare best in the agentic loop.

## Thinking-format detection

The script sets pi/omp `compat.thinkingFormat` based on the alias:

| Alias contains | thinkingFormat   |
| -------------- | ---------------- |
| `qwen`         | `qwen-chat-template` |
| `deepseek`     | `deepseek`       |
| `glm` / `zai` / `chatglm` | `zai` |
| anything else  | omitted          |

Other compat fields (`supportsDeveloperRole: false`,
`supportsReasoningEffort: false`) are always set since llama.cpp's OpenAI shim
supports neither.

## Environment overrides

| Variable              | Default                                          |
| --------------------- | ------------------------------------------------ |
| `LLAMA_MODELS_ROOT`   | `~/models`                                        |
| `LLAMA_INSTANCES_DIR` | `~/.config/llama-server/instances`                |
| `OPENCODE_CONFIG`     | `~/.config/opencode/opencode.json`                |
| `PI_CONFIG`           | `~/.pi/agent/models.json`                         |
| `OMP_CONFIG`          | `~/.omp/agent/models.yml`                         |
| `CCR_CONFIG`          | `~/.claude-code-router/config.json`               |
| `LLAMA_EXAMPLES_DIR`  | `~/.config/llama-server/examples`                 |
| `LLAMA_HOST`          | `0.0.0.0`                                          |
| `LLAMA_PORT_BASE`     | `8080` (first port; subsequent aliases climb up)  |
| `LLAMA_CTX`           | `131072`                                          |
| `LLAMA_NGL`           | `99`                                              |
| `LLAMA_THREADS`       | `$(nproc)`                                        |
| `LLAMA_EXTRA_ARGS`    | `--jinja --flash-attn auto --cache-type-k q8_0 --cache-type-v q8_0` |

These defaults are only written into an instance `.env` the first time it's
created; editing an existing `.env` by hand is preserved (the script only
rewrites `ALIAS`, `MODEL`, `MMPROJ`, and `PORT` on subsequent runs). The client
max-output-tokens is a hardcoded constant (`DEFAULT_OUT=8192`).
