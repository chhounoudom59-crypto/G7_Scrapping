# =============================================================
# scraper/france.py — France (gouvernement.fr)
# =============================================================
# PRIMARY:   RSS feed → https://www.gouvernement.fr/actualites/atom
# SECONDARY: Listing pages (js_required=True → Playwright)
#
# gouvernement.fr is a React/Vue application that requires
# JavaScript rendering for listing pages.  However, the Atom
# feed is static and fetched with plain httpx — so for most
# use cases Playwright is not needed at all.
#
# If the RSS feed is unavailable, Playwright kicks in for the
# listing page and the wait_selector="article" ensures the
# content is fully rendered before parsing.
# =============================================================

from scraper.base_scraper import CountryScraper

class FranceScraper(CountryScraper):
    """
    Scraper for gouvernement.fr.
    No overrides needed — sites.json drives the full config.
    """
    pass
