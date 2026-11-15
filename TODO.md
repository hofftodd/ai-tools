# TODO

Open work across the suite, as of 2026-11-15 (suite fixes deployed: ai-swap leases, API key, model facts and learned peers; ai-common shared by ai-factory and ai-delegate; keys in 1Password, not yet switched on). Benchmarking work is tracked
separately in [`ai-bench/TODO.md`](ai-bench/TODO.md).

## Needs you (a decision, sudo or the router)

- [ ] **Delete the archived Mac models (frees ~738 GB).** All 457 files are verified on the NAS
  (`<nas>/models-mac/`, size plus sampled hashes; see `~/models-archived/README.md`). The delete was
  blocked for me, so run:
  `cd ~/models-archived && rm -rf ds4 deepseek-v4-flash flint qwen3.8-27b qwen3.8-flash-next omlx sushi`

- Keys switched on 2026-11-15: ai-swap's key on all three machines, ai-search's token, all from
  the `ai-suite` vault via `keys/render`. Shells on studio and mini-ubuntu load
  `~/.config/ai-swap/env`.
- [ ] **Change `AI_FACTORY_TOKEN`** (it was copied, not regenerated, and has been in ai-factory's
  access log): regenerate the item, `keys/render mini-ubuntu2`, sign in to the dashboard again.
- [ ] **Store daily-update's Google files** (`credentials.json`, `data/google/token.json`) as
  1Password Documents (`op document create … --vault ai-suite`).
- [ ] **Delete the pre-key env backups** (`*.bak-20261115-*`, mode 600) once the keys have run a
  while.

## ai-factory on the ai-swap cluster

- [ ] **Re-create the nodes from ai-swap** with the Nodes page's Import button (ai-factory#48):
  one node per model with pinned ids (`flint@studio`, `deepseek-v4-flash@studio`,
  `thinkingcap-qwen3.8-27b@mini-ubuntu`) so residency and placement agree. Bindings: Project
  Planner, Task Planner and Escalation → deepseek; Builder → flint; Tester → thinkingcap.
- [ ] **future-lab end to end, unattended** (next): nodes imported as above,
  `max_parallel_tasks` 2. Log every point where a person had to step in; those become the next
  items here. Covers the Environment Agent building the toolchain, the pipeline rules, restart
  recovery and leases in real use.
- [ ] **A real multi-project run** to watch the swap avoidance (`ai-factory/src/ai_factory/residency.py`)
  outside the tests: wait events in the activity feed, loaded-first ordering, no ping-pong swaps,
  and waiting while ai-bench has a machine reserved.
- [ ] **The dashboard token shows up in access logs.** The dashboard's event stream passes
  `AI_FACTORY_TOKEN` as `?token=` in the URL, so uvicorn's access log on mini-ubuntu2 records it in
  `journalctl --user -u ai-factory`. Send it in a header or cookie instead, or drop the query
  string from the access log. Rotate the token once fixed (it moves to 1Password with the rest).
