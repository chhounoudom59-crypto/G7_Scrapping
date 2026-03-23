# =============================================================
# utils/storage.py — Checkpoints, Index, JSON & Markdown
# =============================================================
# Manages all on-disk state:
#   • checkpoints.json  — ETag / Last-Modified / content-hash per URL
#   • <country>_articles.json — full URL index for deduplication
#   • data/markdown/<country>.md — append-only human-readable output
#   • data/raw/<country>_raw.json — raw record backup
# =============================================================

import os
import json
import re
from datetime import datetime, timezone

from config import PROCESSED_DIR, MARKDOWN_DIR, RAW_DIR, CHECKPOINT_FILE
from utils.logger import get_logger

log = get_logger(__name__)


# ── Ensure directories exist ──────────────────────────────────
def _ensure_dirs():
    for d in (PROCESSED_DIR, MARKDOWN_DIR, RAW_DIR):
        os.makedirs(d, exist_ok=True)


# ── Checkpoint helpers (ETag / LM / content-hash per URL) ─────

def load_checkpoints() -> dict:
    """Load the checkpoint file from disk. Returns {} if not found."""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.warning(f"Checkpoint file unreadable: {e} — starting fresh.")
    return {}


def save_checkpoints(data: dict) -> None:
    """Persist checkpoints dict to disk."""
    _ensure_dirs()
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Article index (dedup ground truth per country) ────────────

def _index_path(country_code: str) -> str:
    """Path to the JSON index file for a country."""
    _ensure_dirs()
    return os.path.join(PROCESSED_DIR, f"{country_code}_articles.json")


def load_index(country_code: str) -> dict:
    """
    Load {normalised_url: record} for all previously saved articles.
    Returns {} if the country has never been scraped before.
    """
    path = _index_path(country_code)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                records = json.load(f)
            from utils.url_utils import normalise_url
            return {normalise_url(r["url"]): r for r in records if r.get("url")}
        except Exception as e:
            log.warning(f"Could not load index for {country_code}: {e}")
    return {}


def save_index(country_code: str, index: dict) -> None:
    """Write the in-memory index back to disk, sorted by date descending."""
    _ensure_dirs()
    path    = _index_path(country_code)
    records = sorted(index.values(), key=lambda x: x.get("date", ""), reverse=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    log.debug(f"Index saved for {country_code}: {len(records)} articles → {path}")


# ── Raw JSON backup ───────────────────────────────────────────

def save_raw_json(country_code: str, records: list) -> None:
    """Append raw records to data/raw/<country>_raw.json."""
    _ensure_dirs()
    path     = os.path.join(RAW_DIR, f"{country_code}_raw.json")
    existing = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []
    combined = existing + records
    with open(path, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)


# ── Markdown output ───────────────────────────────────────────

def _md_path(country_code: str) -> str:
    _ensure_dirs()
    return os.path.join(MARKDOWN_DIR, f"{country_code}.md")


def save_document(doc: dict, country_code: str, index: dict) -> bool:
    """
    Layer 5 (final dedup guard): write one article to .md and update index.
    Returns True if saved, False if it was a duplicate caught at write time.

    The index is updated IN MEMORY immediately — the caller must call
    save_index() after the source batch finishes to persist to disk.
    """
    from utils.url_utils import normalise_url
    from utils.cleaner import content_hash

    norm = normalise_url(doc["url"])
    if norm in index:
        log.debug(f"Duplicate at write time: {doc['title'][:60]}")
        return False

    md_path = _md_path(country_code)

    # ── Write country header for brand-new files ──────────────
    if not os.path.exists(md_path) or os.path.getsize(md_path) == 0:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Country: {doc['country']}\n\n")
            f.write(f"*Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*\n\n")
            f.write("---\n\n")

    # ── Build the article block ───────────────────────────────
    block = (
        f"### {doc['title']}\n\n"
        f"- **Source:** {doc['source']}\n"
        f"- **URL:** {doc['url']}\n"
        f"- **Published Date:** {doc.get('date', 'N/A')}\n"
        f"- **Scraped Date:** {doc.get('scraped_at', '')[:10]}\n"
        f"- **Word Count:** {doc.get('word_count', 0)}\n"
        f"- **Unique ID:** `{doc.get('unique_id', '')}`\n\n"
        f"#### Content:\n\n"
        f"{doc['body']}\n\n"
        f"---\n\n"
    )

    with open(md_path, "a", encoding="utf-8") as f:
        f.write(block)

    # ── Update in-memory index immediately ───────────────────
    index[norm] = {
        "url":          doc["url"],
        "title":        doc["title"],
        "date":         doc.get("date", ""),
        "source":       doc["source"],
        "scraped_at":   doc.get("scraped_at", ""),
        "content_hash": content_hash(doc["body"]),
        "unique_id":    doc.get("unique_id", ""),
    }

    log.info(f"  ✅ Saved: {doc['title'][:70]}")
    return True


# ── Summary report ────────────────────────────────────────────

def save_summary_report(summary: dict) -> str:
    """Write a Markdown summary report after all countries finish."""
    _ensure_dirs()
    path = os.path.join(PROCESSED_DIR, "summary_report.md")
    now  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    total_saved   = sum(v.get("saved",   0) for v in summary.values())
    total_skipped = sum(v.get("skipped", 0) for v in summary.values())
    total_errors  = sum(v.get("errors",  0) for v in summary.values())

    lines = [
        "# G7 Scraper — Summary Report",
        f"\n**Run Date:** {now}\n",
        "---\n",
        "## Per-Country Results\n",
        "| Country        | Saved | Skipped (Dedup) | Errors |",
        "|----------------|------:|----------------:|-------:|",
    ]
    for code, s in summary.items():
        lines.append(
            f"| {code.upper():<14} | {s.get('saved',0):>5} "
            f"| {s.get('skipped',0):>15} "
            f"| {s.get('errors',0):>6} |"
        )
    lines += [
        "",
        "---\n",
        "## Totals\n",
        f"- **New Records Saved:** {total_saved}",
        f"- **Duplicates Skipped:** {total_skipped}",
        f"- **Errors:** {total_errors}",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    log.info(f"Summary report → {path}")
    return path
