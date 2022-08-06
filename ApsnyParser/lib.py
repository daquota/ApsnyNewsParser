"""
Библиотека вспомогательных функций и классов
"""
import getopt
import sys
from pymongo import MongoClient
import config as conf
import __environ__
import pytz

def get_module_name_to_run(argv):
    """
    Определяем параметры из командной строки
    :param argv: параметры командной строки
    :return: имя модуля (спайдера) для запуска
    """
    if __environ__.DEVELOPMENT_MODE:
        return 'sputnik'
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
