# keys

Every secret the suite uses (plus daily-update on mini-ubuntu) lives in one 1Password vault,
`ai-suite`. This directory holds only names and `op://` references: the inventory below,
templates for each machine's env files, and two scripts. No values are ever committed here.

Each secret is a **Password** item whose title is the variable name, so its reference is
`op://ai-suite/<NAME>/password`.

```bash
keys/render --dry-run mini-ubuntu2   # what would change, by variable name only
keys/render mini-ubuntu2             # write the env files, restart what changed
keys/new-tokens                      # create AI_SWAP_API_KEY and AI_SEARCH_TOKEN if missing
```

## Inventory

| Item (variable) | Used by | Machine: file | State today |
|---|---|---|---|
| `BRAVE_API_KEY` | ai-search (Brave Search backend) | mini-ubuntu2: `~/.config/ai-search/env` | set |
| `AI_SEARCH_TOKEN` | ai-search: required from clients when set | mini-ubuntu2: `~/.config/ai-search/env` | empty (search is open) |
| ↳ same value as `AI_FACTORY_SEARCH_TOKEN` | ai-factory → ai-search | mini-ubuntu2: `~/.config/ai-factory/env` | new |
| ↳ same value as `AI_DELEGATE_SEARCH_TOKEN` (`web.search_token`) | ai-delegate → ai-search | studio: `~/.config/ai-delegate/env` | new |
| `AI_FACTORY_TOKEN` | ai-factory API/UI login | mini-ubuntu2: `~/.config/ai-factory/env` | set |
| `AI_SWAP_API_KEY` | ai-swap, one key for the whole cluster (also sent to peers) | studio, mini-ubuntu, mini-ubuntu2: `~/.config/ai-swap/env` | new |
| ↳ same value, sent as a client | ai-factory; ai-delegate; ai-bench; daily-update; pi/opencode/claude-swap configs from ai-swap-clients and llama-config (they read `$AI_SWAP_API_KEY` at run time: `!printenv AI_SWAP_API_KEY` for pi and omp, `{env:…}` for opencode, `${…}` in the Claude wrappers) | mini-ubuntu2: ai-factory env; studio: ai-delegate env and your shell; mini-ubuntu: daily-update `.env` and your shell | new |
| `DASH_TOKEN` | daily-update dashboard sign-in | mini-ubuntu: `~/dev/daily-update/.env` | set |
| `LOCATION_TOKEN` | daily-update phone location webhook | mini-ubuntu: `~/dev/daily-update/.env` | set |
| `ANTHROPIC_API_KEY` | daily-update's `anthropic` provider (the SDK reads `ANTHROPIC_API_KEY`/`ANTHROPIC_AUTH_TOKEN` from the environment, which `core/common.py` loads from `.env`) | mini-ubuntu: `~/dev/daily-update/.env` | not set; config.json uses ai-swap. Create the item only if you switch providers |

Files, not variables (store as 1Password **Documents**, not rendered by `render`):

| Document | Used by | Path |
|---|---|---|
| Google OAuth client | daily-update | mini-ubuntu: `~/dev/daily-update/credentials.json` |
| Google refresh token | daily-update (written by its one-time consent flow) | mini-ubuntu: `~/dev/daily-update/data/google/token.json` (exists) |

Not managed here:

- `~/.claude/.credentials.json` on mini-ubuntu: Claude Code's own sign-in, maintained by `claude`.
- `AI_FACTORY_GITHUB_TOKEN`: ai-factory reads it if present; not set anywhere today.
- The Mac's hf-watch LaunchAgent has no secrets (only `PATH`); the Mac's ai-swap LaunchAgent and
  `~/.config/ai-delegate/config.yaml` have none yet.

Retired, delete:

- mini-ubuntu: `~/.config/foreman/` (`foreman.env` still holds `FOREMAN_TOKEN`; the `foreman`
  unit is gone). `rm -r ~/.config/foreman`
- mini-ubuntu2: `~/.config/ai-factory/env.bak-searxng`, an old copy of the ai-factory env that
  still holds `AI_FACTORY_TOKEN`.

## Templates

