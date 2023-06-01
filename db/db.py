import os

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    PrimaryKeyConstraint,
    String,
    create_engine,
    func,
)
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

DB_HOST = os.environ["DB_HOST"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_URL_ASYNC = f"mysql+aiomysql://admin:{DB_PASSWORD}@{DB_HOST}/bolt_db"
DB_URL = f"mysql+mysqlconnector://admin:{DB_PASSWORD}@{DB_HOST}/bolt_db"
BOLT_DB = "bolt_db"


Base = declarative_base()


class User(Base):
    __tablename__ = "user"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    lang = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Media(Base):
    __tablename__ = "media"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    base_url = Column(String(512), nullable=False)
    rss_url = Column(String(512), nullable=False)
    xpath_title = Column(String(1024), nullable=False)
    xpath_publish_date = Column(String(1024), nullable=False)
    xpath_author = Column(String(1024), nullable=False)
    xpath_image_url = Column(String(1024), nullable=False)
    xpath_content = Column(String(1024), nullable=False)
    selector_title = Column(String(1024), nullable=False)
    selector_publish_date = Column(String(1024), nullable=False)
    selector_author = Column(String(1024), nullable=False)
    selector_image_url = Column(String(1024), nullable=False)
    selector_content = Column(String(1024), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Article(Base):
    __tablename__ = "article"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    media_id = Column(
        BigInteger, ForeignKey("media.id", ondelete="CASCADE"), nullable=False
    )
    category_id = Column(
        BigInteger, ForeignKey("category.id", ondelete="CASCADE"), nullable=True
    )
    title = Column(String(512), nullable=False)
    author = Column(String(255), nullable=False)
    link_url = Column(String(1024), nullable=False)
    s3_prefix = Column(String(1024), nullable=False)
    image_link = Column(String(1024), nullable=False)
    publish_date = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationship definition
    media = relationship("Media", backref="articles")


class Category(Base):
    __tablename__ = "category"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class UserMedia(Base):
    __tablename__ = "user_media"

    user_id = Column(
        BigInteger,
        ForeignKey("user.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    media_id = Column(
        BigInteger,
        ForeignKey("media.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    lang = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", backref="user_medias")
    media = relationship("Media", backref="user_medias")

    __table_args__ = (PrimaryKeyConstraint("user_id", "media_id"), {})


class UserArticle(Base):
    __tablename__ = "user_article"

    user_id = Column(
        BigInteger,
        ForeignKey("user.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    article_id = Column(
        BigInteger,
        ForeignKey("article.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", backref="user_articles")
    article = relationship("Article", backref="user_articles")

    __table_args__ = (PrimaryKeyConstraint("user_id", "article_id"), {})


def get_db_engine_async() -> AsyncEngine:
    return create_async_engine(DB_URL_ASYNC, echo=True)


def get_db_engine() -> Engine:
    return create_engine(DB_URL, echo=True)
