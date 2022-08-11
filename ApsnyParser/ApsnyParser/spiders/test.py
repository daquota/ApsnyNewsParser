import scrapy
from scrapy.http import HtmlResponse
import re
from pydispatch import dispatcher
from scrapy import signals
from datetime import datetime, timedelta, timezone
from lib import MongoDB, get_timeshift, make_announce, strip_announce, clear_announce, parse_date
from slugify import slugify
from dateutil.parser import parse
from urllib.parse import urlparse
import html
import requests
import logging
from dateutil.parser import parse


class TestSpider(scrapy.Spider):
    name = 'test'
    allowed_domains = ['sputnik-abkhazia.ru', 'apsadgil.info', 'www.apsnypress.info']
    start_urls = [
        'https://sputnik-abkhazia.ru/20220811/nekharakternaya-obraschaemost-novye-osobennosti-zabolevaemosti-kishechnoy-infektsiey-v-abkhazii-1040861809.html',
        'https://apsadgil.info/news/economics/ministr-ekonomicheskogo-razvitiya-rf-maksim-reshetnikov-pribyl-v-abkhaziyu-s-rabochim-vizitom-/',
        'https://www.apsnypress.info/ru/novosti/?format=feed'
        ]


    def __init__(self, **kwargs):
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        self.parsed_items = []
        super().__init__(**kwargs)

    def spider_closed(self, spider):
        pass

    def parse(self, response: HtmlResponse):
        source = urlparse(response.url).netloc
        if source == 'apsadgil.info':
            date = response.xpath("//div[@class='ds']/span[@class='date']/text()").extract_first()
            article_time = parse_date(date)
            print(source, article_time)
        if source == 'sputnik-abkhazia.ru':
            article_time = response.xpath("//div[@class='article__info-date']/a/@data-unixtime").extract_first()
            article_time = datetime.fromtimestamp(int(article_time), tz=timezone.utc) if article_time else ''
            article_time = get_timeshift(article_time)
            print(source, article_time)
        if source == 'www.apsnypress.info':
            date = re.search(r'<pubDate>(.*?)</pubDate>', response.text, flags=re.MULTILINE + re.DOTALL)
            date = date[1] if date else ''
            article_time = get_timeshift(parse(date))
            print(source, article_time)

