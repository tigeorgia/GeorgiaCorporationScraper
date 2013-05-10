# -*- coding: utf-8 -*-

import re
import math
import urlparse

from scrapy.spider import BaseSpider
from scrapy.http import Request, FormRequest
from scrapy.selector import HtmlXPathSelector
from scrapy import log
from bs4 import BeautifulSoup

from registry.items import Corporation, Person, CorporationDocument, StatementDocument, RegistryStatement, PersonCorpRelation, RegistryExtract
from registry import pdfparse

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
        soup = BeautifulSoup(response.body, "html5lib", from_encoding="utf-8")
        form = soup.find(id="s_search_persons_form")
        if self.page_by_page == True:
            for opt in form.find_all("option"):
                # 0 is nothing. Skip individuals for dev.
                if(opt['value'] == '0' or opt['value'] == '1'):
                    continue
                #log.msg("Found corp class: {}".format(opt['value']))
            
                request = Request(self.base_url, 
                              #formdata=form_data,
                              callback=self.setup_cookies,
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
    def setup_cookies(self, response):
        form_data ={'c': 'search',
                    'm': 'find_legal_persons',
                    's_legal_person_idnumber':'',
                    's_legal_person_name':''}
        
        form_data['s_legal_person_form'] = response.meta['cookiejar']

        request = FormRequest(self.base_url,
                            formdata=form_data,
                            callback=self.parse_corpresults,
                            meta={'cookiejar': response.meta['cookiejar']})
        if 'renew' in response.meta:
            request.meta['renew'] = response.meta['renew']
            request.meta['page'] = response.meta['page']
        yield request
    
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
        # The site does some dumb things with session variables, sometimes
        # they need to get renewed.
        if 'renew' in response.meta:
            form_data['p'] = response.meta['page']
            request = FormRequest(self.base_url,
                              formdata=form_data,
                              callback=self.parse_corptable,
                              meta={'cookiejar': response.meta['cookiejar'],
                                    'page': response.meta['page'],
                                    'type': response.meta['cookiejar'],
                                    })
            yield request
        # Otherwise, this is our first time viewing this result type, and
        # we start from the beginning.
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
                                    'type': response.meta['cookiejar'],
                                    })
            yield request
    
    # Parses the table on the search results page in order to
    # get links to individual corporation detail pages.
    def parse_corptable(self, response):
        # The database IDs of each corporation are located
        # in onclick() events on <a> tags surrounding info
        # button images. So we get the info images, and then
        # extract the db id from their parents.
        #log.msg("Parsing corp results table")
        log.msg("Parsing page {} of type {}".format(response.meta['page'],response.meta['type']))
        soup = BeautifulSoup(response.body, "html5lib", from_encoding="utf-8")
        buttons = soup.find_all("img",src="https://enreg.reestri.gov.ge/images/info.png")
        results = []
        for b in buttons:
            dbid = b.parent['onclick'].split(u"(")[-1].rstrip(u")")
            #log.msg("Found dbid: {}".format(dbid))
            corp_url = self.base_url+u"?c=app&m=show_legal_person&legal_code_id={}".format(dbid)
            request = Request(url=corp_url,callback=self.parse_corpdetails)
            request.meta['id_code_reestri_db'] = dbid
            request.meta['cookiejar'] = response.meta['cookiejar']
            results.append(request)
        
        if(len(results) == 0):
            log.msg("Zero results found on page {} of type {}, renewing cookies".format(response.meta['page'],response.meta['type']))
            request = Request(self.base_url, 
                          callback=self.setup_cookies,
                          dont_filter=True,
                          meta={'cookiejar': response.meta['cookiejar'],
                                'renew': True,
                                'page': response.meta['page'],
                                })
            return [request]
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
        stmnt_caption = soup.find("caption", text=u"განცხადებები")
        scand_caption = soup.find("caption", text=u"სკანირებული დოკუმენტები")

        # Return requests for statement pages
        if stmnt_caption is not None:
            corp['no_docs'] = False
            stmnt_table = stmnt_caption.parent
            for row in stmnt_table.tbody.find_all("tr"):
                link = row.find_all("img", src="https://enreg.reestri.gov.ge/images/blob.png")[0].parent
                stmnt_dbid = link['onclick'].split(u"(")[-1].rstrip(u")")
                my_url = self.base_url+u"?c=app&m=show_app&app_id={}".format(stmnt_dbid)
                results.append(Request(url=my_url, 
                                 callback=self.parse_statement,
                                 meta={'cookiejar':response.meta['cookiejar'],
                                       'corp_id_code':corp['id_code_legal'],
                                       'stmnt_id_reestri_db':stmnt_dbid}))

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
                fname = link_node.parent.find_next_sibling("td").find("a").string

                # Create a CorporationDocument
                doc = CorporationDocument(fk_corp_id_code=corp['id_code_legal'],filename=fname,link=doc_url)
                results.append(doc)

                # Create a request if we might be able to parse it (pdf only)
                if fname[-3:] == "pdf":
                    results.append(Request(url=doc_url,
                                    callback=self.parse_corp_pdf,
                                    meta={'cookiejar':response.meta['cookiejar']}))
        
        results.append(corp)

        return results

    # Parse a corporation statement page.
    # This has lots of details about the corporation and links to
    # other stuff.
    def parse_statement(self, response):
        from scrapy.shell import inspect_response

        results = []
        app_id_code_reestri_db = urlparse.parse_qs(urlparse.urlparse(response.request.url)[4])['app_id'][0]

        soup = BeautifulSoup(response.body, "html5lib", from_encoding="utf-8")
        
        # First table: "Prepared documents" -- scrape details into CorpDoc item
        # and then grab the doc too; they are usually PDFs.
        prepared_table = soup.find("caption", text=u"მომზადებული დოკუმენტები")
        if prepared_table is not None:
            prepared_table = prepared_table.parent
            for row in prepared_table.find_all("tr"):
                # First cell contains link
                # Second contains title, date
                # Third is blank
                cells = row.find_all("td")
                link = cells[0].a["href"]
                spans = cells[1].find_all("span")
                title = spans[0].string
                date = spans[1].string

                results.append(StatementDocument(
                    fk_corp_id_code=response.meta['corp_id_code'],
                    fk_stmnt_id_code_reestri_db=app_id_code_reestri_db,
                    link=link,
                    title=title,
                    date=date))
                
                results.append(Request(url=link,
                            callback=self.parse_stmnt_prepared_doc,
                            meta={'cookiejar':response.meta['cookiejar'],
                                  'corp_id_code':response.meta['corp_id_code']}))
        
        # Second table: Status Documents. Scrape details into CorpDocs, and
        # grab the docs too, they are usually PDFs.
        status_table = soup.find("caption", text=u"სტატუსი / გადაწყვეტილება")
        if status_table is not None:
            status_table = status_table.parent

            for row in status_table.find_all("tr"):
                cells = row.find_all("td")
                link = cells[0].a["href"]
                registration_num = cells[1].find(class_="maintxt").string
                date = cells[1].find(class_="smalltxt").string
                title = cells[2].find(style=True).string

                results.append(StatementDocument(
                    fk_corp_id_code=response.meta['corp_id_code'],
                    fk_stmnt_id_code_reestri_db=app_id_code_reestri_db,
                    link=link,
                    title=title,
                    date=date,
                    registration_num=registration_num))
        
                # Probably don't actually need to parse these.
                #results.append(Request(url=link,
                #            callback=self.parse_stmnt_status_pdf,
                #            meta={'cookiejar':response.meta['cookiejar'],
                #                  'id_code_reestri_db':response.meta['id_code_reestri_db']}))
        # Third table: Scanned Documents. Scrape details into CorpDocs, and
        # grab the docs if they are PDFs.
        scanned_table = soup.find("caption", text=u"სკანირებული დოკუმენტები")
        if scanned_table is not None:
            scanned_table = scanned_table.parent

            for row in scanned_table.find_all("tr"):
                cells = row.find_all("td")
                link = cells[0].a["href"]
                doc_info = cells[1].find_all(class_="maintxt")
                if (len(doc_info) == 2):
                    title = doc_info[0].string
                    date = doc_info[1].string
                else:
                    date = doc_info[0].string
                    title = None
                filename = cells[2].find("a").find("span").string

                doc = StatementDocument(
                    fk_corp_id_code=response.meta['corp_id_code'],
                    fk_stmnt_id_code_reestri_db=app_id_code_reestri_db,
                    link=link,
                    date=date,
                    filename=filename)
                if (title):
                    doc['title'] = title
                
                results.append(doc)
        
                #TODO: Check whether it's a PDF and if so, return
                # a Request to the document.

        # Fourth table: Statement details. Scrape details into RegistryStatement.
        statement = RegistryStatement()
        # First block of info, starting with statement number.
        regx = re.compile(u"^\s+განცხადება.+$")
        caption = soup.find("caption",text=regx)
        if caption is None:
            inspect_response(response)
        statement['statement_num'] = caption.string.split('#')[1]
        table = caption.parent

        statement['registration_num'] = self._get_header_sib(table,u"\n\s*რეგისტრაციის ნომერი\s*").span.string
        statement['statement_type'] = self._get_header_sib(table,u"\n\s*მომსახურების სახე\s*").span.string
        statement['service_cost'] = self._get_header_sib(table,u"\n\s*მომსახურების ღირებულება\s*").span.string
        pay_debt = self._get_header_sib(table,u"\n\s*გადასახდელი თანხა/ბალანსი\s*").span.string
        statement['payment'] = pay_debt.split("/")[0]
        statement['outstanding'] = pay_debt.split("/")[1]
        statement['id_reestri_db'] = response.meta['stmnt_id_reestri_db']

        # Second block of info, starting after payment details.
        # Find the correct table
        table = soup.find("div", id="application_tab").table
        # Grab the relevant parts
        statement['id_code_legal'] = self._get_header_sib(table,u"საიდენტიფიკაციო ნომერი").strong.string
        statement['name'] = self._get_header_sib(table,u"სუბიექტის დასახელება ").string
        statement['classification'] = self._get_header_sib(table,u"სამართლებრივი ფორმა").string
        statement['reorganization_type'] = self._get_header_sib(table,u"რეორგანიზაციის ტიპი ").string
        statement['quantity'] = self._get_header_sib(table,u"რაოდენობა").string
        statement['changed_info'] = self._get_header_sib(table,u"შესაცვლელი რეკვიზიტი: ").string
        
        # Attached docs description is a <ul>
        attached = self._get_header_sib(table, u"\n\s*თანდართული დოკუმენტაცია\s")
        attached_desc = []
        for li in attached.ul.contents:
            attached_desc.append(li.string)
        statement['attached_docs_desc'] = attached_desc

        # Additional docs is a <div>, don't know what the format looks like yet
        addtl_td = self._get_header_sib(table,u"\n\s*დამატებით წარმოდგენილი\s*")
        statement['additional_docs'] = addtl_td.find(id="additional_docs_container").string
        
        # Issued docs also a ul
        issued = self._get_header_sib(table, u"\n\s*გასაცემი დოკუმენტები\s*").ul
        issued_desc = []
        for li in issued.contents:
            issued_desc.append(li.string)
        statement['issued_docs'] = issued_desc
        
        # Don't know the format of notes yet either.
        notes_td = self._get_header_sib(table, u"\n\s*შენიშვნა\s*")
        statement['notes'] = notes_td.string
        results.append(statement)

        # Cells containing people require a bit more intelligence
        representative_td = self._get_header_sib(table,u" წარმომადგენელი  ")
        rv_pers = self._person_from_statement_cell(representative_td)
        if len(rv_pers) > 0:
            results.append(PersonCorpRelation(person=rv_pers,
                        fk_corp_id_code = response.meta['corp_id_code'],
                        relation_type = [u"წარმომადგენელი"],
                        cite_type = "statement",
                        cite_link = response.request.url))

        representee_td = self._get_header_sib(table,u" წარმომდგენი  ")
        re_pers = self._person_from_statement_cell(representee_td)
        if len(re_pers) > 0:
            results.append(PersonCorpRelation(person=re_pers,
                        fk_corp_id_code = response.meta['corp_id_code'],
                        relation_type = [u"წარმომდგენი"],
                        cite_type = "statement",
                        cite_link = response.request.url))

        ganmcxadebeli_td = self._get_header_sib(table,u"განმცხადებელი  ")
        g_pers = self._person_from_statement_cell(ganmcxadebeli_td)
        if len(g_pers) > 0:
            results.append(PersonCorpRelation(person=g_pers,
                        fk_corp_id_code = response.meta['corp_id_code'],
                        relation_type = [u"განმცხადებელი"],
                        cite_type = "statement",
                        cite_link = response.request.url))
        return results

    def parse_corp_pdf(self, response):
        pass

    # Each statement may have an output document which is "prepared"
    # for that statement. This function scrapes those documents
    def parse_stmnt_prepared_doc(self, response):
        return self._info_from_pdf(response.body,response.url, response.meta['corp_id_code'])

    def _info_from_pdf(self,text,url,corp_id_code):
        from scrapy.shell import inspect_response
        # These documents are PDFs, so they're going to be coming
        # from the PdfToHtml Middleware, which means they'll
        # be XML rather than HTML.
        log.msg("Parsing PDF {}".format(url), level=log.DEBUG)
        headers = pdfparse.headers 
        results = []
        soup = BeautifulSoup(text, "xml", from_encoding="utf-8")
        boxes = pdfparse.boxes_from_xml(text)
        boxes = pdfparse.remove_duplicates(boxes) # Handily, this sorts too
        # TextBoxes define sort order as top-to-bottom, left-to-right.
       
        # TODO: Check for malformed / Blank / Something else extracts
        extract = RegistryExtract()
        extract['fk_corp_id_code'] = corp_id_code

        # Get extract date.
        date_lines = pdfparse.get_pdf_lines('extract_date',boxes,soup)
        if date_lines is not None:
            extract['date'] = u"".join([tb.text for tb in date_lines])

        # Get mailing address
        address_lines = pdfparse.get_pdf_lines('address',boxes,soup)
        if address_lines is not None:
            log.msg("Found address, printing: ", level=log.DEBUG)
            s = u"".join([tb.text for tb in address_lines])
            # TODO: Metrics to check whether we've mis-parsed.
            extract['corp_address'] = s
            log.msg(unicode(s),level=log.DEBUG)
        else:
            log.msg("No address found.", level=log.DEBUG)

        # Get email address
        email_lines = pdfparse.get_pdf_lines('email',boxes,soup)
        if email_lines is not None:
            log.msg("Found email, printing: ", level=log.DEBUG)
            s = u"".join([tb.text for tb in email_lines])
            log.msg(unicode(s), level=log.DEBUG)
            # TODO: Validate email address to check for mis-parse
            extract['corp_email'] = s
        else:
            log.msg("No email found.", level=log.DEBUG)
        
        results.append(extract)


        # Parse directors
        dir_lines = pdfparse.get_pdf_lines('directors',boxes,soup)
        if(dir_lines is not None):
            log.msg("Found directors block, printing", level=log.DEBUG)
            text = [tb.text for tb in dir_lines]

            board = pdfparse.parse_directors(text)
            for mem in board:
                try:
                    pers = Person(personal_code=mem["id_code"])
                except (KeyError, IndexError):
                    continue
                try:
                    pers["name"] = mem["name"]
                except KeyError:
                    pass
                try:
                    pers["nationality"] = mem["nationality"]
                except KeyError:
                    pass
                relation = PersonCorpRelation(person=pers,
                            fk_corp_id_code=corp_id_code,
                            cite_type=u"extract",
                            cite_link=url)
                try:
                    relation["relation_type"] = [mem["position"]]
                except KeyError:
                    pass

                log.msg("Added relation from Extract: {}".format(relation), level=log.DEBUG)
                results.append(relation)

            #s = u"".join([tb.text for tb in dir_lines])
            #log.msg(unicode(s), level=log.DEBUG)
        else:
            log.msg("No directors found.", level=log.DEBUG)

        # Extract ownership info
        own_lines = pdfparse.get_pdf_lines('owners',boxes,soup)
        if(own_lines is not None):
            log.msg("Found partners block, printing", level=log.DEBUG)
            text = [tb.text for tb in own_lines]
            owners = pdfparse.parse_owners(text)

            for o in owners:
                try:
                    pers = Person(personal_code=o["id_code"])
                except KeyError:
                    continue
                try:
                    pers["name"] = o["name"]
                except KeyError:
                    pass
                try:
                    pers["nationality"] = o["nationality"]
                except KeyError:
                    pass
                relation = PersonCorpRelation(person=pers,
                            fk_corp_id_code=corp_id_code,
                            cite_type=u"extract",
                            cite_link=url)
                relation["relation_type"] = [u"პარტნიორი"]
                try:
                    relation["share"] = o["share"]
                except KeyError:
                    pass

                log.msg("Added relation from Extract: {}".format(relation), level=log.DEBUG)
                results.append(relation)

        else:
            log.msg("No owners found.", level=log.DEBUG)
        
        return results

    # Each statement also has status docs which come along with it
    # This function extracts information from those docs.
    # It appears these docs are duplicative so they probably don't
    # need to be scraped.
    #def parse_stmnt_status_pdf(self, response):
    #    pass

    # There are a lot of tables where the header
    # is in column 0, and the info we want is in column 1.
    # So this just searches for a td matching the header
    # string and then returns its next sibling.
    def _get_header_sib(self, soup, header):
        regx = re.compile(header)
        res = soup.find("td",text=regx)
        if res is not None:
            next_col = res.find_next_sibling("td")
            return next_col

    def _person_from_statement_cell(self, cell):
        pers = Person()
        for s in cell.stripped_strings:
            parts = s.split(u"(პ/ნ:")
            if len(parts) == 2:
                pers['name'] = parts[0]
                pers['personal_code'] = parts[1][:-1]
            else:
                pers['address'] = s
        return pers

    def parse(self, response):
        pass
