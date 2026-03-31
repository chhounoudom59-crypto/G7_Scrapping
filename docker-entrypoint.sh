#!/bin/bash
# =============================================================
# docker-entrypoint.sh — Entry point for the G7 Scraper Docker container
# =============================================================
# This script handles:
# 1. Running the scraper immediately if RUN_NOW is "true" (default)
# 2. Starting cron to run scheduled jobs
# =============================================================

set -e

# ── Configure environment ────────────────────────────────────
RUN_NOW=${RUN_NOW:-true}
LOG_FILE="/app/logs/cron.log"

# Ensure log directory exists
mkdir -p /app/logs

# ── Run scraper immediately if RUN_NOW is "true" ────────────
if [ "$RUN_NOW" = "true" ]; then
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Running scraper immediately..." >> "$LOG_FILE"
    cd /app && python main.py >> "$LOG_FILE" 2>&1 || true
fi

# ── Start cron daemon ────────────────────────────────────────
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Starting cron daemon..." >> "$LOG_FILE"
cron -f
