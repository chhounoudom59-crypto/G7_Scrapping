# =============================================================
# scraper/european_union.py — European Union (europa.eu)
# =============================================================
# PRIMARY:   RSS feed → https://europa.eu/newsroom/rss.xml
# SECONDARY: europa.eu/newsroom
#
# The EU newsroom RSS feed includes press releases, speeches,
# and statements. Additional links can be followed from the
# main newsroom page.
# =============================================================

from scraper.base_scraper import CountryScraper

class EuropeanUnionScraper(CountryScraper):
    """
    Scraper for europa.eu.
    No overrides needed — sites.json drives the full config.
    """
    pass