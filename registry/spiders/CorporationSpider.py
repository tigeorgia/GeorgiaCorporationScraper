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

    def parse_corpclasses(self, response):
        soup = BeautifulSoup(response.body, "html5lib")
        form = soup.find(id="s_search_persons_form")
        form_data ={'c': 'search',
                    'm': 'find_legal_persons',
                    's_legal_person_idnumber':'',
                    's_legal_person_name':''}
        
        for opt in form.find_all("option"):
            form_data['s_legal_person_form'] = opt['value']
            log.msg("Found corp class: {}".format(opt['value']))
            yield FormRequest(self.base_url, 
                              formdata=form_data,
                              callback=self.parse_corptables)
        #hxs = HtmlXPathSelector(response)
        #hxs.select('//*[@id="s_search_persons_form"]/select')
    
    def parse_corptables(self, response):
        pass

    def parse(self, response):
        pass
