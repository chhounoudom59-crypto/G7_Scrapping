# =============================================================
# scraper/base_scraper.py — Async Scraping Engine
# =============================================================
# This is the heart of the system. It implements the same
# 5-layer deduplication strategy as the reference scraper
# plus three URL discovery methods: RSS, Sitemap, Listing.
#
# LAYER 1 — in-memory candidates dict (keyed by normalised URL)
# LAYER 2 — JSON index loaded from disk (known articles)
# LAYER 3 — content hash (skip unchanged pages)
# LAYER 4 — HTTP conditional requests (ETag / Last-Modified)
# LAYER 5 — final guard in save_document() before writing
# =============================================================

import asyncio
import itertools
import random
from datetime import datetime, timezone
from typing import Optional, cast

import httpx
from bs4 import BeautifulSoup

from config import (
    HEADERS, RATE_LIMIT_MIN, RATE_LIMIT_MAX,
    REQUEST_TIMEOUT, MAX_ARTICLES, RSS_FALLBACK_PATHS,
)
from utils.logger     import get_logger
from utils.cleaner    import normalise_date, content_hash, url_hash, unique_id
from utils.url_utils  import normalise_url, same_domain, can_fetch, make_absolute
from utils.storage    import (
    load_index, save_index, save_document,
    load_checkpoints, save_checkpoints, save_raw_json,
)
from utils.translator import translate_to_english

log = get_logger(__name__)


# =============================================================
# HTTP helpers
# =============================================================

async def fetch_url(
    client: httpx.AsyncClient,
    url: str,
    etag: str = "",
    last_modified: str = "",
) -> tuple[Optional[str], Optional[str], Optional[str], int]:
    """
    Fetch a URL with async httpx.
    Supports HTTP conditional requests (ETag / If-Modified-Since).

    Returns: (html, new_etag, new_last_modified, status_code)
      - html is None on failure or 304 Not Modified
      - status 304 → content unchanged, skip processing
    """
    if not can_fetch(url):
        log.warning(f"  robots.txt disallows: {url}")
        return None, None, None, 403

    # Polite random delay before each request
    await asyncio.sleep(RATE_LIMIT_MIN + random.random() * (RATE_LIMIT_MAX - RATE_LIMIT_MIN))

    headers = dict(HEADERS)
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    try:
        resp = await client.get(
            url, headers=headers,
            follow_redirects=True,
            timeout=REQUEST_TIMEOUT
        )
        new_etag = resp.headers.get("ETag")
        new_lm   = resp.headers.get("Last-Modified")

        if resp.status_code == 304:
            return None, etag, last_modified, 304
        if resp.status_code == 200:
            return resp.text, new_etag, new_lm, 200

        log.warning(f"  HTTP {resp.status_code}: {url}")
        return None, None, None, resp.status_code

    except httpx.TimeoutException:
        log.warning(f"  Timeout: {url}")
        return None, None, None, 0
    except Exception as e:
        log.warning(f"  Fetch error {url}: {e}")
        return None, None, None, 0