- Done 2026-11-15: restart recovery requeues interrupted tasks, per-model health checks, Docker
  permission problems reported to the user, residency with pinned ids, placement spreads
  parallel steps across machines, node import from ai-swap (ai-factory#48); ai-common sandbox
  and web research, a lease per step, the ai-swap key everywhere (ai-factory#49). Parallel tasks
  already existed (`max_parallel_tasks`, ai-factory 1b13115).

## ai-delegate

- [ ] **Register it and try it on real work** (on main since 2026-11-13): `uv run
  ai-delegate image && uv run ai-delegate routes --write && uv run ai-delegate skill`, then
  `claude mcp add -s user ai-delegate -- uv run --project ~/dev/ai-tools/ai-delegate ai-delegate
  serve`. Copy `examples/config.yaml` first for the ai-bench name map (`ds4-q4` and others).
  Keep the trial notes DESIGN.md asks for (kept / fixed / redone); they decide what's next.
- [ ] **Run `routes --write` after new ai-bench results**; it lists the models it couldn't match.
- [ ] **Watch `ai-delegate stats`** during the trial: tokens saved net of redone work, per tool
  and model. The native side is an estimate; compare it with real session usage when possible.
- Done 2026-11-15: web research writes a partial report at its limits, warns when another
  variant of the requested model is loaded, and "typically" counts every run by depth
  (ai-delegate#5); ai-common, a lease per job, and the ai-swap and ai-search keys (ai-delegate#6).
- [ ] Idea: a `sandbox-exec` (Seatbelt) level on macOS between `docker` and `local`, so jobs
  can use the Mac's toolchains with writes limited to the clone (DESIGN.md, Delegation safety).

## ai-bench

- [ ] **Benchmark the pending models** on the Mac (Arete-27B, Nemotron 3.5 Super VL, AesCode-32B in
  `~/models-pending`; details in `ai-bench/TODO.md`). Runs now reserve the Mac's ai-swap and unload
  its models automatically (`reserve:` in `bench-mac.yaml`), so it can stay running.

## ai-swap

- Done 2026-11-15 (ai-swap#4, deployed on all three): leases (`/api/leases`), `node.api_key` /
  `AI_SWAP_API_KEY`, parameters and quantization from model files on the card, peers learned
  from peers. Placement is deployed; ai-factory's residency maps pinned ids (ai-factory#48).

- [ ] **Event stream** (idea): `GET /api/events` (server-sent events) for model and reservation
  changes, to replace the UI's 3 s polling, the peers' 10 s polling and ai-factory's residency reads.
  The step to take before considering any message broker.
- [ ] **Measured memory** (its roadmap): `memory_gb` is configured, not measured. oMLX reports
  actual model sizes at `/v1/models/status`, and ai-swap could cross-check with it.
- [ ] **Strata's non-interactive server command**, still unconfirmed (roadmap item 1). Sushi, ds4
  and oMLX are confirmed.
- [ ] **omp ignores its generated providers on mini-ubuntu.** omp 14.6.4 lists only its own
  `llama.cpp/gemma-4-26b-a4b`; the `llama-*` and `ai-swap-*` providers that llama-config and
  ai-swap-clients write to `~/.omp/agent/models.yml` don't appear in `omp --list-models`, so the
  file's format or location has changed for this omp. pi works with the same providers.
- [ ] **pi 0.72 on mini-ubuntu** is the old `@mariozechner/pi-coding-agent`; studio runs
  `@earendil-works/pi-coding-agent` 1.5. Both work with the keyed configs (`!printenv`).
- [ ] **omp on the Mac:** `ai-swap-clients` skips oh-my-pi because `~/.omp` doesn't exist there.
  Set it up, then rerun `ai-swap-clients --default flint`.
- [ ] **A Mac config generator** (optional): like `llama-config`, but discovering `~/models/omlx`
  and DwarfStar GGUFs, sizing from RAM and restarting through launchd. Only worth it if the Mac's
  model list starts changing often; today its six models are hand-written.
- [ ] Optional: delete `~/.local/share/retired/llama-swap/` on mini-ubuntu once ai-swap has run
  the R9700 benchmarks for a while, and drop llama-swap support from `llama-config`.

## Machines and network

- [ ] mini-ubuntu is on Wi-Fi only (physical constraint; IPv6 disabled on `HoffmanNet` on
  2026-11-08). If it can be wired later, latency to it drops from ~15–35 ms to under 1 ms.
- [ ] The Mac's Wi-Fi is off (wired on en0, 192.168.0.4). Turn it back on only if needed.

## Reference

- Layout: `suite` clones, updates and checks everything (`./suite`, `./suite update`); see
  [README.md](README.md) and [ARCHITECTURE.md](ARCHITECTURE.md).
- ai-swap configs: Mac `~/.config/ai-swap/config.yaml` (hand-written; LaunchAgent
  `com.github.hofftodd.ai-swap`), mini-ubuntu `~/.config/ai-swap/config.yaml` (generated by
  `llama-config`; `peers:` is kept; systemd user unit `ai-swap`).
- Agents on either machine reach every model: `ai-swap-clients` writes `ai-swap-*` providers for
  pi, omp and opencode, plus `~/.local/bin/claude-swap`.
- Reservations: ai-bench runs reserve their machine's ai-swap (`reserve:` in both configs); a stuck
  reservation lapses after 5 minutes, or use Release in the ai-swap UI.
- llama-swap is retired (2026-11-08). ai-swap answers its `/running`, `/unload` and `/upstream`, and
  ai-bench's R9700 `swap` backend is now `type: ai-swap`. The binary, config and unit file are in
  mini-ubuntu's `~/.local/share/retired/llama-swap/`; to bring it back, move them to
  `~/.local/bin/`, `~/.config/llama-swap/` and `~/.config/systemd/user/`, then run
  `LLAMA_BACKEND=llama-swap llama-config`.
- mini-ubuntu's `ai-factory/executor-base` image was rebuilt on 2026-11-08 from PR #5's Dockerfile
  (pi, OpenCode, ripgrep).
