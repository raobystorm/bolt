#import newspaper
import pandas as pd
import numpy as np
import re
import os

import time,datetime

import requests, pickle, zipfile, io
from bs4 import BeautifulSoup

import boto3

proxies = {
   'http': '127.0.0.1:7890',
   'https': '127.0.0.1:7890',
}

headers = {
    "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
}

#获取当前时间，用于创建日期目录
now=datetime.datetime.now()
year=now.strftime("%y")
month=now.strftime("%m")
day=now.strftime("%d")
hour=now.strftime("%H")
write_dir="Bucket/Articles/"+year+"/"+month+"/"+day+"/"+hour+"/"

#记录已经获取的所有渠道的新闻标题，每个月情空一次
title_list=[]
if(time.strftime("%d")=='16'):
    #每个月初清空列表
    title_list.clear()
    
#获取新闻周刊头版页面
craspurl="https://www.newsweek.com/"
response = requests.get(craspurl,headers=headers)
#response = requests.get(craspurl)
html=response.text
bs=BeautifulSoup(html,"html.parser")
ele=bs.select(".img-pr")[0]

#获取新闻周刊头版页面对应新闻标题和内容
first_url="https://www.newsweek.com"+ele.select("a")[0].attrs['href']
craspurl=first_url

response = requests.get(craspurl,headers=headers)
html=response.text
bs=BeautifulSoup(html,"html.parser")
title=bs.select("h1[class*=title]")[0].text

write_dir=write_dir+title.replace(" ","_")
#os.makedirs(base_dir)
#进行title查重，查找title列表里是否有该标题，如果没有再进行抓取
if (title not in title_list):
    title_list.append(title)
    #新闻周刊正文分布在多个段落P中，需要获取每一个段落的文字
    content=""
    length=len(bs.select(".article-body")[0].find_all("p"))
    for i in range(0,length):
        content+=bs.select(".article-body")[0].find_all("p")[i].text
        
    #把爬取的内容写成一个文件，文件名为新闻来源加时间戳，内容为新闻标题和新闻正文
    s3 = boto3.resource('s3')
    object = s3.Object('bolt-prod', write_dir+'article.txt')
    object.put(Body=content)
    #f = open(base_dir+"/"+"article.txt", "w",encoding='utf-8')
    #f.write(title+"\n"+content)
    #f.close()
    
