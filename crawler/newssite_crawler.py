# import newspaper
# import newspaper
import datetime
import threading
import time

#import boto3
import pandas as pd
import requests
from bs4 import BeautifulSoup

# 全局配置，包含线程数，爬虫重试次数等
threadmax = threading.BoundedSemaphore(3)
requests.adapters.DEFAULT_RETRIES = 3
#告警关闭
import warnings

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

warnings.filterwarnings("ignore")


# 函数功能：将爬取的信息写入aws的s3
def write_s3(media, title, content):
    # 获取当前时间，用于创建日期目录
    now = datetime.datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    day = now.strftime("%d")
    hour = now.strftime("%H")
    write_dir = (
        f"Articles/media={media}/Year={year}/Month={month}/Day={day}/Hour={hour}/"
    )
    # 把爬取的内容写成一个文件，文件名为新闻来源加时间戳，内容为新闻标题和新闻正文
    session = boto3.Session(profile_name="bolt")
    s3 = session.resource("s3")
    object = s3.Object("bolt-prod", write_dir + "/article.txt")
    object.put(Body=title + "\n" + content)
    return write_dir


# 函数功能：将爬取的信息写入消息队列
def send_SQS(media_id, title, s3_prefix, job_type="summary", target_lang="zh-CN"):
    return


# 函数功能：实现httpRequest功能
# 函数返回：返回html代码
def httpRequest(url):
    try:
        session = requests.Session()
        retry = Retry(connect=3, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        response = session.get(url, headers=headers, verify=False, timeout=30)
        if response.status_code == 200:
            return response
    except:
        return ""


# 函数功能：爬取newsweek网站
def crawl_newsweek(site_url, selector_path, title_list):
    response = httpRequest(site_url)
    if response == "":
        return
    html = response.text
    bs = BeautifulSoup(html, "html.parser")
    ele = bs.select(selector_path)[0]
    # print(ele)
    # 获取link_url
    link_url = "https://www.newsweek.com/" + ele.select("a")[0].attrs["href"]
    # 获取text_path（指写入s3路径）
    text_path = ""
    response = httpRequest(link_url)
    if response == "":
        return
    html = response.text
    bs = BeautifulSoup(html, "html.parser")

    # 获取title并查重
    title = bs.select("[class*=title]")[0].text
    # 进行title查重，查找title列表里是否有该标题，如果没有再进行抓取
    if title not in title_list:
        title_list.append(title)
    else:
        return
    # 获取publish_date
    publish_date = bs.select("time")[0].attrs["datetime"]
    # 获取author
    author = bs.select(".author")[0].text
    # 获取image_path
    image_path = bs.select(".article-body img")[0].attrs["src"]
    # 获取content
    # write_dir = write_dir + title.replace(" ", "_")
    # 新闻周刊正文分布在多个段落P中，需要获取每一个段落的文字
    content = ""
    length = len(bs.select(".article-body")[0].find_all("p"))
    for i in range(0, length):
        content += bs.select(".article-body")[0].find_all("p")[i].text
    df = pd.DataFrame(
        {
            "title": [title],
            "content": [content],
            "link_url": [link_url],
            "text_path": [text_path],
            "publish_date": [publish_date],
            "author": [author],
            "image_path": [image_path],
        }
    )
    return df


def crawl_times(site_url, selector_path, title_list):
    return


# 函数功能：爬取nytimes网站
def crawl_nytimes(site_url, selector_path, title_list):
    response = httpRequest(site_url)
    if response == "":
        return
    html = response.text
    bs = BeautifulSoup(html, "html.parser")
    ele = bs.select(selector_path)[0]
    # 获取link_url
    link_url = ele.select("a")[0].attrs["href"]
    if link_url.__contains__("http") is False:
        link_url = "https://www.nytimes.com" + link_url
    # 获取text_path（指写入s3路径）
    text_path = ""
    # 获取title并查重
    response = httpRequest(link_url)
    if response == "":
        return
    html = response.text
    bs = BeautifulSoup(html, "html.parser")
    title = bs.select("[id*=link-]")[0].text
    # 进行title查重，查找title列表里是否有该标题，如果没有再进行抓取
    if title not in title_list:
        title_list.append(title)
    else:
        return
    # 获取publish_date
    publish_date = bs.select("time")[0].attrs["datetime"]
    # 获取author
    author = bs.select(".e1jsehar0")[0].text
    # 获取image_path
    image_path = bs.select("img")[0].attrs["src"]
    # 获取content
    # write_dir = write_dir + title.replace(" ", "_")
    # 新闻周刊正文分布在多个段落P中，需要获取每一个段落的文字
    content = ""
    length = len(bs.select(".meteredContent")[0].find_all("p"))
    for i in range(0, length):
        content += bs.select(".meteredContent")[0].find_all("p")[i].text
    df = pd.DataFrame(
        {
            "title": [title],
            "content": [content],
            "link_url": [link_url],
            "text_path": [text_path],
            "publish_date": [publish_date],
            "author": [author],
            "image_path": [image_path],
        }
    )
    return df


def get_news_info(media, site_url, selector_path, title_list):
    # 用于记录爬虫返回的结果
    if media == "NewsWeek":
        df = crawl_newsweek(site_url, selector_path, title_list)
        return df
    elif media == "nytimes":
        df = crawl_nytimes(site_url, selector_path, title_list)
        return df
    else:
        return


class myThread(threading.Thread):
    def __init__(self, Media, site_url, selector_path, title_list):
        threading.Thread.__init__(self)
        self.Media = Media
        self.site_url = site_url
        self.selector_path = selector_path
        self.title_list = title_list
        self.exit_code = 0

    def run(self):
        try:
            self._run()
        except Exception as e:
            self.exit_code = 1
            threadmax.release()
            f = open("异常url.txt", "a")
            now = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            f.write(now + " " + self.site_url + "出现异常"+"异常提示："+str(e)+"\n")
            f.close()
            raise Exception(str(self.site_url) + "出现异常")

    def _run(self):
        threadmax.acquire()
        df=get_news_info(self.Media, self.site_url, self.selector_path, self.title_list)
        #write_s3(self.Media, df["title"], df["content"])
        now = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        f = open("成功url.txt", "a")
        f.write(now + " " + self.site_url + "\n")
        f.close()
        print(self.Media, df["title"], df["content"])
        # send_SQS(self.Media, df["title"])
        threadmax.release()


proxies = {
    "http": "127.0.0.1:7890",
    "https": "127.0.0.1:7890"
}

headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
}

