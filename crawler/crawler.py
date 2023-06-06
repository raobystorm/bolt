import json
import logging
import threading

# 告警关闭
import warnings
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

import boto3
import requests
from bs4 import BeautifulSoup
from lxml import etree
from rss import DEFAULT_DATETIME, httpRequest, parse_datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from sqlalchemy.orm import sessionmaker

from db import Article, Media, get_db_engine

warnings.filterwarnings("ignore")

THREAD_MAX = 4
requests.adapters.DEFAULT_RETRIES = 3
logger = logging.getLogger(__name__)

# 代理服务器
PROXIES = {"http": "127.0.0.1:7890", "https": "127.0.0.1:7890"}


SQS_QUEUE_URL = "https://sqs.us-west-2.amazonaws.com/396260505786/bolt-worker-prod"


@dataclass
class ArticleDTO:
    media_id: int
    article_id: int
    title: str
    content: str = ""
    author: str = ""
    publish_date: datetime = DEFAULT_DATETIME
    image_link: str = ""

    def any_empty(self) -> bool:
        return (
            self.content == ""
            or self.author == ""
            or self.publish_date == DEFAULT_DATETIME
            or self.image_link == ""
        )


# 函数功能：将爬取的信息写入消息队列
def send_SQS(
    *, media_id, article_id, title, s3_prefix, target_lang="zh-CN", image_link=""
):
    sqs = boto3.client("sqs", region_name="us-west-2")
    # 需要发送3个消息，分别为"summarize_article", "summarize_title", "translate_article"
    job = {
        "media_id": media_id,
        "article_id": article_id,
        "title": title,
        "s3_prefix": s3_prefix,
        "job_type": "summarize_title",
        "target_lang": target_lang,
        "image_link": image_link,
    }
    sqs.send_message(QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps(job))
    job["job_type"] = "summarize_article"
    sqs.send_message(QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps(job))
    job["job_type"] = "translate_article"
    sqs.send_message(QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps(job))
    if image_link != "":
        job["job_type"] = "get_image"
        sqs.send_message(QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps(job))


def write_s3(s3_prefix, content):
    s3 = boto3.client("s3", region_name="us-west-2")
    s3.put_object(Bucket="bolt-prod", Key=f"{s3_prefix}/article.txt", Body=content)


