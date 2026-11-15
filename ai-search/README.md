# ai-search

One web search endpoint for the suite's local models, in SearXNG's JSON shape, with the
actual search engine hidden behind it. It runs on mini-ubuntu2 at `http://mini-ubuntu2.local:8889`.

```
GET /search?q=<query>&format=json[&count=1-20][&pageno=1-10][&language=en][&time_range=day|week|month|year]
→ {"query", "number_of_results", "results": [{"title", "url", "content", "engine", "publishedDate"?, ...}], ...}
GET /healthz
→ {"ok", "backend", "cache": {...}, "usage": {"month", "calls", "cap"}}
```

- **Any SearXNG client works unchanged.** ai-factory's planner research takes it as
  `AI_FACTORY_SEARCH_URL=http://mini-ubuntu2.local:8889`, and ai-delegate's web research
  will too.
- **Backends:** `brave`, the Brave Search API and the default, and `searxng`, a SearXNG
  instance passed through. Choose one with `AI_SEARCH_BACKEND` and restart the service.
  mini-ubuntu2 already runs a SearXNG for ai-factory (`ai-factory-searxng` on
  `127.0.0.1:8888`), so `AI_SEARCH_SEARXNG_URL=http://127.0.0.1:8888` switches to it. To
  add another, write a class with `name`, `min_interval` and `search(Query) -> list[Result]`
  in `ai-search` and register it in `BACKENDS`.
- **The API key stays on this host.** Clients, and the sandboxes their agents run in, only
  ever see results.
- **Cheap to call repeatedly.**
  - Identical queries are cached for a day (`AI_SEARCH_CACHE_TTL`).
  - Backend calls go out one at a time, spaced to the plan's rate (`AI_SEARCH_QPS`).
  - A `429` from the backend is retried once.
  - `AI_SEARCH_MONTHLY_CAP` refuses calls past a monthly count, so a runaway research job
    can't use up a paid quota. The count is kept in `~/.local/state/ai-search/usage.json`
    and survives restarts.
- **Exposure:** it listens on the LAN with no auth by default. Set `AI_SEARCH_TOKEN` to
  require a token. The monthly cap limits what anyone on the LAN can spend.

Files:

- `ai-search`: the service. Python 3, standard library only.
- `ai-search.service`: the systemd user unit. Install steps are in its header.
- `env.example`: every setting, with defaults. Copy it to `~/.config/ai-search/env`.
- `test_ai_search.py`: `python3 -m unittest -v`, run from this directory.

Run it by hand: `BRAVE_API_KEY=... ./ai-search` (listens on `0.0.0.0:8889`).
