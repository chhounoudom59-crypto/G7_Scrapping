# =============================================================
# scraper/usa.py — United States (whitehouse.gov)
# =============================================================
# PRIMARY:   RSS feed → https://www.whitehouse.gov/feed/
# SECONDARY: Listing pages (statements, speeches, briefings)
#
# The RSS feed is the most reliable source — it contains the
# latest 10-20 items from the Briefing Room with titles and
# dates already structured.  The listing pages provide deeper
# pagination for historical scraping.
#
# All heavy lifting (fetching, dedup, storage) is handled by
# CountryScraper in base_scraper.py.
# This file only holds USA-specific config overrides if needed.
# =============================================================

from scraper.base_scraper import CountryScraper

class USAScraper(CountryScraper):
    """
    Scraper for whitehouse.gov.
    No overrides needed — sites.json drives the full config.
    """
    pass