if __name__ == "__main__":
    # 记录已经获取的所有渠道的新闻标题，每个月情空一次
    title_list = []
    if time.strftime("%d") == "16":
        # 每个月初清空列表
        title_list.clear()
    # 记录系统中维护的媒体列表
    # media_list = ["NewsWeek","Times","BusinessWeek"]
    # media_list = ["NewsWeek"]
    # 以下代码查询db中每一个media的site_url和selector_path，查询结果crawler_info形式如{media1:{url1:selector_path1,url2:selector_path2……},url2:{url3:selector_path3,url4:selector_path4……}}
    # db写好之前直接使用crawler_info
    crawler_info = {
        "NewsWeek": {
            "https://www.newsweek.com": ".img-pr",
            "https://www.newsweek.com/world": ".row",
            "https://www.newsweek.com/tech-science": ".row",
            "https://www.newsweek.com/autos": ".row",
            "https://www.newsweek.com/education": ".row",
        },
        "nytimes": {
            "https://www.nytimes.com/": "#site-content",
            "https://www.nytimes.com/international/section/us": "article",
        },
    }
    # execute only if run as a script
    thread_list = []
    df = pd.DataFrame()
    # print(crawler_info_new[0][0])
    while(True):
        for media in crawler_info.keys():
            for site_url in crawler_info[media].keys():
                # 以下为单线程版本
                # df = pd.concat(
                #     [
                #         df,
                #         get_news_info(
                #             media, site_url, crawler_info[media][site_url], title_list
                #         ),
                #     ]
                # )
                # 以下5行为多线程版本
                thread = myThread(
                    media, site_url, crawler_info[media][site_url], title_list
                )
                thread.start()
                thread_list.append(thread)

        for t in thread_list:
            t.join()
            
        #每半小时爬取一次
        time.sleep(500)
