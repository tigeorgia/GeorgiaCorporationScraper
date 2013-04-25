import uuid, os
import codecs
from scrapy.exceptions import IgnoreRequest
from scrapy.http import TextResponse
from registry.settings import PDFTOHTML_TEMP_DIR as tmp
class DropDjvuMiddleware(object):
    
    def __init__(self, stats):
        self.stats = stats
            
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.stats)
    
    def process_response(self, request, response, spider):
        if response.headers['Content-Type'] != 'image/vnd.djvu':
            return response
        else:
            self.stats.inc_value('djvu-extracts')
            raise IgnoreRequest

# Custom middleware that downloads a PDF file, converts
# it to HTML / XML using either Python or an external
# program, and then provides the result as if it were a
# request.
class PdfToHtmlMiddleware(object):
    
    def process_response(self, request, response, spider):
        # Relies on the server setting the content-type header 
        # correctly.
        if response.headers['Content-Type'] != "application/pdf":
            return response
        
        # If it's a PDF
        else:
            # Generate a unique file name
            fname = str(uuid.uuid1())
            
            # Open file for writing
            # Dump response to file
            with open(tmp+'/'+fname+'.pdf', 'wb') as f:
                f.write(response.body)

            # Execute PDF-to-HTML (however)
            # pdftohtml from the poppler suite, executed with the
            # following options:
            # -q: Don't print messages or errors
            # -xml: Output xml, not HTML
            # -s: Generate a single document with all PDF pages
            # -i: ignore images
            # -enc: Encoding
            os.system('pdftohtml -q -xml -s -i -enc UTF-8 {} {}'.format(tmp+'/'+fname+'.pdf',tmp+'/'+fname))
            # Read output
            with codecs.open(tmp+'/'+fname+'.xml', 'rb',encoding="utf-8") as fin:
                new_body = fin.read()
            
            # Clean up after ourselves
            os.remove(tmp+'/'+fname+'.pdf')
            os.remove(tmp+'/'+fname+'.xml')

            # Construct new response
            return TextResponse(url=response.url, encoding="utf-8",
                        status=response.status, headers=response.headers,
                        body=new_body, flags=response.flags)
