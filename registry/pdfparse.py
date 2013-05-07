# -*- coding: utf-8 -*-
import os, codecs
import checkers
from bs4 import BeautifulSoup

# Headers for extracting different types of data from PDF
headers = {
    "extract_date": u"ამონაწერის მომზადების თარიღი:",
    "subject": u"სუბიექტი",
    "name": u"საფირმო სახელწოდება:",
    "address": u"იურიდიული მისამართი:",
    "email": u"ელექტრონული ფოსტა:",
    "legal_id_code": u"საიდენტიფიკაციო კოდი:",
    "legal_form": u"სამართლებრივი ფორმა:",
    "reg_date": u"სახელმწიფო რეგისტრაციის თარიღი:",
    "reg_agency": u"მარეგისტრირებელი ორგანო:",
    "tax_agency": u"საგადასახადო ინსპექცია:",
    "directors": u"ხელმძღვანელობაზე/წარმომადგენლობაზე უფლებამოსილი პირები",
    "owners": u"პარტნიორები",
    "lien": u"ყადაღა/აკრძალვა:",
    "leasing": u"გირავნობა",
    "reorganization": u"რეორგანიზაცია",
    "founders": u"დამფუძნებლები",
}
# Find all the text boxes after the start box
# until a box that is in headers is found.
def find_to_next_header(start, headers, search):
    results = []
    si = 0
    for tb in search: #search.index(start) fails with UnicodeError. No idea why
        try:
            if tb == start:
                si += 1
                break
        except UnicodeError:
            print(u"Header: {}".format(start))
            print(u"Current: {}".format(tb))
            return results
        si += 1
    while si < len(search) and search[si].text not in headers.values():
        #print(u"checking {}".format(search[si+1].text))
        results.append(search[si])
        si += 1
    return results

def get_pdf_lines(start_header,boxes,soup):
    header_tag = soup.find("text",text=headers[start_header])
    if header_tag is not None:
        lines = find_to_next_header(TextBox(header_tag),headers,boxes)
        return lines
    else:
        return None


# Find all the text boxes between the two given boxes.
# The definition of "between" is: on the same line,
# after the first box, through on the same line, before the
# second box.
# Relies on a list sorted top to bottom, left to right.
def find_between(start, end,search):
    results = []
    # Find search indices:
    si = search.index(start)
    ei = search.index(end)
    # This slightly funky search is due to the fact that 
    # the == operator works on all fields, while the
    # other operators operate on only .top.
    while search[si] <= search[si-1]:
        si -= 1
    while search[ei] >= search[ei+1]:
        ei += 1

    # Search through all text boxes that might fit our criteria
    for i in range(si, ei+1):
        if search[i].top != start.top and search[i].top != end.top:
            results.append(search[i])
        elif search[i].top == start.top:
            if search[i].left > start.left:
                results.append(search[i])
        elif search[i].top == end.top:
            if search[i].left < end.left:
                results.append(search[i])

    return results

def boxes_from_xml(text):
    soup = BeautifulSoup(text, "xml", from_encoding="utf-8")
    boxes = []
    for t in soup.find_all("text"):
        t['top'] = unicode(int(t['top'])+1200*(int(t.parent['number'])-1))
        boxes.append(TextBox(t))

    return boxes

# Removes duplicates from a list.
# Sorts too.
# items that are almost equal but don't hash equal.
def remove_duplicates(tb_list):
    results = sorted(tb_list) 
    for i in range(0,len(results)):
        if (i < len(results)-1 and 
            results[i] == results[i+1]): # Stop early, avoid out of bounds
                                        # == is defined fuzzily
                results[i+1] = results[i]
    results = set(results) # But hash isn't fuzzy, so we need to do this to
                            # get rid of duplicates.
    return sorted(results)

