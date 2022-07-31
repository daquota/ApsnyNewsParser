import scrapy


class ApsnyparserItem(scrapy.Item):
    page_id = scrapy.Field()
    article_time = scrapy.Field()
    title = scrapy.Field()
    img = scrapy.Field()
    announce = scrapy.Field()
    article = scrapy.Field()
    tags = scrapy.Field()
    source = scrapy.Field()
    link = scrapy.Field()
    _id = scrapy.Field()
