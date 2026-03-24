#!/usr/bin/env python3
# =============================================================
# main.py — G7 Government Website Scraper  (v2 — async edition)
# =============================================================
#
# Run with:
#     python main.py
#
# What this does:
#   1. Reads sites.json for all 7 G7 country configurations
#   2. Runs each country scraper sequentially (async inside each)
#   3. Handles errors per-country — one failure never stops others
#   4. Writes results to data/markdown/<country>.md (append-only)
#   5. Saves a summary report to data/processed/summary_report.md
#   6. Prints a formatted summary table at the end
#
# All scraping logic lives in scraper/base_scraper.py.
# All site configs (URLs, selectors, RSS) live in sites.json.
# =============================================================

import asyncio
import json
import os
import sys
from datetime import datetime, timezone

# Allow imports relative to project root regardless of where
# the script is invoked from.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx

from config import SITES_FILE
from utils.logger  import get_logger
from utils.storage import save_summary_report
from scraper.base_scraper import CountryScraper

log = get_logger("main")


BANNER = """
╔══════════════════════════════════════════════════════════════╗
║        G7 GOVERNMENT WEBSITE SCRAPER  (v2 — async)         ║
║  RSS + Listing discovery · 5-layer dedup · Append-only MD  ║
╚══════════════════════════════════════════════════════════════╝
"""


async def run_all() -> None:
    """
    Main async orchestrator.

    Loads sites.json, creates one shared CountryScraper instance
    (which holds the shared checkpoint and index caches), then
    iterates through every site sequentially.

    Sequential (not concurrent) keeps us polite to government
    servers and makes logs easy to read.  The async event loop
    is still used inside each source for non-blocking I/O.
    """
    start_time = datetime.now(timezone.utc)
    print(BANNER)

    # ── Load site configurations ──────────────────────────────
    if not os.path.exists(SITES_FILE):
        log.error(f"sites.json not found at {SITES_FILE}")
        log.error("Make sure sites.json is in the same directory as main.py")
        return

    with open(SITES_FILE, "r", encoding="utf-8") as f:
        sites = json.load(f)

    log.info(f"Loaded {len(sites)} site configurations from sites.json")
    log.info("Output: data/markdown/  |  Index: data/processed/")
    log.info("")

    # ── Create one shared scraper instance ───────────────────
    # Sharing the instance means the checkpoint cache and all
    # country indexes are loaded once and reused across sources.
    scraper = CountryScraper()

    # ── Per-country stats ─────────────────────────────────────
    summary: dict = {}

    # ── Shared HTTP client (HTTP/2, connection pooling) ───────
    # HTTP/2 disabled — some gov sites return 'stream closed' errors with h2
    async with httpx.AsyncClient(
        http2=False,
        limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        timeout=httpx.Timeout(30.0, connect=10.0),
        follow_redirects=True,
    ) as client:

        for site in sites:
            name         = site["name"]
            country_code = site["country_code"]

            log.info(f"Starting: {name} ({country_code.upper()})")

            try:
                stats = await scraper.scrape_source(client, site)
                summary[country_code] = stats

            except Exception as e:
                log.error(
                    f"Fatal error scraping {name}: {e}",
                    exc_info=True
                )
                summary[country_code] = {"saved": 0, "skipped": 0, "errors": 1}

            # Small pause between countries (polite crawling)
            log.info(f"Finished {name}. Pausing before next country...")
            await asyncio.sleep(3)

    # ── Save summary report ───────────────────────────────────
    report_path = save_summary_report(summary)

    # ── Final summary table ───────────────────────────────────
    elapsed = int((datetime.now(timezone.utc) - start_time).total_seconds())

    print("\n" + "=" * 62)
    print("  G7 Scraper — Run Complete")
    print("=" * 62)
    print(f"  {'Country':<14}  {'Saved':>7}  {'Skipped':>9}  {'Errors':>7}")
    print("  " + "-" * 46)

    total_saved   = 0
    total_skipped = 0
    total_errors  = 0

    for code, stats in summary.items():
        s = stats.get("saved",   0)
        k = stats.get("skipped", 0)
        e = stats.get("errors",  0)
        total_saved   += s
        total_skipped += k
        total_errors  += e
        # Mark countries with errors in red (if terminal supports it)
        flag = " ⚠" if e > 0 else ""
        print(f"  {code.upper():<14}  {s:>7}  {k:>9}  {e:>7}{flag}")

    print("  " + "-" * 46)
    print(f"  {'TOTAL':<14}  {total_saved:>7}  {total_skipped:>9}  {total_errors:>7}")
    print("=" * 62)
    print(f"  ⏱  Elapsed    : {elapsed}s")
    print(f"  📄 Summary    : {report_path}")
    print("  📁 Markdown   : data/markdown/")
    print("  🗂  Index      : data/processed/")
    print("  📋 Checkpoints: data/processed/checkpoints.json")
    print("=" * 62)
    print()


if __name__ == "__main__":
    asyncio.run(run_all())
