# =============================================================
# scraper/uk.py — United Kingdom (gov.uk)
# =============================================================
# PRIMARY:   Atom feed → https://www.gov.uk/search/news-and-communications.atom
# SECONDARY: Listing page with ?page={n} pagination
#
# GOV.UK uses the GDS design system — very clean, consistent HTML.
# The Atom feed is excellent: structured, reliable, always current.
# =============================================================

from scraper.base_scraper import CountryScraper

class UKScraper(CountryScraper):
    """
    Scraper for gov.uk.
    No overrides needed — sites.json drives the full config.
    """
    pass
