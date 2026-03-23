# =============================================================
# scraper/italy.py — Italy (governo.it)
# =============================================================
# PRIMARY:   RSS feed → https://www.governo.it/it/articoli/feed
# SECONDARY: English news listing → https://www.governo.it/en/news
#
# Italy's government site is a Drupal CMS — relatively clean HTML.
# The RSS feed covers Italian-language content.  The English
# listing page gives EN articles.  extra_domains includes
# g7italy.it which was used for G7 Italy presidency content.
# =============================================================

from scraper.base_scraper import CountryScraper

class ItalyScraper(CountryScraper):
    """
    Scraper for governo.it.
    No overrides needed — sites.json drives the full config.
    """
    pass
