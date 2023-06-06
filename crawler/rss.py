import logging
import random

# 告警关闭
import warnings
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from sqlalchemy.orm import sessionmaker
from urllib3.util.retry import Retry

from db import Article, Media, get_db_engine

warnings.filterwarnings("ignore")

# UA 列表
USER_AGENT_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1",
    "Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 Edg/87.0.664.75",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.18363",
]
# headers={"User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36'}
# 获取新闻链接的rss源
RSS_URLS = [
    "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Space.xml",
    #'https://rss.nytimes.com/services/xml/rss/nyt/Sports.xml',
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    #'https://rss.nytimes.com/services/xml/rss/nyt/Upshot.xml',
    "https://www.newsweek.com/rss",
    "https://www.forbes.com/real-time/feed/",
]

logger = logging.getLogger(__name__)

# 使用1970-01-01 00：00：00作为时间戳的空值
DEFAULT_DATETIME = datetime(1970, 1, 1, 0, 0, 0)


def parse_datetime(datetime_s: str) -> datetime:
    try:
        return datetime.strptime(datetime_s, "%a, %d %b %Y %H:%M:%S %z")
    except (ValueError, AttributeError):
        return DEFAULT_DATETIME


# 函数功能：实现httpRequest功能
# 函数返回：返回html代码
def httpRequest(url):
    try:
        session = requests.Session()
        retry = Retry(connect=3, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        # response = session.get(url, headers=headers,proxies=proxies, verify=False, timeout=30)
        headers = {"User-Agent": random.choice(USER_AGENT_LIST)}
        session.headers.update({"User-Agent": headers["User-Agent"]})
        response = session.get(url, headers=headers, timeout=30)
        # print(session.headers['user-agent'])
        if response.status_code == 200:
            return response
    except Exception as e:
        logger.error(f"httpRequests失败: {url}, {e}")
        return ""


# 函数功能：实现解析rss并返回新闻链接
# 参数：rss_urls：rss源列表
# 函数返回：新闻http链接, title和发布日期的列表
def get_news_links(rss_urls: list[str]) -> list[tuple]:
    news_links = []
    if type(news_links) != list:
        return
    for url in rss_urls:
        try:
            rs = httpRequest(url)
            soup = BeautifulSoup(rs.content, "xml")
            entries = soup.find_all("item")
            for i in entries:
                link = i.link.text
                title = i.title.text
                pub_date = parse_datetime(i.pubDate.text)
                # summary = i.summary.text
                # print(f'Link:{link}\n\n------------------------\n')
                news_links.append((link, title, pub_date, url))
        except Exception as e:
            logger.error(f"get_news_links出现异常: {url}, {e}")
            continue
    return news_links


def rss_crawler():
    engine = get_db_engine()
    db_sess = sessionmaker(bind=engine)()
    try:
        news_links = get_news_links(RSS_URLS)
        links = list(map(lambda x: x[0], news_links))
        exists = list(
            map(
                lambda x: x[0],
                list(
                    db_sess.query(Article.link_url)
                    .filter(Article.link_url.in_(links))
                    .all()
                ),
            )
        )
        news_links = list(filter(lambda x: x[0] not in exists, news_links))
        articles = []

        for link, title, pub_date, rss_url in news_links:
            media_id = (
                db_sess.query(Media.id).filter(Media.rss_url == rss_url).first()[0]
            )
            articles.append(
                Article(
                    media_id=media_id,
                    title=title,
                    link_url=link,
                    author="",
                    s3_prefix="",
                    image_link="",
                    publish_date=pub_date,
                )
            )

        db_sess.add_all(articles)
        db_sess.commit()
    finally:
        db_sess.close_all()
        engine.dispose()


if __name__ == "__main__":
    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    handler = logging.FileHandler("crawler.log")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    rss_crawler()
