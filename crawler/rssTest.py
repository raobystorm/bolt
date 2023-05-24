# import newspaper
# import newspaper
import datetime
import random
import threading

# 告警关闭
import warnings
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
from urllib3.util.retry import Retry

from db import Media

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
        response = session.get(url, headers=headers, proxies=proxies, timeout=30)
        # print(session.headers['user-agent'])
        if response.status_code == 200:
            return response
    except:
        return ""


# 函数功能：获取媒体的xpath列表
def get_xpaths(url, session):
    host = urlparse(url)[1]
    media = session.query(Media).filter(Media.name == host).first()
    return (
        media.xpath_title,
        media.xpath_publish_date,
        media.xpath_author,
        media.xpath_image_url,
        media.xpath_content,
    )


# 函数功能：获取媒体的css_selector列表
def get_css_selectors(url, session):
    host = urlparse(url)[1]
    # 应从数据库获取，分别对应title、date、author、imagepath、content,测试代码直接填写
    media = session.query(Media).filter(Media.name == host).first()
    return (
        media.selector_title,
        media.selector_publish_date,
        media.selector_author,
        media.selector_image_url,
        media.selector_content,
    )


# 函数功能：实现解析rss并返回新闻链接
# 参数：rss_urls：rss源列表
# 函数返回：新闻http链接列表
def get_news_links(rss_urls):
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


# 函数功能：使用request爬取网站
# 参数：site_url：链接地址，path：选择器形式，枚举值：xpath、css_selector，默认xpath，
# 函数返回：pd.Dataframe,包含标题、日期、作者、图片（可选）、正文、链接地址（同site_url）
def crawl_news_Request(site_url, path="xpath"):
    # 获取text_path（指写入s3路径）
    text_path = ""
    # 获取title并查重
    response = httpRequest(site_url)
    if response == "":
        return
    html = response.text
    # 获取xpath
    if path == "xpath":
        xpaths = get_xpaths(site_url)
        html = etree.HTML(html)
        # title、content为必须
        title = html.xpath(xpaths[0])[0].text
        content = html.xpath(xpaths[4])[0].xpath("string(.)")
        publish_date = author = image_path = ""
        if len(html.xpath(xpaths[1])) > 0:
            publish_date = html.xpath(xpaths[1])[0].text
        if len(html.xpath(xpaths[2])) > 0:
            author = html.xpath(xpaths[2])[0].text
        if len(html.xpath(xpaths[3])) > 0:
            image_path = html.xpath(xpaths[3])[0]
    # 获取css_selector
    if path == "css_selector":
        css_selectors = get_css_selectors(site_url)
        bs = BeautifulSoup(html, "html.parser")

        # title、content为必须
        title = bs.select(css_selectors[0])[0].text
        # 正文分布在多个段落P中，需要获取每一个段落的文字
        content = ""
        length = len(bs.select(css_selectors[4]))
        for i in range(0, length):
            content += bs.select(css_selectors[4])[i].text
        publish_date = author = image_path = ""
        # 获取publish_date
        if len(bs.select(css_selectors[1])) > 0:
            publish_date = bs.select(css_selectors[1])[0].text
        # 获取author
        if len(bs.select(css_selectors[2])) > 0:
            author = bs.select(css_selectors[2])[0].text
        # 获取image_path
        image_path = ""
        if len(bs.select(css_selectors[3])) > 0:
            image_path = bs.select(css_selectors[3])[0].attrs["src"]
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
def crawl_news_Selenium(site_url, path="xpath"):
    chrome_options = Options()
    chrome_options.add_argument("--disable-javascript")
    driver = webdriver.Chrome(chrome_options=chrome_options)
    driver.get(site_url)
    # 获取text_path（指写入s3路径）
    text_path = ""
    wait = WebDriverWait(driver, timeout=10)
    if path == "xpath":
        xpaths = get_xpaths(site_url)
        # title、content为必须
        try:
            title = wait.until(
                EC.presence_of_element_located((By.XPATH, xpaths[0]))
            ).text
            content = wait.until(
                EC.presence_of_element_located((By.XPATH, xpaths[4]))
            ).text
        except:
            return
        publish_date = author = image_path = ""
        try:
            image_path = wait.until(
                EC.presence_of_element_located((By.XPATH, xpaths[3]))
            ).get_attribute("src")
            publish_date = wait.until(
                EC.presence_of_element_located((By.XPATH, xpaths[1]))
            ).text
            author = wait.until(
                EC.presence_of_element_located((By.XPATH, xpaths[2]))
            ).text
        except:
            pass
    if path == "css_selector":
        css_selectors = get_css_selectors(site_url)
        # title、content为必须
        try:
            title = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, css_selectors[0]))
            ).text
            content = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, css_selectors[4]))
            ).text
        except:
            return
        publish_date = author = image_path = ""
        try:
            image_path = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, css_selectors[3]))
            ).get_attribute("src")
            publish_date = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, css_selectors[1]))
            ).text
            author = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, css_selectors[2]))
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


class myThread(threading.Thread):
    def __init__(self, site_url):
        threading.Thread.__init__(self)
        self.site_url = site_url
        self.exit_code = 0

    def run(self):
        try:
            self._run()
        except Exception:
            self.exit_code = 1
            threadmax.release()
            f = open("异常url.txt", "a")
            datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            f.write(self.site_url + "\n")
            f.close()
            # raise Exception(str(self.site_url) + "出现异常")

    def _run(self):
        threadmax.acquire()
        # 用于写入数据库的df
        df = crawl_news_Request(self.site_url)
        # 成功爬取后更新对应的site_url的content为1，表示该url已经获取了内容
        rows = df_result.site_url == self.site_url
        df_result.loc[rows, "title"] = df["title"][0]
        df_result.loc[rows, "content"] = df["content"][0]
        # write_s3(self.Media, df["title"], df["content"])
        datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        f = open("成功url.txt", "a")
        f.write(self.site_url + "\n")
        f.close()
        # print(df["title"], df["content"])
        # send_SQS(self.Media, df["title"])
        threadmax.release()


if __name__ == "__main__":
    thread_list = []
    news_links = get_news_links(rss_urls)
    f = open("siteurl.txt", "a")
    for i in news_links:
        f.write(i + "\n")
    f.close()
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
    f = open("异常url.txt", "r")
    failed_urls = f.readlines()
    for i in range(len(failed_urls)):
        failed_urls[i] = failed_urls[i].replace("\n", "")
    f.close()
    # 对于没有爬取到内容的url，再爬取n_repeat次
    n_repeat = 3
    i = 0
    while i < n_repeat:
        i = i + 1
        # 内容为空的网址继续尝试爬取几次
        for site_url in df_result[df_result["content"] == ""]["site_url"]:
            try:
                df = crawl_news_Request(site_url, path="css_selector")
                # df=crawl_news(site_url)
                rows = df_result.site_url == site_url
                df_result.loc[rows, "title"] = df["title"][0]
                df_result.loc[rows, "content"] = df["content"][0]
                now = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                f = open("二次成功url.txt", "a")
                f.write(now + " " + site_url + "\n")
                f.close()
                # print(df["title"][0], df["content"][0])
            except Exception as e:
                f = open("二次异常url.txt", "a")
                now = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                f.write(now + " " + site_url + " error info: " + str(e) + "\n")
                f.close()
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
