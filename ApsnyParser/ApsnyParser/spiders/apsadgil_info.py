import scrapy
import re
from pydispatch import dispatcher
from scrapy import signals
from datetime import datetime, timedelta
from scrapy.http import HtmlResponse
from ApsnyParser.items import ApsnyparserItem
from lib import MongoDB, get_timeshift, make_announce, parse_date, strip_announce
from slugify import slugify
from dateutil.parser import parse
from urllib.parse import urlparse
import time
import requests
import logging
from copy import deepcopy


class ApsadgilInfoSpider(scrapy.Spider):
    name = 'apsadgil_info'
    domain = 'https://apsadgil.info'
    allowed_domains = ['apsadgil.info']
    start_urls = ['https://apsadgil.info/news/']

    def __init__(self, **kwargs):
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        self.parsed_items = []
        self._mongoClient = MongoDB()
        self.already_parsed = self._mongoClient.read_parsed(urlparse(self.domain).netloc)
        self.single = [
        # 'https://apsadgil.info/news/politics/komanda-minoborony-abkhazii-prinimaet-uchastie-v-konkurse-snayperskiy-rubezh-na-armi-2022-v-venesuee/'
                       ]
        super().__init__(**kwargs)

    def spider_closed(self, spider):
        print(f'{get_timeshift(datetime.now())} Spider "{spider.name}": {len(self.parsed_items)} items parsed')

    def parse(self, response: HtmlResponse):
        if len(self.single):
            for i in self.single:
                yield response.follow(i, callback=self.parse_page)
        else:
            if response.status == 200:
                items = response.xpath("//div[@class='newslist']/div[@class='item']").extract()

                for i in items:
                    link = re.search(r'href="(.+?)"', i, flags=re.MULTILINE+re.DOTALL)
                    link = f'{self.domain}{link[1]}' if link else ''
                    announce = re.search(r'class="text">(.+?)</div>', i, flags=re.MULTILINE+re.DOTALL)
                    announce = announce[1].strip() if announce else ''
                    if link not in self.already_parsed:
                        yield response.follow(link, callback=self.parse_page, cb_kwargs={'announce': deepcopy(announce)})

    def parse_page(self, response: HtmlResponse, announce):
        link = response.url
        title = response.xpath("//h1/text()").extract_first().strip()
        slug = slugify(title, max_length=128, word_boundary=True)
        date = response.xpath("//div[@class='ds']/span[@class='date']/text()").extract_first()
        article_time = parse_date(date)
        img = response.xpath("//div[@class='newsdetail']/img/@src").extract_first()
        if img:
            img = img if urlparse(img).netloc else f'{self.domain}{img}'
        detext = response.xpath("//div[@class='detext']").extract_first()
        article = self.clean_article(detext)
        devideo = response.xpath("//div[@class='newsdetail']//iframe/@src").extract()
        media = self.extract_media(detext)
        media.extend(self.get_gallery_img(devideo))
        tags = ''
        embed = ''
        page_id = int(time.mktime(article_time.timetuple()))
        source = urlparse(response.url).netloc

        item = ApsnyparserItem(
            page_id=page_id, article_time=article_time, title=title, img=img, embed=embed, media=media,
            announce=announce, article=article, tags=tags, source=source, link=link, slug=slug
        )
        self.parsed_items.append(item)
        yield item

    def extract_media(self, article):
        figure = re.findall(r'<figure>.+?src="(.+?)".+?</figure>', article, flags=re.MULTILINE+re.DOTALL)
        gallery = [x if urlparse(x).netloc else f'{self.domain}{x}'for x in figure]
        return self.get_gallery_img(gallery)

    @staticmethod
    def clean_article(article):
        """
        Очистка текста новости от html-тегов и прочих ненужных вставок
        :param article: текст с куском кода блока статьи
        :return: текст, очищенный от html-тегов. содержит только <p> и <blockquote>
        """
        clean_article = ''
        p = re.findall(r'<p.+?>(.*?)</p>', article, flags=re.MULTILINE+re.DOTALL)
        p_list = [x.strip() for x in p if x.strip()]
        for i, item in enumerate(p_list):
            if re.search(r'<b><span class="marker1">', item, flags=re.MULTILINE+re.DOTALL):
                p_list[i] = '<blockquote>'+re.sub(re.compile('<.*?>'), '', item).strip()+'</blockquote>'
            else:
                tmp = re.sub(re.compile('<.*?>'), '', item).strip()
                p_list[i] = '<p>'+tmp+'</p>' if tmp else ''
            clean_article += p_list[i]

        return clean_article

    @staticmethod
    def get_gallery_img(gallery):
        """
        Вытаскиваем имена файлов их html-кода карусельки
        :param gallery_txt: html-код карусельки
        :return: словарь с урлами файлов (картинок) и медиа типы
        """
        media = []
        for i in gallery:
            try:
                file_head = requests.head(i)
                media.append({'file': i, 'type': file_head.headers['Content-Type']})
            except Exception as e:
                logging.error(e)
        return media
