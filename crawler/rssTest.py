import random
import threading
# 告警关闭
import warnings
from datetime import datetime
from urllib.parse import urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from lxml import etree
from requests.adapters import HTTPAdapter
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from sqlalchemy.orm import sessionmaker
from urllib3.util.retry import Retry

from db import Article, Media, get_db_engine

warnings.filterwarnings("ignore")

# 全局变量部分
threadmax = threading.BoundedSemaphore(5)
requests.adapters.DEFAULT_RETRIES = 3
# 代理服务器
proxies = {"http": "127.0.0.1:7890", "https": "127.0.0.1:7890"}
# UA 列表
user_agent_list = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1",
    "Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 Edg/87.0.664.75",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.18363",
]
# headers={"User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36'}
# 获取新闻链接的rss源
rss_urls = [
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
# 获取新闻链接对应的内容是否已经爬取，如果已经爬取df['content']=1否则为0，对于为零的内容可重复尝试爬取几次提高成功率
df_result = pd.DataFrame(columns=["site_url", "content"])


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
        headers = {"User-Agent": random.choice(user_agent_list)}
        session.headers.update({"User-Agent": headers["User-Agent"]})
        response = session.get(url, headers=headers, timeout=30)
        # print(session.headers['user-agent'])
        if response.status_code == 200:
            return response
    except:
        return ""


# 函数功能：实现解析rss并返回新闻链接
# 参数：rss_urls：rss源列表
# 函数返回：新闻http链接列表
def get_news_links(rss_urls: list[str]):
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
                # summary = i.summary.text
                # print(f'Link:{link}\n\n------------------------\n')
                news_links.append(link)
        except:
            print(url + "出现异常")
            continue
    return news_links


class myThread(threading.Thread):
    def __init__(self, site_url):
        threading.Thread.__init__(self)
        engine = get_db_engine()
        self.session = sessionmaker(bind=engine)()
        self.site_url = site_url
        host = urlparse(site_url)[1]
        self.media = self.session.query(Media).filter(Media.name == host).first()
        self.exit_code = 0

    def run(self):
        try:
            self._run()
        except Exception:
            self.exit_code = 1
            threadmax.release()
            with open("异常url.txt", "a") as f:
                datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                f.write(self.site_url + "\n")
            # raise Exception(str(self.site_url) + "出现异常")
        finally:
            self.session.commit()
            self.session.close()

    def _run(self):
        threadmax.acquire()
        # 用于写入数据库的df
        df = self.crawl_news_Request(path="xpath")
        content_len = sum(map(len, df["content"]))
        if content_len == 0:
            df = self.crawl_news_Request(path="css_selector")
            content_len = sum(map(len, df["content"]))
        if content_len == 0:
            df = self.crawl_news_Selenium(path="xpath")
            content_len = sum(map(len, df["content"]))
        if content_len == 0:
            df = self.crawl_news_Selenium(path="css_selector")
        # 成功爬取后更新对应的site_url的content为1，表示该url已经获取了内容
        rows = df_result.site_url == self.site_url
        df_result.loc[rows, "title"] = df["title"][0]
        df_result.loc[rows, "content"] = df["content"][0]
        # TODO: 完善DB部分和S3，SQS
        s3_prefix = f"Articles/media={self.media.name}/Year={year}/Month={month}/Day={day}/Hour={hour}/"
        article = Article(
            media_id=self.media.id,
            title=df["title"],
            author=df["author"],
            link_url=df["link_url"],
            s3_prefix=s3_prefix,
        )
        self.session.add(article)
        # write_s3(self.Media, df["title"], df["content"])
        datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        with open("成功url.txt", "a") as f:
            f.write(self.site_url + "\n")
        # print(df["title"], df["content"])
        # send_SQS(self.Media, df["title"])
        self.session.commit()
        threadmax.release()

    # 函数功能：使用request爬取网站
    # 参数：site_url：链接地址，path：选择器形式，枚举值：xpath、css_selector，默认xpath，
    # 函数返回：pd.Dataframe,包含标题、日期、作者、图片（可选）、正文、链接地址（同site_url）
    def crawl_news_Request(self, path="xpath"):
        # 获取text_path（指写入s3路径）
        text_path = ""
        # 获取title并查重
        response = httpRequest(self.site_url)
        if response == "":
            return
        html = response.text
        # 获取xpath
        if path == "xpath":
            html = etree.HTML(html)
            # title、content为必须
            title = html.xpath(self.media.xpath_title)[0].text
            content = html.xpath(self.media.xpath_content)[0].xpath("string(.)")
            publish_date = author = image_path = ""
            if len(html.xpath(self.media.xpath_publish_date)) > 0:
                publish_date = html.xpath(self.media.xpath_publish_date)[0].text
            if len(html.xpath(self.media.xpath_author)) > 0:
                author = html.xpath(self.media.xpath_author)[0].text
            if len(html.xpath(self.media.xpath_image_url)) > 0:
                image_path = html.xpath(self.media.xpath_image_url)[0]
        # 获取css_selector
        if path == "css_selector":
            bs = BeautifulSoup(html, "html.parser")
            # title、content为必须
            title = bs.select(self.media.selector_title)[0].text
            # 正文分布在多个段落P中，需要获取每一个段落的文字
            content = ""
            length = len(bs.select(self.media.selector_content))
            for i in range(0, length):
                content += bs.select(self.media.selector_content)[i].text
            publish_date = author = image_path = ""
            # 获取publish_date
            if len(bs.select(self.media.selector_publish_date)) > 0:
                publish_date = bs.select(self.media.selector_publish_date)[0].text
            # 获取author
            if len(bs.select(self.media.selector_author)) > 0:
                author = bs.select(self.media.selector_author)[0].text
            # 获取image_path
            image_path = ""
            if len(bs.select(self.media.selector_image_url)) > 0:
                image_path = bs.select(self.media.selector_image_url)[0].attrs["src"]
            # write_dir = write_dir + title.replace(" ", "_")
        df = pd.DataFrame(
            {
                "title": [title],
                "content": [content],
                "link_url": [site_url],
                "text_path": [text_path],
                "publish_date": [publish_date],
                "author": [author],
                "image_path": [image_path],
            }
        )
        return df

    # 函数功能：使用selenium爬取网站
    # 参数：site_url：链接地址，path：选择器形式，枚举值：xpath、css_selector，默认xpath，
    # 函数返回：pd.Dataframe,包含标题、日期、作者、图片（可选）、正文、链接地址（同site_url）
    def crawl_news_Selenium(self, path="xpath"):
        chrome_options = Options()
        chrome_options.add_argument("--disable-javascript")
        driver = webdriver.Chrome(chrome_options=chrome_options)
        driver.get(self.site_url)
        # 获取text_path（指写入s3路径）
        text_path = ""
        wait = WebDriverWait(driver, timeout=10)
        if path == "xpath":
            # title、content为必须
            try:
                title = wait.until(
                    EC.presence_of_element_located((By.XPATH, self.media.xpath_title))
                ).text
                content = wait.until(
                    EC.presence_of_element_located((By.XPATH, self.media.xpath_content))
                ).text
            except:
                return
            publish_date = author = image_path = ""
            try:
                image_path = wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, self.media.xpath_image_url)
                    )
                ).get_attribute("src")
                publish_date = wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, self.media.xpath_publish_date)
                    )
                ).text
                author = wait.until(
                    EC.presence_of_element_located((By.XPATH, self.media.xpath_author))
                ).text
            except:
                pass
        if path == "css_selector":
            # title、content为必须
            try:
                title = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, self.media.selector_title)
                    )
                ).text
                content = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, self.media.selector_content)
                    )
                ).text
            except:
                return
            publish_date = author = image_path = ""
            try:
                image_path = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, self.media.selector_image_url)
                    )
                ).get_attribute("src")
                publish_date = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, self.media.selector_publish_date)
                    )
                ).text
                author = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, self.media.selector_author)
                    )
                ).text
            except:
                pass
        df = pd.DataFrame(
            {
                "title": [title],
                "content": [content],
                "link_url": [site_url],
                "text_path": [text_path],
                "publish_date": [publish_date],
                "author": [author],
                "image_path": [image_path],
            }
        )
        return df


