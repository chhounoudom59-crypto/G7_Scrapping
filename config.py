# =============================================================
# config.py — Central Configuration for G7 Scraper
# =============================================================
# Only paths, rate limits, and behaviour flags live here.
# All site-specific config (URLs, selectors, RSS feeds) lives
# in sites.json so you can edit it without touching Python code.
# =============================================================

import os

BASE_DIR        = os.path.dirname(os.path.abspath(__file__))

# ── Data Directories ──────────────────────────────────────────
DATA_DIR        = os.path.join(BASE_DIR, "data")
RAW_DIR         = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR   = os.path.join(DATA_DIR, "processed")
MARKDOWN_DIR    = os.path.join(DATA_DIR, "markdown")
LOG_DIR         = os.path.join(BASE_DIR, "logs")

SITES_FILE      = os.path.join(BASE_DIR, "sites.json")
CHECKPOINT_FILE = os.path.join(PROCESSED_DIR, "checkpoints.json")

# ── Rate Limiting ─────────────────────────────────────────────
# Random delay between every HTTP request (seconds).
# Being polite keeps us off block-lists and is the ethical thing to do.
RATE_LIMIT_MIN  = 1.5    # minimum seconds between requests
RATE_LIMIT_MAX  = 3.0    # maximum seconds between requests

# Max articles to scrape per source per run.
# Set to 99999 to scrape everything; lower for testing.
MAX_ARTICLES    = 99999

# ── Request Settings ──────────────────────────────────────────
REQUEST_TIMEOUT = 30     # seconds before giving up on a request
MAX_RETRIES     = 3      # retry count on network errors

# For Japan, we generate monthly archive URLs going this far back.
JAPAN_MONTHS_BACK = 24

# Tracking/analytics URL parameters to strip before comparing URLs.
# This prevents the same article with different UTM params being saved twice.
STRIP_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "source", "_ga",
}

# Fallback RSS paths to try if the configured rss_url returns nothing.
RSS_FALLBACK_PATHS = [
    "/feed", "/feed/", "/rss.xml", "/rss",
    "/en/feed", "/en/rss.xml", "/actualites.atom",
]

# HTTP headers — use a research bot User-Agent (more polite and honest)
HEADERS = {
    "User-Agent": (
        "G7PolicyResearchBot/2.0 "
        "(Academic research; contact: research@example.com)"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ── Logging ───────────────────────────────────────────────────
LOG_LEVEL = "INFO"
