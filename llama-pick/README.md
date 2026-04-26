# llama-pick

Interactive switcher for the local `llama-server` setup. Lists every GGUF
under `~/models/`, lets you pick one, and rewires the three places that
reference the active model so they stay in sync:

- `~/.config/llama-server/config.env` — `MODEL=`, `MMPROJ=`, and the
  `--alias …` flag inside `EXTRA_ARGS=`.
- `~/.config/opencode/opencode.json` — the `llama-local` provider's models
  map and the top-level `model` / `small_model`.
- `~/.pi/agent/models.json` — the `llama-local` provider's `models[]` array
  and `compat.thinkingFormat` (selected by alias substring).

Then it restarts `llama-server.service` (systemd user unit) and waits for
`/health` to return 200.

## Requirements

- A working `llama-server` systemd user unit (the `~/.config/llama-server/`
  config.env / launcher / unit triplet).
- `jq` on `PATH`.
- GGUFs organized as `~/models/<family-dir>/<file>.gguf`. The directory name
  becomes the server alias (e.g. `~/models/qwen3.6-35b-a3b/…` →
  `--alias qwen3.6-35b-a3b`).
- `mmproj-F16.gguf` (or `BF16` / `F32`) as a sibling of the model file
  enables vision automatically — `MMPROJ=` is set and pi's `input` becomes
  `["text", "image"]`.

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
Current: gemma-4-26b-a4b/gemma-4-26B-A4B-it-UD-Q5_K_XL.gguf

Available models in /home/thoffman/models:

   1) 16G    gemma-4-26b-a4b/gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf
 * 2) 20G    gemma-4-26b-a4b/gemma-4-26B-A4B-it-UD-Q5_K_XL.gguf
   3) 21G    qwen3.6-35b-a3b/Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf
   ...

Select model number (q/0/Enter to cancel):
```

`*` marks the currently active model. Enter `q`, `Q`, `0`, or just hit
Enter to cancel without changes. Picking the active model is a no-op.

## Thinking-format detection

The script sets pi's `compat.thinkingFormat` based on the alias:

| Alias contains | thinkingFormat   |
| -------------- | ---------------- |
| `qwen`         | `qwen-chat-template` |
| `deepseek`     | `deepseek`       |
| `glm` / `zai` / `chatglm` | `zai` |
| anything else  | omitted          |

Other compat fields (`supportsDeveloperRole: false`,
`supportsReasoningEffort: false`) are always set since llama.cpp's OpenAI
shim supports neither.

## Environment overrides

| Variable              | Default                                  |
| --------------------- | ---------------------------------------- |
| `LLAMA_MODELS_ROOT`   | `~/models`                               |
| `LLAMA_SERVER_CONFIG` | `~/.config/llama-server/config.env`      |
| `OPENCODE_CONFIG`     | `~/.config/opencode/opencode.json`       |
| `PI_CONFIG`           | `~/.pi/agent/models.json`                |

Context window and max output tokens for the rewritten client configs are
hardcoded constants near the top of the script (`DEFAULT_CTX=131072`,
`DEFAULT_OUT=8192`).
