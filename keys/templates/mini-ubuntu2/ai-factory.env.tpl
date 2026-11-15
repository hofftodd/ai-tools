# target: ~/.config/ai-factory/env
# restart: systemd ai-factory
AI_FACTORY_HOST=0.0.0.0
AI_FACTORY_PORT=8700
AI_FACTORY_DATA_DIR=/home/thoffman/.local/share/ai-factory
AI_FACTORY_RUNTIME=docker
AI_FACTORY_TOKEN={{ op://ai-suite/AI_FACTORY_TOKEN/password }}
AI_FACTORY_SEARCH_URL=http://127.0.0.1:8889
AI_FACTORY_SEARCH_TOKEN={{ op://ai-suite/AI_SEARCH_TOKEN/password }}
AI_SWAP_API_KEY={{ op://ai-suite/AI_SWAP_API_KEY/password }}
