# 🌍 G7 Government Website Scraper — v2

A **production-quality async Python pipeline** that scrapes official government websites for all 7 G7 nations. Uses RSS feeds as the primary source, HTML listing pages as fallback, and implements **5-layer deduplication** to ensure clean, non-redundant data across runs.

---

## 📁 Project Structure

```
g7_scraper/
│── main.py                    ← Async orchestrator — run this
│── sites.json                 ← All 7 site configs (URLs, RSS, selectors)
│── config.py                  ← Paths, rate limits, behaviour flags
│── requirements.txt
│
│── scraper/
│    ├── base_scraper.py       ← Core async engine (fetch, parse, dedup, save)
│    ├── usa.py                ← White House
│    ├── uk.py                 ← GOV.UK
│    ├── canada.py             ← Canada.ca / pm.gc.ca
│    ├── france.py             ← gouvernement.fr  (Playwright)
│    ├── germany.py            ← bundesregierung.de  (Playwright)
│    ├── italy.py              ← governo.it
│    └── japan.py              ← japan.kantei.go.jp (monthly archives)
│
│── utils/
│    ├── cleaner.py            ← Text cleaning, date normalisation, hashing
│    ├── storage.py            ← Checkpoints, index, JSON + Markdown writes
│    ├── url_utils.py          ← URL normalisation, robots.txt, same_domain
│    └── logger.py             ← Coloured console + rotating file logger
│
│── data/
│    ├── raw/                  ← Raw JSON records per country
│    ├── processed/            ← Dedup indexes, checkpoints, summary report
│    └── markdown/             ← ✅ Final output: usa.md, uk.md, …
│
└── logs/                      ← Daily rotating log files
```

---

## ⚡ Quick Start

### 1 — Install dependencies

```bash
pip install -r requirements.txt
```

### 2 — Install Playwright browsers  *(France & Germany only)*

```bash
playwright install chromium
```

### 3 — Run

```bash
python main.py
```

Results appear in `data/markdown/` — one `.md` file per country.

---

## 🔎 How URL Discovery Works

For each country the scraper tries **three methods** in order:

```
① RSS / Atom feed  ────────────────────────────────────────────
│  Fastest. Structured. Returns titles + dates pre-parsed.
│  Most government sites publish a public feed.
│
② HTML Listing pages  ─────────────────────────────────────────
│  Crawls the news index page and follows article links.
│  Supports ?page={n} style pagination.
│  Uses Playwright for JS-heavy sites (France, Germany).
│
③ Japan monthly archives  ─────────────────────────────────────
   kantei.go.jp has no RSS. The scraper generates monthly
   archive URLs going back 24 months automatically.
```

All three methods feed into one **candidates dict keyed by normalised URL** — so even if the same article appears in RSS *and* the listing page, it is fetched only once.

---

## 🛡️ 5-Layer Deduplication

```
Layer 1 — In-memory candidates dict (this run)
          Keyed by normalised URL from the moment of discovery.
          RSS + listing results are merged — no double-fetches.

Layer 2 — JSON index loaded from disk (previous runs)
          data/processed/<country>_articles.json
          Any URL already saved is skipped before any HTTP request.

Layer 3 — Content hash (MD5 of raw HTML)
          If the page content hasn't changed since last scrape,
          skip parse + write entirely (even if ETag is missing).

Layer 4 — HTTP conditional requests
          ETag / If-Modified-Since headers.
          Server returns 304 → skip without downloading the body.

Layer 5 — Final guard in save_document()
          Re-checks the in-memory index right before writing to .md.
          Catches any edge-case duplicate that slipped through layers 1–4.
```

---

## 📄 Markdown Output Format

One file per country in `data/markdown/`:

```markdown
# Country: United States

*Last updated: 2026-03-23 14:00 UTC*

---

### President Signs Executive Order on AI Safety

- **Source:** White House
- **URL:** https://www.whitehouse.gov/briefing-room/...
- **Published Date:** 2026-03-20
- **Scraped Date:** 2026-03-23
- **Word Count:** 847
- **Unique ID:** `a1b2c3d4e5f6g7h8`

#### Content:

Today, the President signed an Executive Order directing federal
agencies to...

---
```

---

## 🌐 G7 Countries & Sources

| Country        | Primary Source             | RSS? | JS? |
|----------------|----------------------------|------|-----|
| United States  | whitehouse.gov             | ✅   | ❌  |
| United Kingdom | gov.uk                     | ✅   | ❌  |
| Canada         | pm.gc.ca / canada.ca       | ✅   | ❌  |
| France         | gouvernement.fr            | ✅   | ✅  |
| Germany        | bundesregierung.de         | ✅   | ✅  |
| Italy          | governo.it                 | ✅   | ❌  |
| Japan          | japan.kantei.go.jp         | ❌   | ❌  |

---

## ⚙️ Key Settings (`config.py`)

| Setting             | Default | Description                              |
|---------------------|---------|------------------------------------------|
| `RATE_LIMIT_MIN`    | 1.5s    | Min delay between requests               |
| `RATE_LIMIT_MAX`    | 3.0s    | Max delay between requests               |
| `MAX_ARTICLES`      | 99999   | Max articles per source per run          |
| `JAPAN_MONTHS_BACK` | 24      | How many months of archives to check     |
| `REQUEST_TIMEOUT`   | 30s     | HTTP timeout per request                 |

---

## 🔁 Running on a Schedule (Cron)

Run every day at 6 AM and only **new content** is saved:

```cron
0 6 * * * cd /path/to/g7_scraper && python main.py >> logs/cron.log 2>&1
```

---

## ➕ Adding a New Country

1. Add an entry to `sites.json` following the existing format
2. Create `scraper/newcountry.py` (inherit from `CountryScraper`)
3. Add the site dict to `main.py` (or it's auto-loaded from `sites.json`)

That's it — all scraping logic is in `base_scraper.py`.

---

## 📦 Dependencies

| Package           | Purpose                              |
|-------------------|--------------------------------------|
| `httpx[http2]`    | Async HTTP client with HTTP/2        |
| `beautifulsoup4`  | HTML parsing                         |
| `lxml`            | Fast HTML/XML parser backend         |
| `feedparser`      | RSS/Atom feed parsing                |
| `playwright`      | Headless browser for JS-heavy sites  |
| `python-dateutil` | Flexible date string parsing         |
| `colorlog`        | Coloured console log output          |
