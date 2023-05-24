import logging
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from db import article, get_db_engine_async, media, user_article
from worker.utils.s3 import get_text_file_from_s3

PAGE_LIMIT = 10
THUMBNAIL_PREFIX = "https://bolt-prod-public.s3.us-west-2.amazonaws.com/"

app = FastAPI()
logger = logging.getLogger("uvicorn.error")

origins = ["http://localhost:8080"]

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
    async with engine.connect() as conn:
        offset = PAGE_LIMIT * page
        stmt = (
            select(
                article.c.id, article.c.s3_prefix, article.c.publish_date, media.c.name
            )
            .join(user_article, article.c.id == user_article.c.article_id)
            .join(media, article.c.media_id == media.c.id)
            .filter(user_article.c.user_id == user_id)
            .order_by(article.c.publish_date.desc())
            .offset(offset)
            .limit(PAGE_LIMIT)
        )
        articles = await conn.execute(stmt)

    results: dict[str, list] = {}
    for id, s3_prefix, publish_date, media_name in articles:
        d = datetime.strftime(publish_date, "%Y-%m-%d")
        title = await get_text_file_from_s3(s3_prefix + f"/lang={lang}/title.txt")
        if d not in results:
            results[d] = []
        results[d].append(
            {
                "articleId": id,
                "title": title,
                "thumbnailPath": THUMBNAIL_PREFIX + s3_prefix + "/thumbnail.webp",
                "media": media_name,
            }
        )
    return results


@app.get("/article/{article_id}")
async def get_article(article_id: int, lang: str) -> dict:
    engine = get_db_engine_async()
    async with engine.connect() as conn:
        stmt = (
            select(
                article.c.title,
                article.c.s3_prefix,
                article.c.publish_date,
                media.c.name,
            )
            .join(media, article.c.media_id == media.c.id)
            .filter(article.c.id == article_id)
        )
        query_res = await conn.execute(stmt)

    title, s3_prefix, publish_date, media_name = list(query_res)[0]

    org_text = await get_text_file_from_s3(s3_prefix + "/article.txt")
    trans_title = await get_text_file_from_s3(s3_prefix + f"/lang={lang}/title.txt")
    summary = await get_text_file_from_s3(s3_prefix + f"/lang={lang}/summary.txt")
    trans_text = await get_text_file_from_s3(s3_prefix + f"/lang={lang}/article.txt")

    return {
        "title": title,
        "article": org_text,
        "publish_date": datetime.strftime(publish_date, "%Y-%m-%d"),
        "media": media_name,
        "translate_title": trans_title,
        "summary": summary,
        "translate_article": trans_text,
    }