class myThread(threading.Thread):
    def __init__(self, article_link: str, use_selenium):
        threading.Thread.__init__(self)
        self.article_link = article_link
        self.engine = None
        self.session = None
        self.article = None
        self.media = None
        self.exit_code = 0
        self.use_selenium = use_selenium
        if use_selenium:
            options = Options()
            options.add_argument("--disable-javascript")
            options.add_argument("--disable-dev-shm-usage")
            self.driver = webdriver.Remote(
                "http://172.24.0.4:4444", DesiredCapabilities.CHROME, options=options
            )

    def run(self):
        try:
            self.engine = get_db_engine()
            Session = sessionmaker(bind=self.engine)
            with Session.begin() as db_sess:
                self.session = db_sess
                self.article: Article = (
                    self.session.query(Article)
                    .filter(Article.link_url == self.article_link)
                    .first()
                )
                host = urlparse(self.article_link)[1]
                self.media: Media = (
                    self.session.query(Media).filter(Media.base_url == host).first()
                )
                self._run()
        except Exception as e:
            self.exit_code = 1
            logger.error(f"异常url: {self.article_link}, {e}")
            # raise Exception(str(self.arteicle_url) + "出现异常")
        finally:
            self.engine.dispose()
            if self.use_selenium:
                self.driver.quit()

    def _run(self):
        # 用于写入数据库的dto
        dto = ArticleDTO(
            media_id=self.media.id, article_id=self.article.id, title=self.article.title
        )
        if self.article.publish_date != DEFAULT_DATETIME:
            dto.publish_date = self.article.publish_date

        dto = self.crawl_news_Request(dto, path="xpath")
        if dto.any_empty():
            dto = self.crawl_news_Request(dto, path="css_selector")
        if self.use_selenium:
            if dto.any_empty():
                dto = self.crawl_news_Selenium(dto, path="xpath")
            if dto.any_empty():
                dto = self.crawl_news_Selenium(dto, path="css_selector")

        # 成功爬取后更新对应的article_url的content为1，表示该url已经获取了内容
        if self.article.publish_date == DEFAULT_DATETIME:
            self.article.publish_date = (
                dto.publish_date
                if dto.publish_date != DEFAULT_DATETIME
                else datetime.now()
            )

        if self.article.author == "" and dto.author != "":
            self.article.author = dto.author

        if self.article.image_link == "" and dto.image_link != "":
            self.article.image_link = dto.image_link

        if len(dto.content) > 0:
            title_key = self.article.title.replace(" ", "_")
            pub_date = self.article.publish_date
            s3_prefix = f"Articles/media={self.media.name}/Year={pub_date.year}/Month={pub_date.month}/Day={pub_date.day}/Hour={pub_date.hour}/{title_key}"
            self.article.s3_prefix = s3_prefix
            write_s3(s3_prefix, dto.content)
            # print(df["title"], df["content"])
            send_SQS(
                media_id=self.media.id,
                article_id=self.article.id,
                title=self.article.title,
                s3_prefix=self.article.s3_prefix,
                image_link=self.article.image_link,
            )
            self.check_result(dto.content)

    # 函数功能：使用request爬取网站
    # 参数：article_url：链接地址，path：选择器形式，枚举值：xpath、css_selector，默认xpath，
    # 函数返回：pd.Dataframe,包含标题、日期、作者、图片（可选）、正文、链接地址（同article_url）
    def crawl_news_Request(self, dto: ArticleDTO, path="xpath") -> ArticleDTO:
        # 获取title并查重
        response = httpRequest(self.article.link_url)
        if response == "":
            return
        html = response.text
        # 获取xpath
        if path == "xpath":
            html = etree.HTML(html)

            if dto.content == "" and len(html.xpath(self.media.xpath_content)) > 0:
                dto.content = html.xpath(self.media.xpath_content)[0].xpath("string(.)")
            if (
                dto.publish_date == DEFAULT_DATETIME
                and len(html.xpath(self.media.xpath_publish_date)) > 0
            ):
                dto.publish_date = parse_datetime(
                    html.xpath(self.media.xpath_publish_date)[0].text
                )
            if dto.author == "" and len(html.xpath(self.media.xpath_author)) > 0:
                dto.author = html.xpath(self.media.xpath_author)[0].text
            if dto.image_link == "" and len(html.xpath(self.media.xpath_image_url)) > 0:
                dto.image_link = html.xpath(self.media.xpath_image_url)[0]

        # 获取css_selector
        if path == "css_selector":
            bs = BeautifulSoup(html, "html.parser")

            # 正文分布在多个段落P中，需要获取每一个段落的文字
            content = ""
            length = len(bs.select(self.media.selector_content))
            for i in range(0, length):
                content += bs.select(self.media.selector_content)[i].text

            if dto.content == "" and len(content) > 0:
                dto.content = content

            # 获取publish_date
            if (
                dto.publish_date == DEFAULT_DATETIME
                and len(bs.select(self.media.selector_publish_date)) > 0
            ):
                dto.publish_date = parse_datetime(
                    bs.select(self.media.selector_publish_date)[0].text
                )
            # 获取author
            if dto.author == "" and len(bs.select(self.media.selector_author)) > 0:
                dto.author = bs.select(self.media.selector_author)[0].text
            # 获取image_link
            if (
                dto.image_link == ""
                and len(bs.select(self.media.selector_image_url)) > 0
            ):
                dto.image_link = bs.select(self.media.selector_image_url)[0].attrs[
                    "src"
                ]
            # write_dir = write_dir + title.replace(" ", "_")
        return dto

    # 函数功能：使用selenium爬取网站
    # 参数：article_url：链接地址，path：选择器形式，枚举值：xpath、css_selector，默认xpath，
    # 函数返回：pd.Dataframe,包含标题、日期、作者、图片（可选）、正文、链接地址（同article_url）
    def crawl_news_Selenium(self, dto: ArticleDTO, path="xpath"):
        self.driver.get(self.article.link_url)
        wait = WebDriverWait(self.driver, timeout=10)
        if path == "xpath":
            try:
                if dto.content == "":
                    dto.content = wait.until(
                        EC.presence_of_element_located(
                            (By.XPATH, self.media.xpath_content)
                        )
                    ).text
            except Exception:
                return
            try:
                if dto.image_link == "":
                    dto.image_link = wait.until(
                        EC.presence_of_element_located(
                            (By.XPATH, self.media.xpath_image_url)
                        )
                    ).get_attribute("src")

                if dto.publish_date == DEFAULT_DATETIME:
                    dto.publish_date = parse_datetime(
                        wait.until(
                            EC.presence_of_element_located(
                                (By.XPATH, self.media.xpath_publish_date)
                            )
                        ).text
                    )

                if dto.author == "":
                    dto.author = wait.until(
                        EC.presence_of_element_located(
                            (By.XPATH, self.media.xpath_author)
                        )
                    ).text
            except Exception:
                pass
        if path == "css_selector":
            try:
                if dto.content == "":
                    dto.content = wait.until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, self.media.selector_content)
                        )
                    ).text
            except Exception:
                return
            try:
                if dto.image_link == "":
                    dto.image_link = wait.until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, self.media.selector_image_url)
                        )
                    ).get_attribute("src")
                if dto.publish_date == DEFAULT_DATETIME:
                    dto.publish_date = parse_datetime(
                        wait.until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, self.media.selector_publish_date)
                            )
                        ).text
                    )
                if dto.author == "":
                    dto.author = wait.until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, self.media.selector_author)
                        )
                    ).text
            except Exception:
                pass

        return dto

    def check_result(self, content):
        if content == "":
            logger.error(f"文章内容抓取异常: {self.article.link_url}")
        if self.article.author == "":
            logger.error(f"文章作者抓取异常: {self.article.link_url}")
        if self.article.image_link == "":
            logger.error(f"文章图片链接异常: {self.article.link_url}")
        if self.article.publish_date == DEFAULT_DATETIME:
            logger.error(f"文章发布日期异常：{self.article.link_url}")


