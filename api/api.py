import logging
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from db import Article, ArticleTranslation, Media, UserArticle, get_db_engine_async
from utils import get_text_file_from_s3

PAGE_LIMIT = 10
THUMBNAIL_PREFIX = "https://bolt-prod-public.s3.us-west-2.amazonaws.com/"

app = FastAPI()
logger = logging.getLogger("uvicorn.error")

origins = ["http://bolt_web"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/timeline/{user_id}")
async def fetch_articles(user_id: int, page: int, lang: str) -> dict:
    engine = get_db_engine_async()
    try:
        async with sessionmaker(engine, class_=AsyncSession)() as db_sess:
            offset = PAGE_LIMIT * page
            stmt = (
                select(
                    Article.id,
                    Article.s3_prefix,
                    ArticleTranslation.title,
                    ArticleTranslation.summary,
                    Article.publish_date,
                    Media.name,
                )
                .join(UserArticle, Article.id == UserArticle.article_id)
                .join(Media, Article.media_id == Media.id)
                .join(
                    ArticleTranslation,
                    ArticleTranslation.article_id == UserArticle.article_id
                    and UserArticle.lang == lang,
                )
                .filter(UserArticle.user_id == user_id)
                .order_by(Article.publish_date.desc())
                .offset(offset)
                .limit(PAGE_LIMIT)
            )
            articles = (await db_sess.execute(stmt)).all()

        results: list = []
        for id, s3_prefix, title, summary, publish_date, media_name in articles:
            d = datetime.strftime(publish_date, "%Y-%m-%d %H:%M")
            results.append(
                {
                    "articleId": id,
                    "title": title,
                    "publishDate": d,
                    "summary": summary,
                    "thumbnailPath": THUMBNAIL_PREFIX + s3_prefix + "/thumbnail.webp",
                    "media": media_name,
                }
            )
        return {"articles": results}
    finally:
        await engine.dispose()


@app.get("/article/{article_id}")
async def get_article(article_id: int, lang: str) -> dict:
    engine = get_db_engine_async()
    try:
        async with sessionmaker(engine, class_=AsyncSession)() as db_sess:
            stmt = (
                select(
                    Article.title,
                    Article.s3_prefix,
                    Article.publish_date,
                    Article.link_url,
                    ArticleTranslation.title,
                    ArticleTranslation.summary,
                    Media.name,
                )
                .join(Media, Article.media_id == Media.id)
                .join(
                    ArticleTranslation,
                    ArticleTranslation.article_id == article_id
                    and ArticleTranslation.lang == lang,
                )
                .filter(Article.id == article_id)
            )
            query_res = (await db_sess.execute(stmt)).one()

        (
            title,
            s3_prefix,
            publish_date,
            link_url,
            trans_title,
            summary,
            media_name,
        ) = query_res

        trans_text = await get_text_file_from_s3(
            s3_prefix + f"/lang={lang}/article.txt"
        )
        if summary is None or len(summary) == 0:
            summary = await get_text_file_from_s3(
                s3_prefix + f"/lang={lang}/summary.txt"
            )

        return {
            "title": title,
            "publish_date": datetime.strftime(publish_date, "%Y-%m-%d %H:%M"),
            "link_url": link_url,
            "media": media_name,
            "translate_title": trans_title,
            "summary": summary,
            "translate_article": trans_text,
        }
    finally:
        await engine.dispose()
