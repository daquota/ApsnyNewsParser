"""
Библиотека вспомогательных функций и классов
"""
import getopt
import sys
from pymongo import MongoClient
import config as conf
import __environ__
import credentials as cr
import pytz
import re
import html
from dateutil.parser import parse
import boto3
from datetime import datetime, timedelta, timezone


def get_module_name_to_run(argv):
    """
    Определяем параметры из командной строки
    :param argv: параметры командной строки
    :return: имя модуля (спайдера) для запуска
    """
    if __environ__.DEVELOPMENT_MODE:
        return __environ__.DEV_SPIDER
    module = ''
    opts, args = getopt.getopt(argv, "m:k")
    # print(opts, args)
    if not len(opts) and not len(args):
        print("usage: main.py -m module")
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-m':
            module = arg
    return module


class MongoDB:
    """
    Интерфейс для работы с MongoDB
    """
    def __init__(self):
        _client = MongoClient('localhost', 27017)
        self._mongo_base = _client[conf.MONGO_DB]
        self._collection = self._mongo_base[conf.MONGO_COLLECTION]

    def write_one(self, item):
        result = 0
        if len(item) > 0:
            result = self._collection.insert_one(item)
        return result

    def read_parsed(self, source):
        """
        Прочитали урлы новостей, которые уже сохранены в базе
        :param source: идентификатор сайта на котором парсим новости
        :return: возвращает список урлов новостей, которые уже сохранены в базе
        """
        result = self._collection.find({"source": source}, projection={'link': 1}, sort=[("page_id", -1)]).limit(500)
        parsed = [_['link'] for _ in result]
        return parsed


def get_timeshift(time):
    """
    Добавляет смещение для московского времени, если исходное время в  UTC
    :param time: дата
    :return: скорректированная дата
    """
    return time.astimezone(pytz.timezone('Europe/Moscow'))


def make_announce(text, sentences):
    """
    Делает анонс статьи из первых предложений статьи
    :param text: текст статьи
    :param sentences: количество предложений
    :return: текст анонса, очищенный от html-тегов
    """
    announce = re.sub(r'<strong>.+?</strong>', '', text)
    announce = html.unescape(re.sub(re.compile('<.*?>'), ' ', announce)).lstrip('. ')
    announce = '. '.join(announce.split('. ')[:sentences]).strip()
    return announce


def clear_announce(text):
    announce = re.sub(r'<strong>.+?</strong>', '', text)
    announce = html.unescape(re.sub(re.compile('<.*?>'), '', announce)).lstrip('. ')
    return announce


def parse_date(date):
    """
    Конвертер для русских дат
    :param date:
    :return:
    """
    monthes = {'января': 'january', 'февраля': 'february', 'марта': 'march',
               'апреля': 'april', 'мая': 'may', 'июня': 'june',
               'июля': 'july', 'августа': 'august', 'сентября': 'september',
               'октября': 'october', 'ноября': 'november', 'декабря': 'december'
               }
    date = str(date).lower()+'+0300'
    for i in monthes:
        date = re.sub(f'{i}', monthes[i], date)
    return datetime.strptime(date, '%d %B %Y %H:%M%z')


def strip_announce(txt, max_char):
    """
    Обрезаем анонс до заданной длинны
    :param txt: Исходный текст анонса
    :param max_char: Максимальное число символов
    :return: Обрезанный анонс
    """
    ch = txt.split(' ')
    lead = ''
    for i in ch:
        if max_char >= 0:
            lead += ' ' + i
            max_char -= len(i)
        else:
            lead = lead.strip()
            lead += '...'
            break
    return lead


class S3ObjectCloud:
    def __init__(self):
        self._session = boto3.session.Session(aws_access_key_id=cr.key_id,
                                              aws_secret_access_key=cr.secret_key,
                                              region_name='ru-central1')
        self._s3 = self._session.client(service_name='s3', endpoint_url='https://storage.yandexcloud.net')

