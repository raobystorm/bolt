import os

from sqlalchemy import DateTime, Column, ForeignKeyConstraint, Index, String
from sqlalchemy import MetaData
from sqlalchemy import BigInteger
from sqlalchemy import Table
from sqlalchemy import func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine


DB_HOST = os.environ["DB_HOST"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
BOLT_DB = "bolt_db"

meta = MetaData()

user = Table(
    "user",
    meta,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("lang", String(255), nullable=False),
    Column("email", String(255), nullable=False),
    Column("created_at", DateTime, default=func.now()),
    Column("updated_at", DateTime, default=func.now(), onupdate=func.now()),
)

media = Table(
    "media",
    meta,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("name", String(255), nullable=False),
    Column("base_url", String(512), nullable=False),
    Column("rss_url", String(512), nullable=True),
    Column("text_selector", String(255), nullable=True),
    Column("title_selector", String(255), nullable=True),
    Column("created_at", DateTime, default=func.now()),
    Column("updated_at", DateTime, default=func.now(), onupdate=func.now()),
)

article = Table(
    "article",
    meta,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("media_id", BigInteger, nullable=False),
    Column("category_id", BigInteger, nullable=False),
    Column("title", String(512), nullable=False),
    Column("author", String(255), nullable=True),
    Column("link_url", String(1024), nullable=False),
    Column("s3_key", String(1024), nullable=False),
    Column("publish_date", DateTime, nullable=True),
    Column("thumbnail_path", String(1024), nullable=True),
    ForeignKeyConstraint(["media_id"], ["media.id"], ondelete="CASCADE"),
    ForeignKeyConstraint(["category_id"], ["category.id"], ondelete="CASCADE"),
    Column("created_at", DateTime, default=func.now()),
    Column("updated_at", DateTime, default=func.now(), onupdate=func.now()),
)

category = Table(
    "category",
    meta,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("name", String(255), nullable=False),
    Column("created_at", DateTime, default=func.now()),
    Column("updated_at", DateTime, default=func.now(), onupdate=func.now()),
)

user_media = Table(
    "user_media",
    meta,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("user_id", BigInteger, nullable=False),
    Column("media_id", BigInteger, nullable=False),
    Column("lang", String(255), nullable=False),
    Column("created_at", DateTime, default=func.now()),
    Column("updated_at", DateTime, default=func.now(), onupdate=func.now()),
    ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
    ForeignKeyConstraint(["media_id"], ["media.id"], ondelete="CASCADE"),
    Index("user_media_index", "media_id", "lang", unique=True),
)

user_article = Table(
    "user_article",
    meta,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("user_id", BigInteger, nullable=False),
    Column("article_id", BigInteger, nullable=False),
    Column("created_at", DateTime, default=func.now()),
    Column("updated_at", DateTime, default=func.now(), onupdate=func.now()),
    ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
    ForeignKeyConstraint(["article_id"], ["article.id"], ondelete="CASCADE"),
    Index("user_article_index", "user_id", unique=True),
)


def get_db_engine() -> AsyncEngine:
    return create_async_engine(
        f"mysql+aiomysql://admin:{DB_PASSWORD}@{DB_HOST}/bolt_db", echo=True
    )
