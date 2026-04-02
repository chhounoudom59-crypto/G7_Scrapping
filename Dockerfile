# =============================================================
# Dockerfile — G7 Government Website Scraper
# =============================================================
# Multi-stage build keeps the final image lean.
# Uses Python 3.12 slim (stable).
# =============================================================

FROM python:3.12-slim AS base

# ── Environment variables ─────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# ── System dependencies ───────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    curl \
    wget \
    gnupg \
    ca-certificates \
    # Chromium dependencies for Playwright (manual list for Debian)
    fonts-liberation \
    fonts-unifont \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────────────
WORKDIR /app

# ── Install Python dependencies ───────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Install Playwright Chromium ───────────────────────────────
RUN python -m playwright install chromium

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