# =============================================================
# Dockerfile — G7 Government Website Scraper
# =============================================================
# Using official Playwright image (Python 3.12 + Debian)
# This image comes with browsers and dependencies PRE-INSTALLED.
# =============================================================

FROM mcr.microsoft.com/playwright/python:v1.44.0-bookworm AS base

# ── Environment variables ─────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# ── System dependencies (additional) ─────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────────────
WORKDIR /app

# ── Install Python dependencies ───────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# (Playwright browsers are already in the base image!)

# ── Copy project files ────────────────────────────────────────
COPY . .

# ── Create data directories ───────────────────────────────────
RUN mkdir -p data/raw data/processed data/markdown logs

# ── Cron job: run scraper every day at 06:00 UTC ──────────────
RUN echo "0 6 * * * cd /app && python main.py >> /app/logs/cron.log 2>&1" \
    > /etc/cron.d/g7-scraper \
    && chmod 0644 /etc/cron.d/g7-scraper \
    && crontab /etc/cron.d/g7-scraper

# ── Entrypoint script ─────────────────────────────────────────
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]