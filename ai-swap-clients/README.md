# ai-swap-clients

Points the coding agents at **every model in an [ai-swap](https://github.com/hofftodd/ai-swap)
cluster**, so an agent on either machine can use a model on any machine.

It reads `GET <endpoint>/v1/models` (this machine's models plus every online peer's; a name
that exists on two machines appears a second time as `name@node`) and writes one provider per
model, all pointing at the same ai-swap endpoint, which forwards to the right machine:

| client | file | entries |
|---|---|---|
| pi | `~/.pi/agent/models.json` | providers `ai-swap-<model>` |
| oh-my-pi | `~/.omp/agent/models.yml` (if `~/.omp` exists and `yq` is installed) | providers `ai-swap-<model>` |
| opencode | `~/.config/opencode/opencode.json` | providers `ai-swap-<model>` |
| Claude Code | `~/.local/bin/claude-swap` | `claude-swap --model <id>` |

Only `ai-swap-*` entries are replaced; everything else in those files is kept, and each file
is backed up to `*.bak` first. If ai-swap lists no models (a peer still connecting), nothing
is changed.

```bash
ai-swap-clients --default flint        # Mac: every model; opencode/claude-swap default to flint
ai-swap-clients --remote-only          # R9700: llama-config already covers the local models
ai-swap-clients --dry-run              # show what would be written
```

Using a model on another machine:

```bash
pi --provider ai-swap-thinkingcap-qwen3.8-27b --model thinkingcap-qwen3.8-27b
opencode run -m ai-swap-deepseek-v4-flash/deepseek-v4-flash "…"
claude-swap --model flint@studio
```

On the R9700, `llama-config` runs `ai-swap-clients --remote-only` after restarting ai-swap.
Run it again by hand after adding a peer or changing another machine's models.
