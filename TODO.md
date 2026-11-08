# TODO

Open work across the suite, as of the end of the 2026-11-08 session (ai-swap on both machines,
Foreman swap avoidance and reservations, the suite layout). Benchmarking work is tracked
separately in [`ai-bench/TODO.md`](ai-bench/TODO.md).

## Needs you (a decision, sudo or the router)

- [ ] **Review and merge Foreman PR #5** (https://github.com/hofftodd/foreman/pull/5): the
  Environment Agent and task-pipeline fixes rescued from mini-ubuntu (originally `70478f8`, 23 Oct),
  ported onto `main`, plus the new "How tests run here" note in place of the test-command
  override. Lint, types, 261 tests and all 16 Docker tests (on mini-ubuntu) passed, and GitHub's
  `test` jobs passed on macOS and Ubuntu, **but the `e2e` job (Playwright UI tests) failed**:
  https://github.com/hofftodd/foreman/actions/runs/42509555669/job/128820629160. Probably the new
  Environment step or the settings form changed what a UI test expects; fix that before merging.
  After merging, delete the branches it supersedes:
  `git push origin --delete environment-agent rescue/environment-agent claude/beautiful-edison-pouelc`,
  and on mini-ubuntu `git -C ~/dev/ai-tools/foreman branch -D claude/beautiful-edison-pouelc`
  (its `local-node-and-toolchains` branch is also stale).
- [ ] **Tell the other Claude session on mini-ubuntu** (if it's resumed) that `foreman`, `ai-swap`
  and `ai-bench` moved to `~/dev/ai-tools/`, and that its unpushed commit on
  `claude/beautiful-edison-pouelc` now lives in PR #5: it should work from `main`, not that branch.
- [ ] **Delete the archived Mac models (frees ~738 GB).** All 457 files are verified on the NAS
  (`<nas>/models-mac/`, size plus sampled hashes; see `~/models-archived/README.md`). The delete was
  blocked for me, so run:
  `cd ~/models-archived && rm -rf ds4 deepseek-v4-flash flint qwen3.8-27b qwen3.8-flash-next omlx sushi`
- [ ] **Fixed address for mini-ubuntu.** On the TP-Link router (http://192.168.0.1 → Advanced →
  Network → DHCP Server → Address Reservation), reserve `78:93:C3:BA:E8:56` → `192.168.0.179`
  (optionally the Mac, `7C:D6:2C:04:59:65` → `192.168.0.208`). Then on the Mac:
  `echo "192.168.0.179 mini-ubuntu.local mini-ubuntu" | sudo tee -a /etc/hosts && sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder`
  Until then, programs on the Mac that look up `mini-ubuntu.local` directly wait 5 s per lookup (no
  IPv6 answer). ai-swap itself is unaffected: it dials IPv4 first.
- [ ] **Where to run Foreman.** Pick its host: a separate Linux machine with Docker (preferred; see
  `foreman/specs/000-orchestrator/spec.md` §4), or one of the two model machines for now.

## Foreman on the ai-swap cluster

- [ ] **Start Foreman and add nodes**, one per model, all on the Mac's ai-swap endpoint
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
- [ ] **A real multi-project run** to watch the swap avoidance (`foreman/src/foreman/residency.py`)
  outside the tests: wait events in the activity feed, loaded-first ordering, no ping-pong swaps,
  and waiting while ai-bench has a machine reserved.
- [ ] **Per-model health checks.** Foreman's node check only asks whether `/v1/models` answers. On
  ai-swap nodes it should read the model's own state, so `failed` is caught and `stopped` (merely
  unloaded) isn't treated as down.
- [ ] **Import nodes from ai-swap** (idea): a button on the Nodes page that creates one node per
  ai-swap model with its context length, instead of entering them by hand.

## ai-bench

- [ ] **Benchmark the pending models** on the Mac (Arete-27B, Nemotron 3.5 Super VL, AesCode-32B in
  `~/models-pending`; details in `ai-bench/TODO.md`). Runs now reserve the Mac's ai-swap and unload
  its models automatically (`reserve:` in `bench-mac.yaml`), so it can stay running.
- [ ] **Refresh mini-ubuntu's results pages.** Its `RESULTS.md` and `dashboard/data/` were last
  generated on 1 Nov, before the dashboard gained the 128k columns. Run
  `uv run aibench -c bench.yaml dashboard` there and commit the result.

## ai-swap

- [ ] **Event stream** (idea): `GET /api/events` (server-sent events) for model and reservation
  changes, to replace the UI's 3 s polling, the peers' 10 s polling and Foreman's residency reads.
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
- [ ] The Mac's Wi-Fi is off (wired on en0, 192.168.0.208). Turn it back on only if needed.

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
- mini-ubuntu's `foreman/executor-base` image was rebuilt on 2026-11-08 from PR #5's Dockerfile
  (pi, OpenCode, ripgrep).
