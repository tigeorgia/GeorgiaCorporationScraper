from scrapy.contrib.exporter import JsonLinesItemExporter
from scrapy import signals
import registry.items
import codecs

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/topics/item-pipeline.html

# Exports to multiple JsonLines files, one file per Item
# in items.py
class MultiFileJsonLinesPipeline(object):
    def __init__(self):
        self.exporters = {}
        self.files = []

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        crawler.signals.connect(pipeline.spider_opened, signals.spider_opened)
        crawler.signals.connect(pipeline.spider_closed, signals.spider_closed)
        return pipeline

    def spider_opened(self, spider):
        directory = dir(registry.items)
        for name in directory:
            if name not in ['__builtins__','__doc__','__file__','__name__','__package__']:
                ofile = codecs.open(name+".json",'w+b',encoding="utf-8")
                self.files.append(ofile)
                self.exporters[name] = JsonLinesItemExporter(ofile)
                self.exporters[name].start_exporting()

    def spider_closed(self, spider):
        for e in self.exporters:
            self.exporters[e].finish_exporting()
        for f in self.files:
            f.close()
    
    def process_item(self, item, spider):
        item_name = item.__class__.__name__
        self.exporters[item_name].export_item(item)
        return item
