# -*- coding: utf-8 -*-

import re
import math

from scrapy.spider import BaseSpider
from scrapy.http import Request, FormRequest
from scrapy.selector import HtmlXPathSelector
from scrapy import log
from bs4 import BeautifulSoup

from registry.items import Corporation, Person, CorporationDocument

class CorporationSpider(BaseSpider):
    name = "corps"
    page_by_page = True # Scrape page-by-page -- VERY slow (~19+ days)
                        # Guess db ids, MUCH faster for individual IDs,
                        # But the IDs aren't contiguous enough for this
                        # to be useful; there are ~500K corporations
                        # but ~10M IDs. Currently overruns memory.
    #allowed_domains = ["enreg.reestri.gov.ge"]
    base_url = "https://enreg.reestri.gov.ge/main.php"
    start_urls = [base_url]
    #MAX_CONSEC_MISSES = 100

    # Override so that we can set our cookie easily.
    def start_requests(self):
        #log.msg("in start_requests")
        my_url = self.base_url+"?c=app&m=search_form"
        yield Request(my_url, callback=self.parse_corpclasses)

    # Grabs the different corporation classes from the search
    # form dropdown menu.
    def parse_corpclasses(self, response):
        #log.msg("in parse_corpclasses")
        soup = BeautifulSoup(response.body, "html5lib")
        form = soup.find(id="s_search_persons_form")
        if self.page_by_page == True:
            for opt in form.find_all("option"):
                # 0 is nothing. Skip individuals for dev.
                if(opt['value'] == '0' or opt['value'] == '1'):
                    continue
                #log.msg("Found corp class: {}".format(opt['value']))
            
                request = Request(self.base_url, 
                              #formdata=form_data,
                              callback=self.search_with_cookies,
                              dont_filter=True,
                              meta={'cookiejar': opt['value'],
                                    'corp_class': opt['value']})
                yield request
        else: # Guess ID numbers instead
            form_data ={'c': 'search',
                    'm': 'find_legal_persons',
                    's_legal_person_idnumber':'',
                    's_legal_person_name':'',
                    's_legal_person_form': '1'}
        
            yield FormRequest(self.base_url,
                            formdata=form_data,
                            callback=self.guess_biggest_id)

    # This works but overflows memory because there are about
    # 10M id numbers but only about 500k real corporations.
    # Used when page_by_page set to True, so don't do that right now.
    def guess_biggest_id(self, response):
        """ We assume that corporation listings are listed
        approximately in the order that they were created.
        Therefore the most recently updated corporation is
        the one first on the list. This is usually going to
        be on the individual entrepreneurs page, it has the
        most activity. So scrape that, get the first id, and
        then count up to that; that'll give us a rough idea
        of how many there are."""
        soup = BeautifulSoup(response.body, "html5lib", from_encoding="utf-8")
        buttons = soup.find_all("img",src="https://enreg.reestri.gov.ge/images/info.png")
        results = []
        
        for b in buttons:
            dbid = b.parent['onclick'].split("(")[-1].rstrip(")")
            results.append(int(dbid))
        
        biggest = sorted(results)[-1]+1
        log.msg("Guessing biggest is {}".format(biggest)) 
        for dbid in range(0,biggest):
            corp_url = self.base_url+"?c=app&m=show_legal_person&legal_code_id={}".format(dbid)
            request = Request(url=corp_url,callback=self.parse_corpdetails)
            request.meta['id_code_reestri_db'] = dbid
            request.meta['cookiejar'] = '1' # Don't need a separate jar
            yield request

    # This site does some incredibly stupid things with cookies
    # so we need to use a separate cookie jar for each type of
    # corporation that we will scrape.
    def search_with_cookies(self, response):
        form_data ={'c': 'search',
                    'm': 'find_legal_persons',
                    's_legal_person_idnumber':'',
                    's_legal_person_name':''}
        
        form_data['s_legal_person_form'] = response.meta['corp_class'];

        return [FormRequest(self.base_url,
                            formdata=form_data,
                            callback=self.parse_corpresults,
                            meta={'cookiejar': response.meta['cookiejar']})]
    
    # Finds out how many pages of results there are and launches
    # requests for them.
    def parse_corpresults(self, response):
        # The total number of records is listed at the bottom of the table
        # Divide by 5 records per page to get the total number of pages
        # we need to scrape.
        RESULTS_PER_PAGE = 5
        form_data ={'c': 'search',
                    'm': 'find_legal_persons',
                   }

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
        # Scrapy generally tends to scrape last page first,
        # so reverse the order we return the results so that
        # earlier pages are scraped earlier and easier to manually
        # debug in a browser.
        for pg in reversed(range(1,total_pages+1)):
            form_data["p"]=str(pg)
            request = FormRequest(self.base_url,
                              formdata=form_data,
                              callback=self.parse_corptable,
                              meta={'cookiejar': response.meta['cookiejar'],
                                    'page': str(pg),
                                    'type': response.meta['cookiejar']})
            yield request
    
    # Parses the table on the search results page in order to
    # get links to individual corporation detail pages.
    def parse_corptable(self, response):
        # The database IDs of each corporation are located
        # in onclick() events on <a> tags surrounding info
        # button images. So we get the info images, and then
        # extract the db id from their parents.
        #log.msg("Parsing corp results table")
        soup = BeautifulSoup(response.body, "html5lib", from_encoding="utf-8")
        buttons = soup.find_all("img",src="https://enreg.reestri.gov.ge/images/info.png")
        results = []
        for b in buttons:
            dbid = b.parent['onclick'].split("(")[-1].rstrip(")")
            #log.msg("Found dbid: {}".format(dbid))
            corp_url = self.base_url+"?c=app&m=show_legal_person&legal_code_id={}".format(dbid)
            request = Request(url=corp_url,callback=self.parse_corpdetails)
            request.meta['id_code_reestri_db'] = dbid
            request.meta['cookiejar'] = response.meta['cookiejar']
            results.append(request)
        
        if(len(results) == 0):
            log.msg("Zero results found on page {} of type {}, retrying".format(response.meta['page'],response.meta['type']))
            return [response.request.replace(dont_filter=True)]
        #log.msg("Found {} results on page {} of type {}".format(len(results),response.meta['page'],response.meta['type']))
        return results
    
    # Here we finally get to actually scrape something
    def parse_corpdetails(self, response):
        def get_table_row(soup, header):
            res = soup.find("td",text=header)
            if res is not None:
                text = res.find_next_sibling("td").string
                if text is not None:
                    text = text.strip()
                    return text
        
        #log.msg("Parsing corp details page")
        soup = BeautifulSoup(response.body, "html5lib", from_encoding="utf-8")
        results = [] # Results to be returned by this callback

        # Create 1 corporation
        corp = Corporation()
        corp['id_code_legal'] = get_table_row(soup,u"საიდენტიფიკაციო კოდი")
        corp['personal_code'] = get_table_row(soup,u"პირადი ნომერი")
        corp['state_reg_code'] = get_table_row(soup,u"სახელმწიფო რეგისტრაციის ნომერი")
        corp['name'] = get_table_row(soup,u"დასახელება")
        corp['classification'] = get_table_row(soup,u"სამართლებრივი ფორმა")
        corp['registration_date'] = get_table_row(soup,u"სახელმწიფო რეგისტრაციის თარიღი")
        corp['id_code_reestri_db'] = response.meta['id_code_reestri_db']
       
        # The status cell has some cruft in it, so the easy method doesn't work
        corp['status'] = soup.find("td", text=u"სტატუსი").find_next_sibling("td").div.string
        if (corp['status'] is not None):
            corp['status'] = corp['status'].strip()
        
        corp['no_docs'] = True
        #results.append(corp)
        
        # Return 1 person if necessary (personal corp)
        if ((corp['classification'] == u"ინდივიდუალური მეწარმე") and (corp['personal_code'] is not None)):
            pers = Person()
            pers['name'] = corp['name']
            pers['personal_code'] = corp['personal_code']

            results.append(pers)
        
        # Return Requests / Items for statements and scanned documents.
        stmnt_caption = soup.find("caption", text="განცხადებები")
        scand_caption = soup.find("caption", text="სკანირებული დოკუმენტები")

        # Return requests for statement pages
        if stmnt_caption is not None:
            corp['no_docs'] = False
            stmnt_table = stmnt_caption.parent
            for row in stmnt_table.tbody.find_all("tr"):
                link = row.find_all("img", src="https://enreg.reestri.gov.ge/images/blob.png")[0].parent
                stmnt_dbid = link['onclick'].split("(")[-1].rstrip(")")
                my_url = self.base_url+"?c=app&m=show_app&app_id={}".format(stmnt_dbid)
                results.append(Request(url=my_url, 
                                 callback=self.parse_statement,
                                 meta={'cookiejar':response.meta['cookiejar']}))

        if scand_caption is not None:
            corp['no_docs'] = False
            scand_table = scand_caption.parent
            for row in scand_table.tbody.find_all("tr"):
                link_node = row.find_all("img", src="https://enreg.reestri.gov.ge/images/blob.png")[0].parent
                doc_url = link_node['href']
                # Get the file name
                # It's the text of the second column.
                # But there's an empty <strong> tag there so we
                # can't use BeautifulSoup's convenience .string attribute
                #log.msg("Link node next element {}".format(link_node.parent.next_element))
                fname = link_node.parent.find_next_sibling("td").contents[0]

                # Create a CorporationDocument
                doc = CorporationDocument(fk_corp_id_code_reestri_db=corp['id_code_reestri_db'],filename=fname,link=doc_url)
                results.append(doc)

                # Create a request if we might be able to parse it (pdf only)
                if fname[-3:] == "pdf":
                    results.append(Request(url=doc_url,
                                    callback=self.parse_scannedpdf,
                                    meta={'cookiejar':response.meta['cookiejar']}))
        
        results.append(corp)

        return results

    def parse_statement(self, response):
        pass

    def parse_scannedpdf(self, response):
        pass

    def parse(self, response):
        pass
