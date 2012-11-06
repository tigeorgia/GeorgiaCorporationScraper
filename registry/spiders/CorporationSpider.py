# -*- coding: utf-8 -*-

import re
import math

from scrapy.spider import BaseSpider
from scrapy.http import Request, FormRequest
from scrapy.selector import HtmlXPathSelector
from scrapy import log
from bs4 import BeautifulSoup

class CorporationSpider(BaseSpider):
    name = "corps"
    #allowed_domains = ["enreg.reestri.gov.ge"]
    base_url = "https://enreg.reestri.gov.ge/main.php"
    start_urls = [base_url]

    # Override so that we can set our cookie easily.
    def start_requests(self):
        return [Request(self.base_url, callback=self.get_cookies)]

    # This is only here so that the first request is to the home
    # page, which will set cookies and allow subsequent Requests
    # to work.
    def get_cookies(self, response):
        my_url = self.base_url+"?c=app&m=search_form"
        return [Request(my_url, callback=self.parse_corpclasses)]

    # Grabs the different corporation classes from the search
    # form dropdown menu.
    def parse_corpclasses(self, response):
        form_data ={'c': 'search',
                    'm': 'find_legal_persons',
                    's_legal_person_idnumber':'',
                    's_legal_person_name':''}
        
        soup = BeautifulSoup(response.body, "html5lib")
        form = soup.find(id="s_search_persons_form")
        for opt in form.find_all("option"):
            form_data['s_legal_person_form'] = opt['value']
            #log.msg("Found corp class: {}".format(opt['value']))
            yield FormRequest(self.base_url, 
                              formdata=form_data,
                              callback=self.parse_corpresults)
    
    # Finds out how many pages of results there are and launches
    # requests for them.
    def parse_corpresults(self, response):
        # The total number of records is listed at the bottom of the table
        # Divide by 5 records per page to get the total number of pages
        # we need to scrape.
        RESULTS_PER_PAGE = 5
        form_data ={'c': 'search',
                    'm': 'find_legal_persons',}

        soup = BeautifulSoup(response.body, "html5lib", from_encoding="utf-8")
        cells = soup.find_all("td")
        td = None

        # The number of results is in a <td> that contains the text
        # სულ.
        # After that, there is a <strong> tag that has the actual number
        # in it, and then some other stuff. So we search through all
        # the td tags until we find the one with matching text,
        # and then grab the number in its <strong> tag.
        regx = re.compile(u"^\s+სულ\s+$")
        for cell in cells:
            if (regx.match(cell.contents[0])):
                td = cell #Found the right cell!
                break;

        total_results = float(td.find("strong").string)
        total_pages = int(math.ceil(total_results/RESULTS_PER_PAGE))
        #log.msg("Total pages: {}".format(str(total_pages)))
        for pg in range(1,total_pages):
            form_data["p"]=str(pg)
            yield FormRequest(self.base_url,
                              formdata=form_data,
                              callback=self.parse_corptable)
    
    # Parses the table on the search results page in order to
    # get links to individual corporation detail pages.
    def parse_corptable(self, response):
        # The database IDs of each corporation are located
        # in onclick() events on <a> tags surrounding info
        # button images. So we get the info images, and then
        # extract the db id from their parents.

        form_data ={'c': 'app',
                    'm': 'show_legal_person',}
        soup = BeautifulSoup(response.body, "html5lib", from_encoding="utf-8")
        buttons = soup.find_all("img",src="https://enreg.reestri.gov.ge/images/info.png")
        for b in buttons:
            dbid = b.parent['onclick'].split("(")[-1].rstrip(")")
            #log.msg("Found dbid: {}".format(dbid))
            form_data['legal_code_id'] = dbid
            yield FormRequest(self.base_url,
                              formdata=form_data,
                              callback=self.parse_corpdetails)
    
    def parse_corpdetails(self, response):
        log.msg("parse_corpdetails")

    def parse(self, response):
        pass
