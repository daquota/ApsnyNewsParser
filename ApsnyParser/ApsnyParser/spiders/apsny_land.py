"""
Паук для парсинга группы сайтов apsny.land
"""
import scrapy
import re
from pydispatch import dispatcher
from scrapy import signals
from datetime import datetime
from scrapy.http import HtmlResponse
from ApsnyParser.items import ApsnyparserItem
from lib import MongoDB, get_timeshift, make_announce, strip_announce, clear_announce
from slugify import slugify
from dateutil.parser import parse
from urllib.parse import urlparse
import html
import requests
import logging


class ApsnyLandSpider(scrapy.Spider):
    name = 'apsny.land'
    allowed_domains = ['md.apsny.land', 'sukhum.apsny.land', 'sgb.apsny.land', 'minkult.apsny.land', 'mchs.apsny.land',
                       'minzdrav.apsny.land', 'genproc.apsny.land', 'mso.apsny.land', 'minselhoz.apsny.land',
                       'memory.apsny.land', 'opra.apsny.land', 'csi.apsny.land', 'www.mkdc-sukhum.com',
                       'repatriate.apsny.land', 'www.apsnypress.info', 'www.abkhazinform.com', 'vs-ra.org']
    start_urls = ['https://md.apsny.land/novosti?format=feed', 'https://sukhum.apsny.land/novosti?format=feed',
                  'https://sgb.apsny.land/?format=feed', 'https://minkult.apsny.land/novosti?format=feed',
                  'https://mchs.apsny.land/novosti?format=feed',
                  'https://minzdrav.apsny.land/novosti?format=feed',
                  'https://genproc.apsny.land/genproc-news?format=feed', 'https://mso.apsny.land/novosti?format=feed',
                  'https://minselhoz.apsny.land/novosti/?format=feed', 'https://csi.apsny.land/ru/?format=feed',
                  'https://memory.apsny.land/novosti?format=feed', 'https://www.mkdc-sukhum.com/novosti/?format=feed',
                  'https://opra.apsny.land/novosti?format=feed', 'https://repatriate.apsny.land/novosti?format=feed',
                  'https://www.apsnypress.info/ru/novosti?format=feed',
                  'http://www.abkhazinform.com/?format=feed', 'http://www.abkhazinform.com/intervyu/?format=feed',
                  'http://www.abkhazinform.com/tochka-zreniya/?format=feed',
                  'https://vs-ra.org/primenews/?format=feed', 'https://vs-ra.org/novosti-i-informatsiya/?format=feed'
                  ]

    def __init__(self, **kwargs):
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        self.parsed_items = []
        self._mongoClient = MongoDB()
        self.single = [
            # 'https://www.apsnypress.info/ru/novosti/item/833-obshchestvennaya-palata-gotova-sodejstvovat-dostizheniyu-obshchestvennogo-soglasiya'
                       ]
        super().__init__(**kwargs)

    def spider_closed(self, spider):
        x = [_['source'] for _ in self.parsed_items]
        xx = {i: x.count(i) for i in x}
        print(f'{get_timeshift(datetime.now())} Spider "{spider.name}": {len(self.parsed_items)} items parsed {xx}')

    def parse(self, response: HtmlResponse):
        nodes = response.xpath('//item').extract()
        # иногда rss файл приходит кривой и его распарсить строчкой выше не получается,
        # поэтому конвертируем его в текст и парсим через regexp
        if not nodes:
            text = re.sub(re.compile('[\n\r\t]*?'), '', response.text)
            nodes = re.findall(r'<item>(.*?)</item>', text, flags=re.MULTILINE + re.DOTALL)
        source = urlparse(response.url).netloc
        already_parsed = self._mongoClient.read_parsed(source)
        for i in nodes:
            link = re.search(r'<link>(.*?)</link>', i, flags=re.MULTILINE+re.DOTALL)
            link = link[1] if link else ''
            if link not in already_parsed:
                title = re.search(r'<title>(.*?)</title>', i, flags=re.MULTILINE+re.DOTALL)
                title = title[1] if title else ''
                page_id = self.get_page_id(link)
                date = re.search(r'<pubDate>(.*?)</pubDate>', i, flags=re.MULTILINE+re.DOTALL)
                date = date[1] if date else ''
                article_time = get_timeshift(parse(date))
                embed = ''
                node = html.unescape(i)
                article1 = re.search(r'K2FeedFullText">(.*?)</div>', node, flags=re.MULTILINE+re.DOTALL)
                article1 = article1[1].strip() if article1 else False
                announce1 = re.search(r'K2FeedIntroText">(.*?)</div>', node, flags=re.MULTILINE+re.DOTALL)
                announce1 = announce1[1] if announce1 else False
                if article1 and announce1:
                    announce = clear_announce(announce1)
                    article = self.clear_txt(article1)
                elif article1 and not announce1:
                    announce = make_announce(article1, 1)
                    article = self.clear_txt(article1)
                elif not article1 and announce1:
                    article = self.clear_txt(announce1)
                    announce = make_announce(article, 1)
                elif not article1 and not announce1:
                    article = ''
                    announce = ''

                img = re.search(r'<enclosure url="(.*?)".+?/>', node, flags=re.MULTILINE+re.DOTALL)
                img = img[1] if img else ''
                img = self.try_xl_image(img)

                gallery = re.search(r'K2FeedGallery">(.*?)</div>', node, flags=re.MULTILINE+re.DOTALL)
                media = self.get_gallery_img(gallery[1]) if gallery else ''

                tags = ''
                slug = slugify(title, max_length=128, word_boundary=True)

                item = ApsnyparserItem(
                    page_id=page_id, article_time=article_time, title=title, img=img, embed=embed, media=media,
                    announce=announce, article=article, tags=tags, source=source, link=link, slug=slug
                )
                self.parsed_items.append(item)
                # print(item)
                yield item

    def clear_txt(self, article):
        article = re.sub(r'<p.*?>', '<p>', article, flags=re.MULTILINE+re.DOTALL)
        article = re.sub(r'<span.*?>', '', article, flags=re.MULTILINE+re.DOTALL)
        article = re.sub(r'</span>', '', article, flags=re.MULTILINE+re.DOTALL)
        article = html.unescape(article)
        return article

    @staticmethod
    def get_gallery_img(gallery_txt):
        """
        Вытаскиваем имена файлов их html-кода карусельки
        :param gallery_txt: html-код карусельки
        :return: словарь с урлами файлов (картинок) и медиа типы
        """
        gallery = []
        li_items = re.findall(r'<li.+?>(.+?)</li>', gallery_txt, flags=re.MULTILINE+re.DOTALL)
        for i in li_items:
            try:
                file = re.search(r'href="(.+?)"', i, flags=re.MULTILINE+re.DOTALL)
                if file:
                    file_head = requests.head(file := file[1])
                    gallery.append({'file': file, 'type': file_head.headers['Content-Type']})
            except Exception as e:
                logging.error(e)
        return gallery

    @staticmethod
    def try_xl_image(img):
        """
        Проверяем если ли большая картинка
        :param img: маленькая картинка
        :return: большая картинка если есть, иначе возвращаем исходную маленькую
        """
        if img:
            img_xl = re.sub(r'_S.jpg', '_XL.jpg', img)
            if requests.head(img).status_code < 400:
                return img_xl
        return img

    @staticmethod
    def get_page_id(link):
        page_id = re.search(r'/item/([0-9]*?)-', link, flags=re.DOTALL)
        page_id = page_id[1] if page_id else ''
        return page_id
