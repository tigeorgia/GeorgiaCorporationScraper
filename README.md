This is a scraper for [the corporate registry of the country of Georgia](https://enreg.reestri.gov.ge). It is implemented in Python, using the excellent [Scrapy](http://scrapy.org "Scrapy homepage") framework.

This will eventually replace [our old scraper](https://github.com/tigeorgia/geo-companies-scrape), but it's not quite finished yet.

Installation
=============
Should be pretty simple:

1. `virtualenv geo_corp_scrape`
2. `cd geo_corp_scrape`
3. `source bin/activate` and clone the repo
4. cd into the repo folder and `pip install -r requirements.txt`
5. Install [poppler](http://poppler.freedesktop.org/)

Usage
===========
`scrapy crawl corps` -- That's it.
You should get a series of JSON files representing the scraped data.
