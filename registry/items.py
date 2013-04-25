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
    title = Field()
    link = Field()
    date = Field()

# A downloadable document associated
# with a particular corporation.
class CorporationDocument(Document):
    fk_corp_id_code = Field()
    registration_num = Field()

# Downloadable document associated with a corporation and a registry
# statement for that corporate.
class StatementDocument(CorporationDocument):
    fk_stmnt_id_code_reestri_db = Field()

# A Registry Statement about a corporation. This is an official
# action by the Registry on a matter relating to the corporation.
# There will be at least one person mentioned in each Statement;
# the details of these people will be stored as a PersonCorpRelation.
class RegistryStatement(Item):
    statement_num = Field()
    registration_num = Field()
    statement_type = Field()
    id_reestri_db = Field()
    service_cost = Field()
    payment = Field()
    outstanding = Field()
    id_code_legal = Field() # Refers to the corp for which this was prepared
    name = Field() # Ditto, and so on down.
    classification = Field()
    reorganization_type = Field()
    quantity = Field() # No idea what this refers to.
    changed_info = Field()
    attached_docs_desc = Field()
    additional_docs = Field()
    issued_docs = Field()
    notes = Field()

class RegistryExtract(Item):
    fk_corp_id_code = Field()
    date = Field()
    corp_address = Field()
    corp_email = Field()

class Person(Item):
    name = Field()
    personal_code = Field()
    address = Field()
    dob = Field()
    nationality = Field()

# Represents a direct relationship between a person and a corporation
class PersonCorpRelation(Item):
    person = Field()
    fk_corp_id_code = Field()
    relation_type = Field()
    cite_type = Field()
    cite_link = Field()
