# =============================================================
# utils/cleaner.py — Text Cleaning, Date Parsing, Hashing
# =============================================================

import re
import hashlib
import unicodedata
from datetime import datetime, timezone


def clean_text(text: str) -> str:
    """Full cleaning pipeline: normalise unicode, strip tags, collapse whitespace."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"<[^>]+>", " ", text)           # strip HTML tags
    # Decode common HTML entities
    for entity, char in {
        "&amp;": "&", "&lt;": "<", "&gt;": ">",
        "&quot;": '"', "&apos;": "'", "&nbsp;": " ",
        "&mdash;": "—", "&ndash;": "–", "&hellip;": "…",
    }.items():
        text = text.replace(entity, char)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)       # remaining named entities
    text = re.sub(r"&#\d+;", " ", text)             # numeric entities
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)  # control chars
    text = re.sub(r"[ \t]+", " ", text)             # collapse spaces/tabs
    text = re.sub(r"\n{3,}", "\n\n", text)          # max 2 blank lines
    return text.strip()


def clean_title(title: str) -> str:
    """Lighter cleaning for titles — keeps punctuation, strips Markdown-breakers."""
    if not title:
        return "Untitled"
    title = clean_text(title)
    title = title.replace("|", "-").replace("#", "")
    return title.strip() or "Untitled"


def normalise_date(raw: str) -> str:
    """
    Parse a messy date string → ISO-8601 YYYY-MM-DD.
    Handles all common government site date formats including Japanese.
    Returns the original string unchanged if nothing matches.
    """
    if not raw:
        return ""
    raw = raw.strip()

    # Already in ISO format?
    if re.match(r"\d{4}-\d{2}-\d{2}", raw):
        return raw[:10]

    # Strip common prefixes like "Published:", "Date:", etc.
    raw = re.sub(r"(?i)(published|posted|updated|date)[:\s\-]+", "", raw).strip()

    formats = [
        "%B %d, %Y",           # March 23, 2026
        "%b %d, %Y",           # Mar 23, 2026
        "%d %B %Y",            # 23 March 2026
        "%d %b %Y",            # 23 Mar 2026
        "%d/%m/%Y",            # 23/03/2026
        "%m/%d/%Y",            # 03/23/2026
        "%Y/%m/%d",            # 2026/03/23
        "%d-%m-%Y",            # 23-03-2026
        "%d. %B %Y",           # 23. March 2026  (German)
        "%Y年%m月%d日",         # 2026年03月23日  (Japanese)
        "%a, %d %b %Y",        # Mon, 23 Mar 2026 (RSS)
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
    ]

    short = raw[:40]
    for fmt in formats:
        try:
            return datetime.strptime(short, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Last resort: dateutil
    try:
        from dateutil import parser as du
        return du.parse(raw, fuzzy=True).strftime("%Y-%m-%d")
    except Exception:
        pass

    return raw   # return as-is if all parsing fails


def content_hash(text: str) -> str:
    """MD5 of content — used to detect unchanged pages (fast, not security-critical)."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def url_hash(url: str) -> str:
    """16-char SHA-256 of the normalised URL — used as a stable checkpoint key."""
    from utils.url_utils import normalise_url
    return hashlib.sha256(normalise_url(url).encode()).hexdigest()[:16]


def unique_id(url: str) -> str:
    """16-char SHA-256 of the URL — stored as record unique_id."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]