async def fetch_url_playwright(url: str, wait_selector: str = "") -> Optional[str]:
    """
    Fetch a JavaScript-rendered page using Playwright (headless Chromium).
    Falls back to None if Playwright is not installed.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        log.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
        return None

    await asyncio.sleep(RATE_LIMIT_MIN + random.random() * (RATE_LIMIT_MAX - RATE_LIMIT_MIN))

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=HEADERS["User-Agent"],
                viewport={"width": 1280, "height": 900},
            )
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=60_000)

            # Wait for a specific element if configured
            if wait_selector:
                try:
                    await page.wait_for_selector(wait_selector, timeout=10_000)
                except Exception:
                    pass   # Continue even if selector not found

            await asyncio.sleep(3)   # Let any late JS settle
            html = await page.content()
            await browser.close()
            return html

    except Exception as e:
        log.warning(f"  Playwright error for {url}: {e}")
        return None


# =============================================================
# URL Discovery — three methods
# =============================================================

async def discover_via_rss(
    client: httpx.AsyncClient,
    rss_url: str,
    base_url: str,
) -> list[dict]:
    """
    Parse an RSS/Atom feed and return a list of
    {"url": ..., "title": ..., "date": ...} dicts.

    Tries the configured URL first, then falls back to common
    RSS paths (/feed, /rss.xml, etc.) if the feed is empty.
    """
    if not rss_url:
        return []

    # Try the configured RSS URL first
    entries = await _parse_rss(rss_url)
    if entries:
        return entries

    # Auto-try common feed paths (same domain)
    log.info("  RSS returned 0 entries — trying fallback paths...")
    from urllib.parse import urlparse
    origin = f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}"

    for path in RSS_FALLBACK_PATHS:
        fallback = origin + path
        if normalise_url(fallback) == normalise_url(rss_url):
            continue
        html, _, _, status = await fetch_url(client, fallback)
        if status == 200:
            entries = await _parse_rss(fallback)
            if entries:
                log.info(f"  RSS fallback succeeded: {fallback} → {len(entries)} entries")
                return entries

    log.info("  All RSS paths failed — relying on listing pages only")
    return []


async def _parse_rss(rss_url: str) -> list[dict]:
    """Parse a feed URL using feedparser (runs in a thread executor)."""
    log.info(f"  RSS: {rss_url}")
    try:
        import feedparser
        loop    = asyncio.get_event_loop()
        feed    = await loop.run_in_executor(None, feedparser.parse, rss_url)
        entries = []
        for entry in feed.entries:
            link = entry.get("link", "")
            if not link:
                continue
            title = entry.get("title", "")
            dp    = entry.get("published_parsed") or entry.get("updated_parsed")
            date  = (
                datetime(dp.tm_year, dp.tm_mon, dp.tm_mday,
                         dp.tm_hour, dp.tm_min, dp.tm_sec,
                         tzinfo=timezone.utc).isoformat()
                if dp else ""
            )
            entries.append({"url": link, "title": title, "date": date})
        log.info(f"  RSS → {len(entries)} entries")
        return entries
    except ImportError:
        log.warning("feedparser not installed — skipping RSS. Run: pip install feedparser")
        return []
    except Exception as e:
        log.warning(f"  RSS parse error: {e}")
        return []


async def discover_via_listing(
    client: httpx.AsyncClient,
    listing_url: str,
    link_selector: str,
    base_url: str,
    pagination_pattern: Optional[str],
    max_pages: int = 3,
    js_required: bool = False,
    pagination_step: int = 1,
    known_norm: set = None,
    wait_selector: str = "",
) -> list[str]:
    """
    Crawl paginated listing pages and return article URLs.

    Pagination:
      - If pagination_pattern contains {n}, it replaces it with
        the page offset and appends to the listing URL.
      - Stops early when an entire page consists of already-known URLs.

    Returns a flat list of raw (not normalised) article URLs.
    """
    seen_this_call: set = set()
    found_raw: list     = []

    for page_n in range(1, max_pages + 1):
        # ── Build page URL ────────────────────────────────────
        if page_n == 1:
            url = listing_url
        elif pagination_pattern is not None:
            pat = cast(str, pagination_pattern)  # narrow Optional[str] → str
            if "{n}" not in pat:
                break   # no {n} placeholder — no pagination, stop after page 1
            offset = (page_n - 1) * pagination_step
            suffix = pat.replace("{n}", str(offset))
            url = listing_url.rstrip("/") + suffix
        else:
            break   # no pagination configured, only first page

        # ── Fetch ─────────────────────────────────────────────
        if js_required:
            html = await fetch_url_playwright(url, wait_selector=wait_selector or "a[href]")
        else:
            html, _, _, status = await fetch_url(client, url)
            if status != 200:
                html = None

        if not html:
            log.warning(f"  Could not fetch listing page: {url}")
            break

        soup = BeautifulSoup(html, "lxml")

        # ── Extract links using all comma-separated selectors ─
        raw_links = []
        for sel in [s.strip() for s in link_selector.split(",")]:
            raw_links.extend(soup.select(sel))

        # Deduplicate by href within this page
        seen_hrefs: set = set()
        unique_links = []
        for a in raw_links:
            h = a.get("href", "")
            if h and h not in seen_hrefs:
                seen_hrefs.add(h)
                unique_links.append(a)

        if not unique_links:
            log.info(f"  No links on page {page_n} with selector '{link_selector}' — stopping")
            # Show a sample of what hrefs the page actually has (helps debug)
            sample = [a.get("href", "") for a in soup.find_all("a", href=True)][:10]
            if sample:
                log.debug(f"  Sample hrefs on page: {sample}")
            break

        page_new   = 0
        page_known = 0

        for a in unique_links:
            href = a.get("href", "")
            if not href or href.startswith("#") or href.startswith("javascript"):
                continue

            full      = make_absolute(href, base_url)
            full_norm = normalise_url(full)

            if full_norm in seen_this_call:
                continue   # dup within this discovery call

            seen_this_call.add(full_norm)

            if known_norm and full_norm in known_norm:
                page_known += 1
                continue   # already saved in a previous run

            found_raw.append(full)
            page_new += 1

        log.info(
            f"  Listing page {page_n} → {page_new} new | "
            f"{page_known} already saved | total queued: {len(found_raw)}"
        )

        # Early exit: full page was already known
        if known_norm and page_known > 0 and page_new == 0 and page_n > 1:
            log.info(f"  Entire page {page_n} already saved — stopping early")
            break

        if page_new == 0 and page_known == 0:
            break   # no usable links at all

    return found_raw


# =============================================================
# Article parser
# =============================================================

def parse_article(
    html: str,
    url: str,
    selectors: dict,
    source_name: str,
    country: str,
    prefill_title: str = "",
    prefill_date: str  = "",
) -> Optional[dict]:
    """
    Extract title, date, and body text from a full article HTML page.
    Returns a record dict or None if the content is too thin (<50 chars).
    """
    try:
        soup = BeautifulSoup(html, "lxml")

        # ── Title ─────────────────────────────────────────────
        title = prefill_title
        if not title:
            for sel in [s.strip() for s in selectors.get("title", "h1").split(",")]:
                tag = soup.select_one(sel)
                if tag:
                    title = tag.get_text(" ", strip=True)
                    break
        if not title:
            t = soup.find("title")
            title = t.get_text(strip=True) if t else url
        title = title[:500]

        # ── Date ──────────────────────────────────────────────
        date_str  = prefill_date
        date_attr = selectors.get("date_attr", "datetime")
        if not date_str:
            for sel in [s.strip() for s in selectors.get("date", "time").split(",")]:
                tag = soup.select_one(sel)
                if tag:
                    date_str = tag.get(date_attr, "") or tag.get_text(strip=True)
                    if date_str:
                        break

        # ── Body ──────────────────────────────────────────────
        body_tag = None
        for sel in [s.strip() for s in selectors.get("body", "article, main").split(",")]:
            body_tag = soup.select_one(sel)
            if body_tag:
                break
        if not body_tag:
            body_tag = soup.find("main") or soup.find("article") or soup.find("body")

        if body_tag:
            # Remove navigation noise
            for junk in body_tag.select(
                "nav, footer, script, style, aside, header, "
                ".skip-link, .breadcrumb, .related, .share, .social, "
                ".cookie-banner, .cookie-notice, [aria-hidden='true'], "
                ".site-header, .site-footer, .sidebar"
            ):
                junk.decompose()
            body_text = body_tag.get_text("\n", strip=True)
        else:
            body_text = ""

        import re
        body_text = re.sub(r"\n{3,}", "\n\n", body_text).strip()

        # Skip thin / empty pages (navigation pages, error pages, etc.)
        # 300 chars ≈ 50 words — filters junk like nav wrappers and widget pages
        if len(body_text) < 300:
            log.debug(f"  Thin content ({len(body_text)} chars), skipping: {url}")
            return None

        return {
            "source":     source_name,
            "country":    country,
            "title":      title,
            "date":       normalise_date(date_str),
            "url":        url,
            "body":       body_text,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "word_count": len(body_text.split()),
            "unique_id":  unique_id(url),
        }

    except Exception as e:
        log.warning(f"  Parse error {url}: {e}")
        return None


# =============================================================
# Main per-source scraper
# =============================================================

class CountryScraper:
    """
    Scrapes one source (country) using all three discovery methods
    and 5-layer deduplication.

    Usage:
        scraper = CountryScraper()
        n_saved = await scraper.scrape_source(client, site_config)
    """

    def __init__(self):
        self.checkpoints = load_checkpoints()
        self._indexes: dict = {}   # country_code → {norm_url: record}

    def get_index(self, country_code: str) -> dict:
        """Load and cache the dedup index for a country."""
        if country_code not in self._indexes:
            self._indexes[country_code] = load_index(country_code)
            log.info(
                f"  Dedup index loaded for {country_code}: "
                f"{len(self._indexes[country_code])} known articles"
            )
        return self._indexes[country_code]

    def flush_index(self, country_code: str) -> None:
        """Persist the in-memory index to disk."""
        if country_code in self._indexes:
            save_index(country_code, self._indexes[country_code])

    def _get_cp(self, source: str, key: str) -> str:
        return self.checkpoints.get(source, {}).get(key, "")

    def _set_cp(self, source: str, key: str, value: str) -> None:
        self.checkpoints.setdefault(source, {})[key] = value
        save_checkpoints(self.checkpoints)

    async def scrape_source(self, client: httpx.AsyncClient, site: dict) -> dict:
        """
        Full pipeline for one country site:
          1. Build candidate URL list (RSS → listing)
          2. Fetch each candidate (with ETag / content-hash skipping)
          3. Parse article (title, date, body)
          4. Save to .md and JSON index (5-layer dedup)
          5. Flush index to disk

        Returns stats dict: {saved, skipped, errors}
        """
        name         = site["name"]
        country      = site["country"]
        country_code = site["country_code"]
        base_url     = site["base_url"]
        selectors    = site["selectors"]
        js_required  = site.get("js_required", False)
        extra_doms   = site.get("extra_domains", [])

        # url_rewrite: {"from": "/breg-de/", "to": "/breg-en/"}
        # Applied to EVERY discovered URL (RSS + listing) so that any
        # native-language URL is silently swapped to its English version
        # before being fetched, parsed, or stored.
        url_rewrite  = site.get("url_rewrite")   # None means no rewrite

        log.info("")
        log.info("=" * 60)
        log.info(f"  Source : {name}")
        log.info(f"  Country: {country}  [js={js_required}]")
        if url_rewrite:
            rw_from = url_rewrite.get('from', '')
            rw_to   = url_rewrite.get('to', '')
            log.info(f"  URL rewrite: {rw_from} → {rw_to}")
        log.info("=" * 60)

        # ── LAYER 2: load dedup index ─────────────────────────
        index      = self.get_index(country_code)
        known_norm = set(index.keys())

        # ── LAYER 1: build candidates dict ───────────────────
        # Keyed by normalised URL — merging RSS + listing never
        # creates duplicates because the key is always normalised.
        candidates: dict = {}

        def _rewrite(url: str) -> str:
            # Replace native-language path segments with English equivalents.
            # e.g. /breg-de/ → /breg-en/  (Germany)
            #      /it/      → /en/        (Italy)
            if url_rewrite and url_rewrite.get("from") and url_rewrite.get("to"):
                return url.replace(url_rewrite["from"], url_rewrite["to"])
            return url

        def _add(raw_url: str, title: str = "", date: str = "") -> None:
            # Rewrite language path BEFORE dedup comparison so we never
            # store or fetch the native-language version.
            raw_url = _rewrite(raw_url)
            norm    = normalise_url(raw_url)
            if norm not in known_norm and norm not in candidates:
                candidates[norm] = {"url": raw_url, "title": title, "date": date}

        # A) RSS / Atom feed (fastest, most structured)
        rss_url = site.get("rss_url", "")
        if rss_url:
            for e in await discover_via_rss(client, rss_url, base_url):
                _add(e["url"], e.get("title", ""), e.get("date", ""))
            log.info(f"  After RSS: {len(candidates)} new candidates")

        # B) Listing pages (HTML scraping of index pages)
        listing_urls = site.get("listing_urls", [])

        # Special case: Japan uses monthly archive URLs
        if name == "Government of Japan":
            from config import JAPAN_MONTHS_BACK
            now = datetime.now(timezone.utc)
            for i in range(JAPAN_MONTHS_BACK):
                month = now.month - i
                year  = now.year
                while month <= 0:
                    month += 12
                    year  -= 1
                listing_urls.append(
                    f"https://japan.kantei.go.jp/news/{year}{month:02d}/index.html"
                )
            log.info(f"  Japan: generated {len(listing_urls)} monthly archive URLs")

        for listing_url in listing_urls:
            urls = await discover_via_listing(
                client             = client,
                listing_url        = listing_url,
                link_selector      = selectors["article_links"],
                base_url           = base_url,
                pagination_pattern = site.get("pagination"),
                max_pages          = site.get("max_pages", 3),
                js_required        = js_required,
                pagination_step    = site.get("pagination_step", 1),
                known_norm         = known_norm,
                wait_selector      = site.get("wait_selector", ""),
            )
            for raw in urls:
                _add(raw)
            log.info(f"  After listing {listing_url[-55:]}: {len(candidates)} candidates total")

        if not candidates:
            log.info(f"  No new URLs for {name} — all already saved.")
            return {"saved": 0, "skipped": len(known_norm), "errors": 0}

        log.info(f"  Total new candidates to fetch: {len(candidates)}")

        # ── Fetch, parse, save ────────────────────────────────
        saved   = 0
        skipped = 0
        errors  = 0
        raw_records = []

        for norm, item in itertools.islice(candidates.items(), MAX_ARTICLES):
            url = item["url"]

            # Skip off-domain links
            if not same_domain(url, base_url, extra_doms):
                skipped += 1
                continue

            cp_key       = url_hash(url)
            saved_etag   = self._get_cp(name, f"{cp_key}_etag")
            saved_lm     = self._get_cp(name, f"{cp_key}_lm")
            saved_chash  = self._get_cp(name, f"{cp_key}_chash")

            # ── LAYER 4: HTTP conditional request ────────────
            if js_required:
                html     = await fetch_url_playwright(url, site.get("wait_selector", ""))
                new_etag = new_lm = None
                status   = 200 if html else 0
            else:
                html, new_etag, new_lm, status = await fetch_url(
                    client, url, etag=saved_etag, last_modified=saved_lm
                )

            if status == 304:
                log.debug(f"  304 Not Modified (unchanged): {url}")
                skipped += 1
                continue
            if not html or status != 200:
                errors += 1
                continue

            # ── LAYER 3: content hash ─────────────────────────
            chash = content_hash(html)
            if chash == saved_chash:
                log.debug(f"  Content unchanged: {url}")
                skipped += 1
                if new_etag:
                    self._set_cp(name, f"{cp_key}_etag", new_etag)
                if new_lm:
                    self._set_cp(name, f"{cp_key}_lm", new_lm)
                continue

            # ── Parse article ─────────────────────────────────
            doc = parse_article(
                html         = html,
                url          = url,
                selectors    = selectors,
                source_name  = name,
                country      = country,
                prefill_title= item.get("title", ""),
                prefill_date = item.get("date", ""),
            )

            if doc:
                # ── Translate to English (title + body) ──────────
                doc["title"] = translate_to_english(doc["title"])
                doc["body"]  = translate_to_english(doc["body"])
                doc["word_count"] = len(doc["body"].split())

                raw_records.append(doc)
                # ── LAYER 5: final dedup guard inside save_document ──
                if save_document(doc, country_code, index):
                    saved += 1
                    known_norm.add(norm)   # keep in-memory set in sync
                else:
                    skipped += 1
            else:
                skipped += 1

            # Persist checkpoint data for this URL
            if new_etag:
                self._set_cp(name, f"{cp_key}_etag", new_etag)
            if new_lm:
                self._set_cp(name, f"{cp_key}_lm", new_lm)
            self._set_cp(name, f"{cp_key}_chash", chash)

        # ── Save raw JSON backup for this source ──────────────
        if raw_records:
            save_raw_json(country_code, raw_records)

        # ── Flush index to disk once (not per-article) ────────
        self.flush_index(country_code)

        log.info(
            f"  {name} → SAVED: {saved} | "
            f"SKIPPED: {skipped} | ERRORS: {errors}"
        )

        return {"saved": saved, "skipped": skipped, "errors": errors}
