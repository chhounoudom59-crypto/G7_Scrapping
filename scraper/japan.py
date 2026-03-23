# =============================================================
# scraper/japan.py — Japan (japan.kantei.go.jp)
# =============================================================
# DISCOVERY: Monthly archive URLs (no RSS available)
#
# The Japanese Prime Minister's Office website (kantei.go.jp)
# does not offer an RSS feed.  Instead, it publishes a monthly
# archive index page at:
#   https://japan.kantei.go.jp/news/YYYYMM/index.html
#
# The base_scraper automatically generates these URLs going back
# JAPAN_MONTHS_BACK months (default 24) when site name is
# "Government of Japan".  Each monthly page is fetched and
# article links are extracted from the HTML table.
#
# The selectors in sites.json target the <td> cells that contain
# links to individual article pages.
# =============================================================

from scraper.base_scraper import CountryScraper

class JapanScraper(CountryScraper):
    """
    Scraper for japan.kantei.go.jp using monthly archive pages.
    No overrides needed — base_scraper detects this site by name
    and generates the monthly URLs automatically.
    """
    pass
