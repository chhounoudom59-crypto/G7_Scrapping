# =============================================================
# scraper/germany.py — Germany (bundesregierung.de)
# =============================================================
# PRIMARY:   RSS feed → https://www.bundesregierung.de/breg-de/aktuelles/rss
# SECONDARY: English news listing (js_required=True → Playwright)
#
# The German Federal Government RSS is in German but the article
# URLs can be followed to the English version by appending /en/.
# The English listing page at /breg-en/news is JS-rendered.
#
# Playwright is configured as the fallback for listing pages.
# The RSS feed is parsed with plain httpx (no JS needed).
# =============================================================

from scraper.base_scraper import CountryScraper

class GermanyScraper(CountryScraper):
    """
    Scraper for bundesregierung.de.
    No overrides needed — sites.json drives the full config.
    """
    pass
