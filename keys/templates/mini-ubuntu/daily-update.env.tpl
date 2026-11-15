# target: ~/dev/daily-update/.env
# restart: systemd daily-update
DASH_TOKEN={{ op://ai-suite/DASH_TOKEN/password }}
LOCATION_TOKEN={{ op://ai-suite/LOCATION_TOKEN/password }}
# ai-swap's key; config.json's providers.local has "api_key_env": "AI_SWAP_API_KEY" (daily-update#3).
AI_SWAP_API_KEY={{ op://ai-suite/AI_SWAP_API_KEY/password }}
# Only for config.json's "anthropic" provider (not used today). To use it, create an
# ANTHROPIC_API_KEY item in the vault and add a line for it like the ones above.
# (No vault references in comments: op inject resolves them there too.)