`templates/<machine>/<service>.env.tpl` is the service's env file with each secret replaced by
`{{ op://ai-suite/<NAME>/password }}`; the non-secret lines are copied as they are today. Two
header lines tell `render` what to do (they aren't written to the env file):

```
# target: ~/.config/ai-search/env
# restart: systemd ai-search        # or: launchd <label> | none
```

| Machine | Template | Target | Restart |
|---|---|---|---|
| studio | `ai-swap` | `~/.config/ai-swap/env` | LaunchAgent `com.github.hofftodd.ai-swap` |
| studio | `ai-delegate` | `~/.config/ai-delegate/env` | none (restart Claude Code) |
| mini-ubuntu | `ai-swap` | `~/.config/ai-swap/env` | `ai-swap` |
| mini-ubuntu | `daily-update` | `~/dev/daily-update/.env` (includes `AI_SWAP_API_KEY`) | `daily-update` |
| mini-ubuntu2 | `ai-swap` | `~/.config/ai-swap/env` | `ai-swap` |
| mini-ubuntu2 | `ai-search` | `~/.config/ai-search/env` | `ai-search` |
| mini-ubuntu2 | `ai-factory` | `~/.config/ai-factory/env` | `ai-factory` |

To change a non-secret setting in one of these env files, change the template and render, or
the next render puts the old line back.

## render

`render [--dry-run] [--force] <machine>` refuses to run on a host whose name isn't `<machine>`
unless `--force`. For each template it runs `op inject` into a private temp file and compares it
with the target. If they differ it backs the target up to `<target>.bak-<timestamp>` (mode 600),
installs the new file (mode 600) and restarts that one service:

- **systemd:** if the unit doesn't already load the target (ai-swap's units don't today), it adds
  `~/.config/systemd/user/<unit>.service.d/keys.conf` with `EnvironmentFile=-<target>`, then
  `daemon-reload` and `restart`. daily-update reads `.env` itself, so its drop-in is harmless.
- **launchd:** launchd can't read env files, so the variables are also copied into the
  LaunchAgent's `EnvironmentVariables` (the plist becomes mode 600), then the agent is reloaded.

`--dry-run` lists `+NAME`, `-NAME` or `~NAME` (added, removed, changed) per file, and the
drop-ins and restarts it would do. It compares hashes; values are never printed.

## Rollout order

Setting a key turns authentication on, so clients must have it first:

1. ai-swap with `AI_SWAP_API_KEY` support deployed on all three nodes; ai-factory, ai-delegate
   and the agent clients able to send it.
2. `keys/new-tokens`.
3. Render all three machines back to back: an ai-swap node with a key rejects peers without one.
4. Search: rendering mini-ubuntu2 sets `AI_SEARCH_TOKEN`, which closes ai-search to anything
   without it. ai-factory gets it in the same render; render studio right after for ai-delegate.

Every client can send the key when it's set (and sends nothing when it isn't): ai-factory
(ai-factory#49), ai-delegate (ai-delegate#6, reads `~/.config/ai-delegate/env`), ai-bench
(ai-bench#3), daily-update (daily-update#3, `api_key_env`), and the client configs written by
`ai-swap-clients` and `llama-config`. Merge and deploy those before step 3. daily-update's
`config.json` is local: add `"api_key_env": "AI_SWAP_API_KEY"` to `providers.local` on
mini-ubuntu before rendering it.

## You do

Claude never sees or types the values; you enter them.

1. **Install `op`** on each machine:
   - studio: `brew install 1password-cli`, then in the 1Password app, Settings → Developer →
     *Integrate with 1Password CLI*. Check with `op vault list`.
   - mini-ubuntu, mini-ubuntu2: install the `1password-cli` package from 1Password's apt
     repository (developer.1password.com/docs/cli/get-started).
2. **Create the vault** `ai-suite` (in the app, or `op vault create ai-suite`).
3. **Create a service account** for the two Linux boxes with read access to `ai-suite` only
   (1Password.com → Developer → Service Accounts). On each Linux box save its token:
   `install -d -m 700 ~/.config/op && install -m 600 /dev/stdin ~/.config/op/service-account-token`
   and paste, then Ctrl-D. `op` refuses to run if `~/.config/op` is wider than 700.
   Check with `keys/render --dry-run <machine>`.
4. **Enter the existing values** as Password items titled exactly `BRAVE_API_KEY`,
   `AI_FACTORY_TOKEN`, `DASH_TOKEN`, `LOCATION_TOKEN` (copy them from the env files listed in the
   inventory), e.g. `op item create --vault ai-suite --category password --title DASH_TOKEN` and
   set the password in the app. Add `credentials.json` and `data/google/token.json` with
   `op document create <file> --vault ai-suite`.
5. **Generate the new ones:** `keys/new-tokens` (on studio).
6. **Shells:** pi, opencode, claude-swap and claude-local read `$AI_SWAP_API_KEY`, so load it in
   your shell on studio (`~/.zshrc`) and mini-ubuntu (`~/.bashrc`):
   `set -a; [ -r ~/.config/ai-swap/env ] && . ~/.config/ai-swap/env; set +a`
   Then rerun `ai-swap-clients` (studio) and `llama-config` (mini-ubuntu) once the key is set,
   so their configs refer to the variable instead of the dummy key.
7. **Clean up** the retired files listed above.
8. Follow the rollout order: `keys/render --dry-run <machine>`, then `keys/render <machine>`.
