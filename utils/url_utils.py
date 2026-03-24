# =============================================================
# utils/url_utils.py — URL Normalisation & robots.txt
# =============================================================
# These functions are the foundation of all deduplication logic.
# Two URLs pointing to the same article must compare EQUAL so
# we never save the same article twice, even if one link has a
# trailing slash, http vs https, or extra UTM parameters.
# =============================================================

import urllib.robotparser
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode, urljoin

from config import STRIP_PARAMS, HEADERS

# Cache of parsed robots.txt — loaded once per domain per run
_robots_cache: dict = {}


def normalise_url(url: str) -> str:
    """
    Make URL variants of the same page compare equal:
      • lowercase scheme and host
      • strip trailing slash from path (unless path is just "/")
      • remove tracking params (utm_*, fbclid, gclid, ref, etc.)
      • sort remaining query params for stable string comparison
      • drop the #fragment

    Examples:
      http://Example.com/News/  →  https://example.com/News
      https://x.com/p?a=1&utm_source=tw  →  https://x.com/p?a=1
    """
    try:
        p      = urlparse(url.strip())
        # Preserve the original scheme; only default to https for schemeless URLs
        scheme = p.scheme.lower() if p.scheme else "https"
        netloc = p.netloc.lower()
        path   = p.path.rstrip("/") or "/"
        qs     = parse_qs(p.query, keep_blank_values=False)
        qs     = {k: v for k, v in qs.items() if k.lower() not in STRIP_PARAMS}
        query  = urlencode(sorted(qs.items()), doseq=True)
        return urlunparse((scheme, netloc, path, "", query, ""))
    except Exception:
        return url.strip()


def same_domain(url: str, base_url: str, extra_domains: list | None = None) -> bool:
    """
    Return True if url belongs to the same domain as base_url,
    or to any of the optional extra_domains.

    Strips 'www.' so that http://example.com and
    http://www.example.com are treated as the same domain.
    """
    url_netloc  = urlparse(url).netloc.lstrip("www.").lower()
    base_netloc = urlparse(base_url).netloc.lstrip("www.").lower()
    if not url_netloc:
        return True
    if url_netloc == base_netloc:
        return True
    if extra_domains:
        for d in extra_domains:
            if url_netloc == d.lstrip("www.").lower():
                return True
    return False


def can_fetch(url: str) -> bool:
    """
    Respect robots.txt for the domain.
    Returns True if the bot is allowed to fetch this URL.
    Defaults to True if robots.txt can't be loaded (fail-open).

    Always uses the www. variant of the robots.txt URL so that
    pm.gc.ca and www.pm.gc.ca share the same (permissive) rules.
    """
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()

    # Normalise to www. for robots.txt lookup
    # e.g. pm.gc.ca  → www.pm.gc.ca
    #      www.pm.gc.ca → www.pm.gc.ca  (unchanged)
    if netloc and not netloc.startswith("www."):
        robots_netloc = "www." + netloc
    else:
        robots_netloc = netloc

    domain_key = f"{parsed.scheme}://{robots_netloc}"

    if domain_key not in _robots_cache:
        rp = urllib.robotparser.RobotFileParser()
        try:
            rp.set_url(f"{domain_key}/robots.txt")
            rp.read()
        except Exception:
            pass   # if we can't read robots.txt, assume allowed
        _robots_cache[domain_key] = rp

    return _robots_cache[domain_key].can_fetch(HEADERS["User-Agent"], url)


def make_absolute(href: str, base_url: str) -> str:
    """Convert a relative href to an absolute URL using base_url."""
    return urljoin(base_url, href)
