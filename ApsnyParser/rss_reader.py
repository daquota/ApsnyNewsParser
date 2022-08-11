import feedparser
import ssl
from lib import MongoDB
from ApsnyParser.items import ApsnyparserItem

ssl._create_default_https_context = ssl._create_unverified_context

feed = {
    # 'sgb': 'https://sgb.apsny.land/?format=feed',
    'presidentofabkhazia': 'http://presidentofabkhazia.org/about/info/news/?rss=y',
    'minkult': 'https://minkult.apsny.land/novosti?format=feed',
    'md': 'https://md.apsny.land/novosti?format=feed',
    'sukhum': 'https://sukhum.apsny.land/novosti?format=feed',
    'mchs': 'https://mchs.apsny.land/novosti?format=feed',
    'minzdrav': 'https://minzdrav.apsny.land/novosti?format=feed',
    'genproc': 'https://genproc.apsny.land/genproc-news?format=feed',
    'mso': 'https://mso.apsny.land/novosti?format=feed',
    'minselhoz': 'https://minselhoz.apsny.land/novosti/?format=feed',
    'csi': 'https://csi.apsny.land/ru/?format=feed',
    'memory': 'https://memory.apsny.land/novosti?format=feed',
    'mkdc-sukhum': 'https://www.mkdc-sukhum.com/novosti/?format=feed',
    'opra': 'https://opra.apsny.land/novosti?format=feed',
    'repatriate': 'https://repatriate.apsny.land/novosti?format=feed'
}

mongo = MongoDB()


for i in feed:
    NewsFeed = feedparser.parse(feed[i])
    entry = NewsFeed.entries[1]
    for m in entry.keys():
        print(m, NewsFeed.entries[1][m])

    parsed = mongo.read_parsed(i)
    for k in NewsFeed.entries:
        if k['link'] not in parsed:
            page_id = k['page_id'] if 'page_id' in k.keys() else ''
            article_time = ''
            title = k['title'] if 'title' in k.keys() else ''
            img = ''
            announce = ''
            article = ''
            tags = ''
            source = i
            link = k['link'] if 'link' in k.keys() else ''
            slug = ''
            embed = ''

            item = ApsnyparserItem(
                page_id=page_id, article_time=article_time, title=title, img=img, announce=announce, article=article,
                tags=tags, source=source, link=link, slug=slug, embed=embed
            )
        print()
    # print(i, entry.keys())

