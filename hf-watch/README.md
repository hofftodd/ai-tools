# hf-watch

Watches Hugging Face for new model repos and sends a macOS notification once per
new match. Set up to catch the Inkling 2 Small weights (Thinking Machines) and the
first GGUF/MLX conversions of them.

- `watchlist.txt` — one search per line: `search term|author (optional)|regex on repo id`.
- `hf-watch` — runs every search (newest first), notifies on repo ids it hasn't seen.
  State in `~/.cache/hf-watch/` (`seen.txt`, `hf-watch.log`). `HF_WATCH_QUIET=1`
  records without notifying (use it to seed `seen.txt` after adding a search).
- `com.thoffman.hf-watch.plist` — LaunchAgent: every 6 hours and at login. Install
  and remove commands are in its header comment.
