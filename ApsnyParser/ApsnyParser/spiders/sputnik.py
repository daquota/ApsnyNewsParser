"""
Паук для парсинга новостей с сайта sputnik-abkhazia.ru
"""
import re
import scrapy
from pydispatch import dispatcher
from scrapy import signals
from datetime import datetime, timedelta
from scrapy.http import HtmlResponse
from ApsnyParser.items import ApsnyparserItem
from lib import MongoDB, get_timeshift
from slugify import slugify
# from copy import deepcopy


class SputnikSpider(scrapy.Spider):
    name = 'sputnik'
    allowed_domains = ['sputnik-abkhazia.ru']
    domain = 'https://sputnik-abkhazia.ru'
    start_urls = ['https://sputnik-abkhazia.ru/Abkhazia/']

    def __init__(self, **kwargs):
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        self.parsed_items = []
        self._mongoClient = MongoDB()
        self.already_parsed = self._mongoClient.read_parsed(self.name)
        self.single = [
            # 'https://sputnik-abkhazia.ru/20220804/ot-pervogo-litsa-aslan-bzhaniya-otvetil-na-voprosy-zhurnalistov-1040717671.html'
            # 'https://sputnik-abkhazia.ru/20220804/tsifry-ot-mera-uspekhi-sukhuma-v-pervoy-polovine-2022-goda-1040720197.html'
                       ]
        super().__init__(**kwargs)

    def spider_closed(self, spider):
        print(f'{get_timeshift(datetime.now())} Spider "{spider.name}": {len(self.parsed_items)} items parsed')

    def parse(self, response: HtmlResponse):
        if self.single:
            for i in self.single:
                # if f'{self.domain}{i}' not in self.already_parsed:
                yield response.follow(i, callback=self.parse_page)
        else:
            if response.status == 200:
                links = response.xpath("//div[@class='list__content']/a/@href").extract()
                # news_ids = [re.search(r'-([0-9]+)\.html', _)[1] for _ in links]
                for i in links:
                    if f'{self.domain}{i}' not in self.already_parsed:
                        yield response.follow(i, callback=self.parse_page)

    def parse_page(self, response: HtmlResponse):
        page_id = re.search(r'-([0-9]+)\.html', response.url)
        page_id = page_id[1] if page_id else ''
        title = response.xpath("//h1/text()").extract_first()
        article_time = response.xpath("//div[@class='article__info-date']/a/@data-unixtime").extract_first()
        article_time = datetime. strptime(datetime.utcfromtimestamp(int(article_time) + 60*60*3).strftime('%H:%M:%S %d-%m-%Y'), '%H:%M:%S %d-%m-%Y') if article_time else ''
        img = response.xpath("//div[@class='photoview__open']/img/@src").extract_first()
        embed = response.xpath("//div[@class='article__announce']//div[@class='media__embed']/iframe/@src").extract()
        embed = [_ for _ in embed]
        announce = response.xpath("//div[@class='article__announce-text']/text()").extract_first()
        article = response.xpath("//div[@class='article__body']/*[(contains(@data-type, 'quote')) or (contains(@data-type, 'text')) or (contains(@data-type, 'h3'))]").extract()
        article = self.clean_article(article)
        tags = response.xpath("//ul[contains(@class, 'tag')]/li/a/text()").extract()
        link = response.url
        slug = slugify(title, max_length=64, word_boundary=True)

        item = ApsnyparserItem(
            page_id=page_id, article_time=article_time, title=title, img=img, embed=embed,
            announce=announce, article=article, tags=tags, source=self.name, link=link, slug=slug
        )
        self.parsed_items.append(item)
        yield item

    @staticmethod
    def clean_article(article):
        """
        Очистка текста новости от html-тегов и прочих ненужных вставок
        :param article: текст с куском кода блока статьи
        :return: текст, очищенный от html-тегов. содержит только <p> и <h3>
        """
        clean_article = ''
        for i in article:
            p = ''
            data_type = re.search(r'data-type="(.+?)"', i, flags=re.MULTILINE+re.DOTALL)
            data_type = data_type[1] if data_type else ''
            if data_type == 'text':
                p = re.search(r'<div class="article__text">(.*?)</div>', i, flags=re.MULTILINE+re.DOTALL)
            elif data_type == 'quote':
                p = re.search(r'<div class="article__quote-text">(.*?)</div>', i, flags=re.MULTILINE+re.DOTALL)
            elif data_type == 'h3':
                p = re.search(r'<h3 class="article__h2">(.*?)</h3>', i, flags=re.MULTILINE + re.DOTALL)
            p = p[1] if p else ''
            p = re.sub(re.compile('<.*?>'), '', p).strip()
            clean_article += ('<h3>'+p+'</h3>' if data_type == 'h3' else '<blockquote>'+p+'</blockquote>' if data_type == 'quote' else '<p>'+p+'</p>' if p else '')
        return clean_article
