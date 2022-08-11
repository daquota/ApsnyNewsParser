# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from lib import MongoDB, S3ObjectCloud
import os
import requests
import re


class ApsnyparserPipeline:
    def __init__(self, *args, **kwargs):
        self._mongoClient = MongoDB()
        super().__init__(*args, **kwargs)

    def process_item(self, item, spider):
        if item['source'] == 'www.abkhazinform.com':
            self.try_images_dir()
            item['img'] = self.upload_img_to_s3(item['img'])
        self._mongoClient.write_one(item)
        return item

    def upload_img_to_s3(self, img):
        new_img = ''
        filename_name = re.search(r'[^/\\&\?]+\.\w{3,4}(?=([\?&].*$|$))', img)[0]
        filename = f"images/{filename_name}"
        response_pic = requests.get(img)
        with open(filename, 'wb') as file1:
            file1.write(response_pic.content)
        _aws = S3ObjectCloud()
        _aws._s3.upload_file(f"images/{filename_name}", 'apsny-news', f"{filename_name}")
        return f'https://storage.yandexcloud.net/apsny-news/{filename_name}'

    def try_images_dir(self):
        if not os.path.isdir('images'):
            try:
                os.mkdir('images')
            except OSError as error:
                print('images', error)
