# =============================================================
# tests/test_config.py — Unit tests for config.py + sites.json
# =============================================================

import json
import os

import pytest


# ─────────────────────────────────────────────────────────────
# Config module validation
# ─────────────────────────────────────────────────────────────

class TestConfig:
    def setup_method(self):
        import config
        self.cfg = config

    def test_rate_limit_min_positive(self):
        assert self.cfg.RATE_LIMIT_MIN > 0

    def test_rate_limit_max_gte_min(self):
        assert self.cfg.RATE_LIMIT_MAX >= self.cfg.RATE_LIMIT_MIN

    def test_max_articles_positive(self):
        assert self.cfg.MAX_ARTICLES > 0

    def test_request_timeout_positive(self):
        assert self.cfg.REQUEST_TIMEOUT > 0

    def test_japan_months_back_positive(self):
        assert self.cfg.JAPAN_MONTHS_BACK > 0

    def test_headers_has_user_agent(self):
        assert "User-Agent" in self.cfg.HEADERS
        assert len(self.cfg.HEADERS["User-Agent"]) > 10

    def test_headers_has_accept(self):
        assert "Accept" in self.cfg.HEADERS

    def test_strip_params_is_set(self):
        assert isinstance(self.cfg.STRIP_PARAMS, set)
        assert "utm_source" in self.cfg.STRIP_PARAMS
        assert "fbclid" in self.cfg.STRIP_PARAMS

    def test_rss_fallback_paths_is_list(self):
        assert isinstance(self.cfg.RSS_FALLBACK_PATHS, list)
        assert len(self.cfg.RSS_FALLBACK_PATHS) > 0

    def test_sites_file_path_defined(self):
        assert hasattr(self.cfg, "SITES_FILE")

    def test_data_dirs_defined(self):
        assert hasattr(self.cfg, "DATA_DIR")
        assert hasattr(self.cfg, "MARKDOWN_DIR")
        assert hasattr(self.cfg, "PROCESSED_DIR")
        assert hasattr(self.cfg, "RAW_DIR")


# ─────────────────────────────────────────────────────────────
# sites.json validation
# ─────────────────────────────────────────────────────────────

REQUIRED_SITE_KEYS = {"name", "country", "country_code", "base_url", "selectors"}
REQUIRED_SELECTOR_KEYS = {"title", "date", "body", "article_links"}


class TestSitesJson:
    def setup_method(self):
        sites_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sites.json")
        with open(sites_path, encoding="utf-8") as f:
            self.sites = json.load(f)

    def test_sites_is_list(self):
        assert isinstance(self.sites, list)

    def test_at_least_one_site(self):
        assert len(self.sites) >= 1

    def test_all_sites_have_required_keys(self):
        for site in self.sites:
            missing = REQUIRED_SITE_KEYS - set(site.keys())
            assert not missing, f"Site '{site.get('name', '?')}' missing: {missing}"

    def test_all_names_are_strings(self):
        for site in self.sites:
            assert isinstance(site["name"], str)
            assert len(site["name"]) > 0

    def test_all_country_codes_are_lowercase(self):
        for site in self.sites:
            code = site["country_code"]
            assert code == code.lower(), f"country_code '{code}' should be lowercase"

    def test_all_base_urls_start_with_https(self):
        for site in self.sites:
            url = site["base_url"]
            assert url.startswith("http"), f"base_url should start with http(s): {url}"

    def test_all_selectors_have_required_keys(self):
        for site in self.sites:
            sel = site["selectors"]
            missing = REQUIRED_SELECTOR_KEYS - set(sel.keys())
            assert not missing, f"Site '{site['name']}' selectors missing: {missing}"

    def test_no_duplicate_country_codes(self):
        codes = [s["country_code"] for s in self.sites]
        assert len(codes) == len(set(codes)), "Duplicate country_code entries found"

    def test_no_duplicate_names(self):
        names = [s["name"] for s in self.sites]
        assert len(names) == len(set(names)), "Duplicate site name entries found"

    def test_pagination_step_positive_when_set(self):
        for site in self.sites:
            if "pagination_step" in site:
                assert site["pagination_step"] > 0, \
                    f"pagination_step must be positive in site '{site['name']}'"

    def test_max_pages_positive_when_set(self):
        for site in self.sites:
            if "max_pages" in site:
                assert site["max_pages"] > 0, \
                    f"max_pages must be positive in site '{site['name']}'"

    def test_js_required_is_bool_when_set(self):
        for site in self.sites:
            if "js_required" in site:
                assert isinstance(site["js_required"], bool), \
                    f"js_required must be bool in site '{site['name']}'"