if __name__ == "__main__":
    thread_list = []
    news_links = get_news_links(rss_urls)
    with open("siteurl.txt", "a") as f:
        for i in news_links:
            f.write(i + "\n")
    df_result["site_url"] = news_links
    df_result["title"] = ""
    df_result["content"] = ""
    # news_links=["https://www.nytimes.com/2023/05/12/business/media/last-hollywood-writers-strike.html"]
    # 多线程版本
    for site_url in df_result[df_result["content"] == ""]["site_url"]:
        thread = myThread(site_url)
        thread.start()
        thread_list.append(thread)
    for t in thread_list:
        t.join()
    with open("异常url.txt", "r") as f:
        failed_urls = f.readlines()
        for i in range(len(failed_urls)):
            failed_urls[i] = failed_urls[i].replace("\n", "")
    # 对于没有爬取到内容的url，再爬取n_repeat次
    n_repeat = 3
    i = 0
    while i < n_repeat:
        i = i + 1
        # 内容为空的网址继续尝试爬取几次
        for site_url in df_result[df_result["content"] == ""]["site_url"]:
            try:
                thread = myThread(site_url)
                df = thread.crawl_news_Request(path="css_selector")
                # df=crawl_news(site_url)
                rows = df_result.site_url == site_url
                df_result.loc[rows, "title"] = df["title"][0]
                df_result.loc[rows, "content"] = df["content"][0]
                with open("二次成功url.txt", "a") as f:
                    f.write(
                        datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                        + " "
                        + site_url
                        + "\n"
                    )
                # print(df["title"][0], df["content"][0])
            except Exception as e:
                with open("二次异常url.txt", "a") as f:
                    f.write(
                        datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                        + " "
                        + site_url
                        + " error info: "
                        + str(e)
                        + "\n"
                    )
                continue
    df_result.to_excel("result.xlsx", index=False)
    # 单线程版本
    # for site_url in news_links:
    #     try:
    #         df=crawl_news_Request(site_url,path="css_selector")
    #         #df=crawl_news(site_url)
    #         now = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    #         f = open("成功url.txt", "a")
    #         f.write(now + " " + site_url + "\n")
    #         f.close()
    #         print(df["title"][0], df["content"][0])
    #     except Exception as e:
    #         f = open("异常url.txt", "a")
    #         now = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    #         f.write(now + " " + site_url +" error info: " +str(e)+"\n")
    #         f.close()
    #         continue
