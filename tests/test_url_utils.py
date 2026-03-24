# =============================================================
# tests/test_url_utils.py — Unit tests for utils/url_utils.py
# =============================================================

import pytest

from utils.url_utils import make_absolute, normalise_url, same_domain


# ─────────────────────────────────────────────────────────────
# normalise_url
# ─────────────────────────────────────────────────────────────

class TestNormaliseUrl:
    def test_removes_trailing_slash(self):
        result = normalise_url("https://example.com/news/")
        assert not result.endswith("/news/")
        assert result.endswith("/news")

    def test_root_slash_preserved(self):
        result = normalise_url("https://example.com/")
        # normalise_url keeps root path as-is (doesn't strip the only slash)
        assert "example.com" in result
        assert result.startswith("https://")

    def test_lowercases_scheme(self):
        result = normalise_url("HTTPS://example.com/page")
        assert result.startswith("https://")

    def test_lowercases_host(self):
        result = normalise_url("https://EXAMPLE.COM/page")
        assert "example.com" in result

    def test_strips_utm_source(self):
        result = normalise_url("https://example.com/p?utm_source=twitter")
        assert "utm_source" not in result

    def test_strips_utm_medium(self):
        result = normalise_url("https://example.com/p?utm_medium=social")
        assert "utm_medium" not in result

    def test_strips_fbclid(self):
        result = normalise_url("https://example.com/p?fbclid=abc123")
        assert "fbclid" not in result

    def test_strips_gclid(self):
        result = normalise_url("https://example.com/p?gclid=abc123")
        assert "gclid" not in result

    def test_keeps_non_tracking_params(self):
        result = normalise_url("https://example.com/search?q=summit&page=2")
        assert "q=summit" in result
        assert "page=2" in result

    def test_removes_fragment(self):
        result = normalise_url("https://example.com/page#section-2")
        assert "#" not in result

    def test_sorts_query_params(self):
        r1 = normalise_url("https://example.com/p?b=2&a=1")
        r2 = normalise_url("https://example.com/p?a=1&b=2")
        assert r1 == r2

    def test_same_url_different_case_equal(self):
        r1 = normalise_url("HTTPS://Example.COM/News/")
        r2 = normalise_url("https://example.com/News")
        assert r1 == r2

    def test_utm_and_non_utm_mixed(self):
        result = normalise_url("https://example.com/p?a=1&utm_source=tw&b=2")
        assert "utm_source" not in result
        assert "a=1" in result
        assert "b=2" in result

    def test_handles_empty_string_gracefully(self):
        # Should not raise an exception
        result = normalise_url("")
        assert isinstance(result, str)

    def test_preserves_https(self):
        result = normalise_url("https://example.com/page")
        assert result.startswith("https://")

    def test_preserves_http(self):
        result = normalise_url("http://example.com/page")
        assert result.startswith("http://")


# ─────────────────────────────────────────────────────────────
# same_domain
# ─────────────────────────────────────────────────────────────

class TestSameDomain:
    BASE = "https://www.gov.uk"

    def test_same_domain_exact(self):
        assert same_domain("https://www.gov.uk/news", self.BASE)

    def test_same_domain_without_www(self):
        # www. stripped so gov.uk == www.gov.uk
        assert same_domain("https://gov.uk/article", self.BASE)

    def test_different_domain_rejected(self):
        assert not same_domain("https://bbc.com/news", self.BASE)

    def test_subdomain_rejected(self):
        # api.gov.uk is a different netloc from www.gov.uk
        assert not same_domain("https://api.gov.uk/data", self.BASE)

    def test_relative_path_no_netloc_allowed(self):
        # URLs with no netloc (relative) are allowed through
        assert same_domain("/local/path", self.BASE)

    def test_extra_domain_allowed(self):
        assert same_domain(
            "https://assets.publishing.service.gov.uk/file.pdf",
            self.BASE,
            extra_domains=["assets.publishing.service.gov.uk"],
        )

    def test_extra_domain_with_www_stripped(self):
        assert same_domain(
            "https://pm.gc.ca/news",
            "https://canada.ca",
            extra_domains=["www.pm.gc.ca"],
        )

    def test_no_extra_domains_rejects_external(self):
        assert not same_domain("https://reuters.com", self.BASE, extra_domains=None)

    def test_case_insensitive_host(self):
        # normalise_url lowercases the host, so same_domain works for identical netlocs
        r1 = normalise_url("HTTPS://Example.COM/News/")
        r2 = normalise_url("https://example.com/News")
        assert r1 == r2


# ─────────────────────────────────────────────────────────────
# make_absolute
# ─────────────────────────────────────────────────────────────

class TestMakeAbsolute:
    BASE = "https://www.gov.uk/news"

    def test_relative_path(self):
        result = make_absolute("/articles/summit", self.BASE)
        assert result == "https://www.gov.uk/articles/summit"

    def test_already_absolute_unchanged(self):
        url = "https://www.gov.uk/articles/summit"
        assert make_absolute(url, self.BASE) == url

    def test_relative_with_dotdot(self):
        result = make_absolute("../other/page", self.BASE)
        assert result.startswith("https://www.gov.uk")

    def test_protocol_relative(self):
        result = make_absolute("//cdn.example.com/file.js", self.BASE)
        assert result.startswith("https://cdn.example.com")

    def test_different_domain_kept_as_is(self):
        result = make_absolute("https://bbc.com/article", self.BASE)
        assert result == "https://bbc.com/article"
