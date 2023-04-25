import os

from sqlalchemy import Column, String
from sqlalchemy import MetaData
from sqlalchemy import BigInteger
from sqlalchemy import Table


DB_HOST = os.environ["DB_HOST"]
DB_PASSWORD = os.environ["DB_PASSWORD"]

meta = MetaData()
user_media = Table(
    "user_media",
    meta,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("user_id", BigInteger),
    Column("media_id", BigInteger),
    Column("lang", String(255)),
)

user_article = Table(
    "user_article",
    meta,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("user_id", BigInteger),
    Column("article_id", BigInteger),
)