# Converts the given PDF file to XML, returns the text.
def pdfToHtml(filename):
    # pdftohtml from the poppler suite, executed with the
    # following options:
    # -q: Don't print messages or errors
    # -xml: Output xml, not HTML
    # -s: Generate a single document with all PDF pages
    # -i: ignore images
    # -enc: Encoding
    os.system('pdftohtml -q -xml -s -i -enc UTF-8 {} {}'.format(filename,filename+'.xml'))
    # Read output
    with codecs.open(filename+'.xml', 'rb',encoding="utf-8") as fin:
        text = fin.read()
    
    # Clean up after ourselves
    #os.remove(tmp+'/'+fname+'.xml')

    # Construct new response
    return text

# I'm not sure these next two are very useful anymore as currently written.
def parse_address(array):
    confidence = 0.0
    joined = u''.join(array)
    # Some random metrics, currently not used.
    if len(joined) > 40 and len(joined) < 90:
        confidence += 0.25
    if u"საქართველო" in joined:
        confidence += 0.30
    return [[(u"address", joined, confidence)]]

def parse_email(array):
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
    result = []
    for s in array:
        try:
            validate_email(s)
            result.append([(u"email", s, 1.0)])
        except ValidationError:
            pass
    return result

def parse_directors(array):
    # First, flatten the array so we don't have to do a double for-loop
    strings = [s.strip() for sr in array for s in sr.split(",")]
    # The first item in every record is going to be an ID number
    # (probably). So if we can make a reasonably good guess about
    # whether a string is an ID number, then we can figure out where
    # the new records start (with the unfortunate exception that some
    # records have multiple leading IDs).
    results = []
    record = {"id_code": [],}
    for s in strings:
        if len(s) == 0:
            continue
        if checkers.check_id(s) >= 0.5: # Found an ID, might indicate new record.
            # Two possibilities: blank / non-blank record
            if len(record) == 1:
                record["id_code"].append(s)
            else: # Non-blank record, create a new record
                for key in record:
                    record[key] = ' '.join(record[key])
                results.append(record)
                record = {"id_code":[s],}
                
        else: # Not an ID, must be something else.
            # Figure out which of our checkers is most confident
            # and assume that the string is of that type.
            info_types = [(checkers.check_name,"name"),
                          (checkers.check_nationality,"nationality"),
                          (checkers.check_position,"position")]
            greatest = (0,"unknown")
            for typ in info_types:
                conf = typ[0](s)
                if conf is not None and conf > greatest[0]:
                    greatest = (conf, typ[1])
           
            try:
                record[greatest[1]].append(s)
            except KeyError:
                record[greatest[1]] = [s]

    # Convert arrays into strings
    for key in record:
        record[key] = ' '.join(record[key])
    results.append(record)
    return results

from bs4 import Tag
class TextBox:
    def __init__(self, tag):
        if(isinstance(tag,Tag)):
            self.top = int(tag['top'])
            self.left = int(tag['left'])
            self.width = int(tag['width'])
            self.height = int(tag['height'])
            self.text = tag.string
        else:
            raise TypeError(u"Tried to construct TextBox with {}".format(tag.__class__))

    def ctr_v(self):
        return self.height / 2

    def ctr_h(self):
        return self.width / 2

    def __lt__(self, other):
        if self.top < other.top:
            return True
        elif self.top == other.top:
            return self.left < other.left

    def __gt__(self, other):
        if self.top > other.top:
            return True
        elif self.top == other.top:
            return self.left > other.left

    def __le__(self, other):
        if self.top <= other.top:
            return True
        else:
            return False

    def __ge__(self, other):
        if self.top >= other.top:
            return True
        else:
            return False

    def __eq__(self, other):
        if (isinstance(other, TextBox) and 
                abs(self.top - other.top) < 2 and
                abs(self.left - other.left) < 2 and
                self.width == other.width and
                self.height == other.height and
                self.text == other.text):
            return True
        else:
            return False
    def __hash__(self):
        return hash((self.top,self.left,self.width,self.height,self.text))

    def __repr__(self):
        return str(((self.top,self.left),(self.width,self.height)))

    def __unicode__(self):
        return u"TextBox t="+unicode(self.top)+u", l="+unicode(self.left)+\
		u", w="+unicode(self.width)+u", h="+unicode(self.height)#+u", txt="+unicode(self.text)

