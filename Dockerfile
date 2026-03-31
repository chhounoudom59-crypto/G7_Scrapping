# =============================================================
# Dockerfile — G7 Government Website Scraper
# =============================================================
# Multi-stage build keeps the final image lean.
# Uses Python 3.12 slim (stable; 3.13 Playwright wheels are not
# yet on all registries).
# =============================================================

# FROM python:3.12-slim AS base

# # ── System dependencies ───────────────────────────────────────
# # Playwright Chromium needs these libs even in headless mode.
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     cron \
#     curl \
#     ca-certificates \
#     # Playwright Chromium dependencies
#     libnss3 \
#     libnspr4 \
#     libatk1.0-0 \
#     libatk-bridge2.0-0 \
#     libcups2 \
#     libdrm2 \
#     libxkbcommon0 \
#     libxcomposite1 \
#     libxdamage1 \
#     libxfixes3 \
#     libxrandr2 \
#     libgbm1 \
#     libasound2 \
#     libpango-1.0-0 \
#     libcairo2 \
#     libx11-6 \
#     libx11-xcb1 \
#     libxcb1 \
#     libxext6 \
#     fonts-liberation \
#     fonts-unifont \
#     && rm -rf /var/lib/apt/lists/*

# # ── Working directory ─────────────────────────────────────────
# WORKDIR /app

# # ── Install Python dependencies ───────────────────────────────
# # Copy requirements first (Docker cache layer — only reinstalls
# # when requirements.txt changes, not on every code change).
# COPY requirements.txt .
# RUN pip install --no-cache-dir --upgrade pip \
#  && pip install --no-cache-dir -r requirements.txt

# # ── Install Playwright Chromium browser ───────────────────────
# RUN python -m playwright install chromium

# # ── Copy project files ────────────────────────────────────────
# COPY . .

# # ── Create data directories ───────────────────────────────────
# RUN mkdir -p data/raw data/processed data/markdown logs

# # ── Cron job: run scraper every day at 06:00 UTC ──────────────
# # Output is appended to /app/logs/cron.log so you can tail it.
# RUN echo "0 6 * * * cd /app && python main.py >> /app/logs/cron.log 2>&1" \
#     > /etc/cron.d/g7-scraper \
#  && chmod 0644 /etc/cron.d/g7-scraper \
#  && crontab /etc/cron.d/g7-scraper

# # ── Entrypoint script ─────────────────────────────────────────
# COPY docker-entrypoint.sh /docker-entrypoint.sh
# RUN chmod +x /docker-entrypoint.sh

# ENTRYPOINT ["/docker-entrypoint.sh"]


# =============================================================
# Dockerfile — G7 Government Website Scraper (Fixed)
# =============================================================
FROM python:3.12-slim AS base

# ── Install system dependencies for Playwright Chromium ──────
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    curl \
    wget \
    gnupg \
    ca-certificates \
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

# ── Set working directory ───────────────────────────────────
WORKDIR /app

# ── Copy requirements and install Python packages ───────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ── Install Playwright and Chromium ─────────────────────────
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN python -m pip install playwright --upgrade \
 && python -m playwright install chromium

# ── Copy project files ──────────────────────────────────────
COPY . .

# ── Create data & log directories ──────────────────────────
RUN mkdir -p data/raw data/processed data/markdown logs

# ── Setup cron job to run scraper every 3 days at 06:00 UTC ─
RUN echo "0 6 */3 * * cd /app && python main.py >> /app/logs/cron.log 2>&1" \
    > /etc/cron.d/g7-scraper \
 && chmod 0644 /etc/cron.d/g7-scraper \
 && crontab /etc/cron.d/g7-scraper

# ── Entrypoint script ───────────────────────────────────────
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]