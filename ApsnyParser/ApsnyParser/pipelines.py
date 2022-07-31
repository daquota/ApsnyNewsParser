# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from lib import MongoDB


class ApsnyparserPipeline:
    def __init__(self, *args, **kwargs):
        self._mongoClient = MongoDB()
        super().__init__(*args, **kwargs)

    def process_item(self, item, spider):
        self._mongoClient.write_one(item)
        return item
