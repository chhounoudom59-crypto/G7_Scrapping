#!/bin/bash
# =============================================================
# docker-entrypoint.sh
# =============================================================
# Behaviour:
#   • RUN_NOW=true  → run scraper immediately, then start cron
#   • RUN_NOW=false → start cron only (default for production)
#   • Pass "python main.py" as CMD args to run once and exit
# =============================================================

set -e

echo "=================================================="
echo "  G7 Scraper Docker Container Starting"
echo "  Time: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "=================================================="

# If CMD args were passed (e.g. python main.py), run them directly
if [ "$#" -gt 0 ]; then
    echo "Running command: $@"
    exec "$@"
fi

# Run immediately on first start if RUN_NOW=true
if [ "${RUN_NOW:-true}" = "true" ]; then
    echo ""
    echo "RUN_NOW=true — running scraper now..."
    echo ""
    python main.py
    echo ""
    echo "Initial run complete. Starting cron for scheduled runs..."
fi

# Start cron daemon in foreground
echo "Cron schedule: daily at 06:00 UTC"
echo "Logs: /app/logs/cron.log"
echo ""

# Touch cron log so tail works immediately
touch /app/logs/cron.log

# Keep cron alive and stream logs
service cron start
tail -f /app/logs/cron.log