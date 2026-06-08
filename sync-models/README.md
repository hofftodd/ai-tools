# sync-models

Bidirectional sync of `~/models` ↔ `/mnt/nas/models` via [unison](https://www.cis.upenn.edu/~bcpierce/unison/).
GGUF model weights aren't edited in place, so conflicts only happen when one
side has a file the other doesn't — `prefer = newer` resolves them safely.

## Files

- `sync-models` — wrapper script; symlinked to `~/.local/bin/sync-models`.
- `models.prf` — unison profile; symlinked to `~/.unison/models.prf` on first run.

## Requirements

- `unison` on `PATH` (`install-unison.sh` from `ubuntu-install`/`mac-install`).
- `/mnt/nas` mounted (NFS to TrueNAS in our setup).

## Usage

```bash
sync-models                              # run the sync
sync-models -batch=false -auto=false     # preview interactively (q to quit)
sync-models -repeat 300                  # rerun every 5 minutes; Ctrl-C to exit
```

Unison has no `-dryrun` flag; the preview pattern above turns off batch/auto so
it lists each proposed action and prompts before applying.

The first run scans both sides — slow on large GGUF collections. Subsequent
runs use mtime+size fastcheck and only diff the changed files.

## Profile highlights

- Roots: `/home/thoffman/models` and `/mnt/nas/models` (edit `models.prf` if
  your paths differ).
- `prefer = newer` — newer mtime wins on conflict.
- `perms = 0` + `dontchmod = true` — don't compare permission bits and never
  call `chmod` on the NAS. TrueNAS NFSv4-ACL datasets reject POSIX chmod, which
  otherwise aborts the whole transfer with "Error in setting permissions".
- `nodeletion = /mnt/nas/models` — the NAS is a safe backup; unison never
  deletes files there. New/changed files still sync both ways, but a local
  deletion won't remove the NAS copy.
- `batch = true`, `auto = true` — non-interactive.
- Ignores `.DS_Store`, `*.tmp`, `*.partial`, and `.Trash-*`.

## Schedule

Add a systemd user timer for nightly sync:

```ini
# ~/.config/systemd/user/sync-models.service
[Unit]
Description=Sync ~/models with NAS via unison
ConditionPathIsMountPoint=/mnt/nas

[Service]
Type=oneshot
ExecStart=%h/.local/bin/sync-models

# ~/.config/systemd/user/sync-models.timer
[Unit]
Description=Nightly sync of ~/models with NAS

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Then: `systemctl --user enable --now sync-models.timer`.

## Logs

`~/.unison/models.log` (set by the profile).
