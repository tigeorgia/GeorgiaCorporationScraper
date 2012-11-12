from scrapy.item import Item, Field

class Corporation(Item):
    id_code_legal = Field()
    personal_code = Field() # Mainly (solely?) for individual entrepreneurs.
    state_reg_code = Field()
    name = Field()
    classification = Field()
    registration_date = Field()
    status = Field()
    id_code_reestri_db = Field()
    no_docs = Field()

# A downloadable document
class Document(Item):
    filename = Field()
    link = Field()

# A downloadable document associated
# with a particular corporation.
class CorporationDocument(Document):
    fk_corp_id_code_reestri_db = Field()

class Person(Item):
    name = Field()
    personal_code = Field()
    address = Field()
    dob = Field()
