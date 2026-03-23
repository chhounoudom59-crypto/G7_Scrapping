# =============================================================
# scraper/canada.py — Canada (canada.ca + pm.gc.ca)
# =============================================================
# PRIMARY:   RSS feed → https://pm.gc.ca/en/news/rss.xml
# SECONDARY: canada.ca/en/news.html + pm.gc.ca/en/news
#
# Canada's PM office RSS is reliable and includes press releases,
# speeches, and statements.  The extra_domains config lets us
# follow links to pm.gc.ca and news.gc.ca from canada.ca pages.
# =============================================================

from scraper.base_scraper import CountryScraper

class CanadaScraper(CountryScraper):
    """
    Scraper for canada.ca / pm.gc.ca.
    No overrides needed — sites.json drives the full config.
    """
    pass
