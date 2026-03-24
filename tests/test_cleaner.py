# =============================================================
# tests/test_cleaner.py — Unit tests for utils/cleaner.py
# =============================================================

import pytest

from utils.cleaner import (
    clean_text,
    clean_title,
    content_hash,
    normalise_date,
    unique_id,
    url_hash,
)


# ─────────────────────────────────────────────────────────────
# clean_text
# ─────────────────────────────────────────────────────────────

class TestCleanText:
    def test_empty_string(self):
        assert clean_text("") == ""

    def test_none_equiv_falsy(self):
        assert clean_text("") == ""

    def test_strips_html_tags(self):
        assert clean_text("<p>Hello</p>") == "Hello"

    def test_strips_nested_tags(self):
        assert clean_text("<div><span>World</span></div>") == "World"

    def test_decodes_amp(self):
        assert "&" in clean_text("a &amp; b")

    def test_decodes_lt_gt(self):
        result = clean_text("&lt;tag&gt;")
        assert "<" in result and ">" in result

    def test_decodes_nbsp(self):
        result = clean_text("hello&nbsp;world")
        assert "hello" in result and "world" in result

    def test_collapses_whitespace(self):
        result = clean_text("hello   world")
        assert "  " not in result

    def test_collapses_tabs(self):
        result = clean_text("hello\t\tworld")
        assert "\t" not in result

    def test_max_two_blank_lines(self):
        result = clean_text("a\n\n\n\n\nb")
        assert "\n\n\n" not in result

    def test_strips_leading_trailing_whitespace(self):
        assert clean_text("  hello  ") == "hello"

    def test_removes_control_characters(self):
        # \x01 is a control char that should be removed
        result = clean_text("hello\x01world")
        assert "\x01" not in result

    def test_normalises_unicode(self):
        # ﬁ (U+FB01 LATIN SMALL LIGATURE FI) → "fi" after NFKC
        result = clean_text("ﬁle")
        assert result == "file"


# ─────────────────────────────────────────────────────────────
# clean_title
# ─────────────────────────────────────────────────────────────

class TestCleanTitle:
    def test_empty_returns_untitled(self):
        assert clean_title("") == "Untitled"

    def test_replaces_pipe(self):
        result = clean_title("News | Government Site")
        assert "|" not in result
        assert "-" in result

    def test_removes_hash(self):
        result = clean_title("Headlines #1")
        assert "#" not in result

    def test_normal_title_unchanged(self):
        result = clean_title("G7 Summit Communiqué")
        assert "G7 Summit" in result

    def test_whitespace_only_returns_untitled(self):
        assert clean_title("   ") == "Untitled"


# ─────────────────────────────────────────────────────────────
# normalise_date
# ─────────────────────────────────────────────────────────────

class TestNormaliseDate:
    def test_empty_returns_empty(self):
        assert normalise_date("") == ""

    def test_iso_format_passthrough(self):
        assert normalise_date("2026-03-24") == "2026-03-24"

    def test_iso_with_timestamp(self):
        # Should strip everything after YYYY-MM-DD
        assert normalise_date("2026-03-24T12:00:00") == "2026-03-24"

    def test_full_month_name(self):
        assert normalise_date("March 24, 2026") == "2026-03-24"

    def test_abbreviated_month(self):
        assert normalise_date("Mar 24, 2026") == "2026-03-24"

    def test_day_month_year(self):
        assert normalise_date("24 March 2026") == "2026-03-24"

    def test_dd_slash_mm_slash_yyyy(self):
        assert normalise_date("24/03/2026") == "2026-03-24"

    def test_rss_format(self):
        # Mon, 24 Mar 2026
        assert normalise_date("Mon, 24 Mar 2026") == "2026-03-24"

    def test_german_format(self):
        # 24. March 2026
        assert normalise_date("24. March 2026") == "2026-03-24"

    def test_japanese_format(self):
        assert normalise_date("2026年03月24日") == "2026-03-24"

    def test_strips_published_prefix(self):
        assert normalise_date("Published: March 24, 2026") == "2026-03-24"

    def test_strips_date_prefix(self):
        assert normalise_date("Date: 2026-03-24") == "2026-03-24"

    def test_unparseable_returns_original(self):
        raw = "not a date at all"
        result = normalise_date(raw)
        # Should return the original string (or a best-effort parse — either is OK)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_iso_datetime_z_suffix(self):
        assert normalise_date("2026-03-24T06:00:00Z") == "2026-03-24"


# ─────────────────────────────────────────────────────────────
# content_hash, url_hash, unique_id
# ─────────────────────────────────────────────────────────────

class TestHashing:
    def test_content_hash_is_32_chars(self):
        h = content_hash("hello world")
        assert len(h) == 32

    def test_content_hash_deterministic(self):
        assert content_hash("abc") == content_hash("abc")

    def test_content_hash_different_for_different_input(self):
        assert content_hash("abc") != content_hash("xyz")

    def test_url_hash_is_16_chars(self):
        h = url_hash("https://example.com/news/article-1")
        assert len(h) == 16

    def test_url_hash_normalises_trailing_slash(self):
        # URLs with / without trailing slash should produce same hash
        h1 = url_hash("https://example.com/news/")
        h2 = url_hash("https://example.com/news")
        assert h1 == h2

    def test_url_hash_strips_utm(self):
        h1 = url_hash("https://example.com/p?a=1")
        h2 = url_hash("https://example.com/p?a=1&utm_source=twitter")
        assert h1 == h2

    def test_unique_id_is_16_chars(self):
        uid = unique_id("https://example.com/article")
        assert len(uid) == 16

    def test_unique_id_deterministic(self):
        url = "https://example.com/article"
        assert unique_id(url) == unique_id(url)

    def test_unique_id_different_for_different_urls(self):
        assert unique_id("https://example.com/a") != unique_id("https://example.com/b")
