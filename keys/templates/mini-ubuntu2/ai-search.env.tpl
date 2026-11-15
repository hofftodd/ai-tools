# target: ~/.config/ai-search/env
# restart: systemd ai-search
AI_SEARCH_BACKEND=brave
AI_SEARCH_QPS=1
AI_SEARCH_MONTHLY_CAP=1800
AI_SEARCH_BIND=0.0.0.0:8889
AI_SEARCH_TOKEN={{ op://ai-suite/AI_SEARCH_TOKEN/password }}
AI_SEARCH_CACHE_TTL=86400
BRAVE_API_KEY={{ op://ai-suite/BRAVE_API_KEY/password }}
