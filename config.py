# ── ClothingID EE250 — shared configuration ────────────────
# Only two values need editing before you run anything.

ANTHROPIC_API_KEY = "YOUR_ANTHROPIC_API_KEY_HERE"
SERPAPI_KEY       = "8c72895a0ef4a35369ea21148a3a8bd1fdf29bbb959c5d2278a5035057a820e2"
SERVER_IP         = "10.23.198.21"                    # ← your laptop's LAN IP

# Flask  (server.py)
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000

# Claude model
CLAUDE_MODEL = "claude-sonnet-4-6"
MAX_TOKENS   = 700

# SerpApi
SERPAPI_ENGINE  = "google_shopping"
SERPAPI_RESULTS = 3   # top N shopping results per search query

# Pi polling interval (seconds) — how often pi_camera.py checks for a trigger
PI_POLL_INTERVAL = 2
