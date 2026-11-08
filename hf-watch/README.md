# hf-watch

Watches Hugging Face for new model repos and sends one macOS notification per run
when there are new matches. Set up for:

- **Named models, any size:** Inkling Small (Thinking Machines: Inkling 2 Small and
  later, not the full-size Inkling), Ripple (Ricursive), flint (Recursive) and Qwen4,
  from each lab and from the usual GGUF/MLX converters (unsloth, mlx-community,
  Jundot, AtomicChat).
- **US labs, models that fit:** new 7–600B models from NVIDIA, Google, Meta, OpenAI,
  Microsoft, Ai2, IBM, Arcee, Nous, Deep Cogito, Liquid, Prime Intellect, Snowflake,
  ServiceNow, Zyphra, xAI and Amazon. Quantized re-uploads, base models, reward/embedding
  models and other labs' models that these orgs republish are filtered out.

Files:

- `watchlist.txt` — one search per line:
  `search term ; author ; include regex ; exclude regex ; min B ; max B` (details in its header).
- `hf-watch` — Python 3, standard library only. Runs every search (newest 100 repos),
  logs each new repo id with its size, and notifies once per run.
  State in `~/.cache/hf-watch/` (`seen.txt`, `hf-watch.log`). `HF_WATCH_QUIET=1`
  records without notifying (use it to seed `seen.txt` after adding a search).
- `com.thoffman.hf-watch.plist` — LaunchAgent: every 6 hours and at login. Install
  and remove commands are in its header comment.

Run it by hand with `~/dev/ai-tools/hf-watch/hf-watch`; the log is the full list.
