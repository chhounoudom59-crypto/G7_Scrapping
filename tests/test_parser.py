# =============================================================
# tests/test_parser.py — Unit tests for parse_article()
# =============================================================

import pytest

from scraper.base_scraper import parse_article


SELECTORS = {
    "title": "h1",
    "date": "time",
    "date_attr": "datetime",
    "body": "article, main",
    "article_links": "a",
}

LONG_BODY = "Government policy matters greatly for economic stability. " * 10


def make_html(title="Test Title", date_attr="2026-03-24", body=LONG_BODY):
    return f"""
    <html>
    <head><title>{title}</title></head>
    <body>
      <main>
        <h1>{title}</h1>
        <time datetime="{date_attr}">March 24, 2026</time>
        <article><p>{body}</p></article>
      </main>
    </body>
    </html>
    """


# ─────────────────────────────────────────────────────────────
# Happy path
# ─────────────────────────────────────────────────────────────

class TestParseArticleHappyPath:
    def test_returns_dict(self):
        doc = parse_article(make_html(), "https://example.com/a", SELECTORS, "Test", "US")
        assert isinstance(doc, dict)

    def test_title_extracted(self):
        doc = parse_article(make_html(title="G7 Summit"), "https://example.com/a", SELECTORS, "Test", "US")
        assert doc is not None
        assert "G7 Summit" in doc["title"]

    def test_url_stored(self):
        url = "https://example.com/article-123"
        doc = parse_article(make_html(), url, SELECTORS, "Test", "US")
        assert doc is not None
        assert doc["url"] == url

    def test_source_stored(self):
        doc = parse_article(make_html(), "https://example.com/a", SELECTORS, "MySource", "US")
        assert doc is not None
        assert doc["source"] == "MySource"

    def test_country_stored(self):
        doc = parse_article(make_html(), "https://example.com/a", SELECTORS, "Test", "Canada")
        assert doc is not None
        assert doc["country"] == "Canada"

    def test_date_extracted_from_datetime_attr(self):
        doc = parse_article(make_html(date_attr="2026-01-15"), "https://example.com/a", SELECTORS, "Test", "US")
        assert doc is not None
        assert "2026-01-15" in doc["date"]

    def test_body_not_empty(self):
        doc = parse_article(make_html(), "https://example.com/a", SELECTORS, "Test", "US")
        assert doc is not None
        assert len(doc["body"]) > 50

    def test_word_count_is_int(self):
        doc = parse_article(make_html(), "https://example.com/a", SELECTORS, "Test", "US")
        assert doc is not None
        assert isinstance(doc["word_count"], int)
        assert doc["word_count"] > 0

    def test_unique_id_is_16_chars(self):
        doc = parse_article(make_html(), "https://example.com/a", SELECTORS, "Test", "US")
        assert doc is not None
        assert len(doc["unique_id"]) == 16

    def test_scraped_at_is_iso_string(self):
        doc = parse_article(make_html(), "https://example.com/a", SELECTORS, "Test", "US")
        assert doc is not None
        assert "T" in doc["scraped_at"]  # ISO-8601 format

    def test_prefill_title_used_when_no_h1(self):
        html = f"<html><body><main><p>{LONG_BODY}</p></main></body></html>"
        doc = parse_article(html, "https://example.com/a", SELECTORS, "Test", "US",
                            prefill_title="Prefilled Title")
        assert doc is not None
        assert "Prefilled" in doc["title"]

    def test_prefill_date_used_when_no_time_tag(self):
        html = f"<html><body><main><p>{LONG_BODY}</p></main></body></html>"
        doc = parse_article(html, "https://example.com/a", SELECTORS, "Test", "US",
                            prefill_date="2026-06-15")
        assert doc is not None
        assert "2026-06-15" in doc["date"]


# ─────────────────────────────────────────────────────────────
# Thin content (should return None)
# ─────────────────────────────────────────────────────────────

class TestParseArticleThinContent:
    def test_thin_body_returns_none(self):
        html = "<html><body><main><p>Too short.</p></main></body></html>"
        doc = parse_article(html, "https://example.com/a", SELECTORS, "Test", "US")
        assert doc is None

    def test_empty_body_returns_none(self):
        html = "<html><body><main></main></body></html>"
        doc = parse_article(html, "https://example.com/a", SELECTORS, "Test", "US")
        assert doc is None

    def test_nav_only_returns_none(self):
        html = "<html><body><nav>Home | About | Contact</nav></body></html>"
        doc = parse_article(html, "https://example.com/a", SELECTORS, "Test", "US")
        assert doc is None


# ─────────────────────────────────────────────────────────────
# Navigation noise removal
# ─────────────────────────────────────────────────────────────

class TestParseArticleNoiseRemoval:
    def test_footer_text_removed(self):
        html = f"""
        <html><body><main>
          <article><p>{LONG_BODY}</p></article>
          <footer>Copyright 2026 Government Website</footer>
        </main></body></html>
        """
        doc = parse_article(html, "https://example.com/a", SELECTORS, "Test", "US")
        assert doc is not None
        assert "Copyright 2026" not in doc["body"]

    def test_nav_text_removed(self):
        html = f"""
        <html><body><main>
          <nav>Skip to content | About | Contact</nav>
          <article><p>{LONG_BODY}</p></article>
        </main></body></html>
        """
        doc = parse_article(html, "https://example.com/a", SELECTORS, "Test", "US")
        assert doc is not None
        assert "Skip to content" not in doc["body"]

    def test_script_tag_removed(self):
        html = f"""
        <html><body><main>
          <script>alert('hello')</script>
          <article><p>{LONG_BODY}</p></article>
        </main></body></html>
        """
        doc = parse_article(html, "https://example.com/a", SELECTORS, "Test", "US")
        assert doc is not None
        assert "alert" not in doc["body"]


# ─────────────────────────────────────────────────────────────
# Edge cases
# ─────────────────────────────────────────────────────────────

class TestParseArticleEdgeCases:
    def test_broken_html_does_not_raise(self):
        broken = "<html><body><main><p>Unclosed tag"
        # Should not raise — returns None or a dict
        result = parse_article(broken, "https://example.com/a", SELECTORS, "Test", "US")
        assert result is None or isinstance(result, dict)

    def test_fallback_title_from_title_tag(self):
        html = f"""
        <html><head><title>Page Title from Head</title></head>
        <body><main><p>{LONG_BODY}</p></main></body></html>
        """
        doc = parse_article(html, "https://example.com/a", SELECTORS, "Test", "US")
        if doc:
            assert len(doc["title"]) > 0

    def test_title_truncated_to_500_chars(self):
        long_title = "A" * 600
        doc = parse_article(make_html(title=long_title), "https://example.com/a", SELECTORS, "Test", "US")
        if doc:
            assert len(doc["title"]) <= 500
