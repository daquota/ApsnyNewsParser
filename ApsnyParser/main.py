"""
Основной файл для запуска пауков
Для запуска из командной строки: main.py -m spider_name
"""
import sys
import lib
from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings

from ApsnyParser import settings as apsnysettings
from ApsnyParser.spiders.sputnik import SputnikSpider


def sputnik_spider():
    crawler_settings = Settings()
    crawler_settings.setmodule(apsnysettings)
    process = CrawlerProcess(settings=crawler_settings)
    process.crawl(SputnikSpider)
    process.start()


if __name__ == '__main__':
    module = lib.get_module_name_to_run((sys.argv[1:]))
    if module == 'sputnik':
        sputnik_spider()