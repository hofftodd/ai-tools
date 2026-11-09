# TODO

Open work across the suite, as of 2026-11-09 (Foreman renamed to ai-factory, which runs on mini-ubuntu2). Benchmarking work is tracked
separately in [`ai-bench/TODO.md`](ai-bench/TODO.md).

## Needs you (a decision, sudo or the router)

- [ ] **Delete the archived Mac models (frees ~738 GB).** All 457 files are verified on the NAS
  (`<nas>/models-mac/`, size plus sampled hashes; see `~/models-archived/README.md`). The delete was
  blocked for me, so run:
  `cd ~/models-archived && rm -rf ds4 deepseek-v4-flash flint qwen3.8-27b qwen3.8-flash-next omlx sushi`

## ai-factory on the ai-swap cluster

- [ ] **Start ai-factory and add nodes**, one per model, all on the Mac's ai-swap endpoint
  (`http://studio.local:8080/v1`), OpenAI-compatible, no key, price 0:

  | node | context window | capacity | model id |
  |---|---|---|---|
  | `deepseek` | 131072 | 2 | `deepseek-v4-flash` |
  | `flint` | 131072 | 4 | `flint` |
  | `thinkingcap` | 131072 | 1 | `thinkingcap-qwen3.8-27b` |

  Bindings: Project Planner, Task Planner and Escalation → deepseek; Builder → flint;
  Tester → thinkingcap.
- [ ] **A real project end to end** after PR #5: the Environment Agent building the toolchain,
  the new pipeline rules, and (for an existing repo) the "How tests run here" note.
- [ ] **A real multi-project run** to watch the swap avoidance (`ai-factory/src/ai_factory/residency.py`)
  outside the tests: wait events in the activity feed, loaded-first ordering, no ping-pong swaps,
  and waiting while ai-bench has a machine reserved.
- [ ] **Per-model health checks.** ai-factory's node check only asks whether `/v1/models` answers. On
  ai-swap nodes it should read the model's own state, so `failed` is caught and `stopped` (merely
  unloaded) isn't treated as down.
- [ ] **Import nodes from ai-swap** (idea): a button on the Nodes page that creates one node per
  ai-swap model with its context length, instead of entering them by hand.
- [ ] **Run a project's independent tasks in parallel.** Today each project runs one task at a
  time (`orchestrator/main.py` `pick_ready`; an M1 simplification, `specs/000-orchestrator/plan.md`
  "One active task per project"). On this cluster the Builder (flint, Mac) and Tester
  (ThinkingCap, R9700) are on different machines, so serial tasks leave one idle while the other
  works; overlapping two tasks would keep both busy without extra swaps. Do it after future-lab's
  serial run (a baseline to compare, and no restart with tasks in flight). What it takes:
  1. *Scheduling:* up to N active tasks per project (setting, default 1), only tasks whose deps
     are done; SETUP runs alone first, DOCS last.
  2. *Merge queue:* merges one at a time; after A merges, B syncs with the milestone branch and
     the full suite runs again before B merges. A conflict sends B back to its Builder with the
     conflict.
  3. *Replanning:* the after-task reviews queue per project, and a review may change or remove
     only queued tasks, never running ones.
  4. *Coverage and diffs* are measured from a task's base commit; keep that right when the branch
     moves under a running task.
  5. *Placement:* the swap avoidance (`residency.py`) should prefer overlapping steps that land on
     different machines over two steps queueing for one model.
  Tests should cover the merge queue (two green tasks that break together, a conflict) and the
  replanning races. Use future-lab's next phase as the first real trial.

## ai-bench

- [ ] **Benchmark the pending models** on the Mac (Arete-27B, Nemotron 3.5 Super VL, AesCode-32B in
  `~/models-pending`; details in `ai-bench/TODO.md`). Runs now reserve the Mac's ai-swap and unload
  its models automatically (`reserve:` in `bench-mac.yaml`), so it can stay running.

## ai-swap

- [ ] **Event stream** (idea): `GET /api/events` (server-sent events) for model and reservation
  changes, to replace the UI's 3 s polling, the peers' 10 s polling and ai-factory's residency reads.
  The step to take before considering any message broker.
- [ ] **Measured memory** (its roadmap): `memory_gb` is configured, not measured. oMLX reports
  actual model sizes at `/v1/models/status`, and ai-swap could cross-check with it.
- [ ] **Strata's non-interactive server command**, still unconfirmed (roadmap item 1). Sushi, ds4
  and oMLX are confirmed.
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
