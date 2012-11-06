# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/topics/items.html

from scrapy.item import Item, Field

class Corporation(Item):
    classification = Field()
    id_code_url = Field()
    id_code_legal = Field()
    personal_code = Field() # Mainly (solely?) for individual entrepreneurs.
    state_reg_code = Field()
    name = Field()
    status = Field()