def thread_pool_worker(article_link: str):
    thread = myThread(article_link=article_link, use_selenium=False)
    thread.start()


def main():
    # news_links=["https://www.nytimes.com/2023/05/12/business/media/last-hollywood-writers-strike.html"]
    # 多线程版本
    with ThreadPoolExecutor(max_workers=THREAD_MAX) as pool:
        engine = get_db_engine()
        try:
            with sessionmaker(bind=engine).begin() as db_sess:
                # 使用s3_prefix是否为空来标记article的内容是否爬取成功
                article_links = (
                    db_sess.query(Article.link_url)
                    .filter(Article.s3_prefix == "")
                    .all()
                )
                for article_link in article_links:
                    pool.submit(thread_pool_worker, article_link[0])
        finally:
            db_sess.close()
            engine.dispose()


if __name__ == "__main__":
    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    handler = logging.FileHandler("crawler.log")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    main()
    # 单线程版本
    # engine = get_db_engine()
    # try:
    #     with sessionmaker(bind=engine).begin() as db_sess:
    #         article_links = (
    #             db_sess.query(Article.link_url).filter(Article.s3_prefix == "").all()
    #         )
    #         for article_link in article_links:
    #             thread = myThread(article_link=article_link[0], use_selenium=False)
    #             thread.run()
    # finally:
    #     engine.dispose()
