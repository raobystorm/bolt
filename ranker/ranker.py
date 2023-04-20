import asyncio
from dataclasses import dataclass
import json
import logging
import os
from typing import Any
from aiobotocore import get_session
from sqlalchemy import Column, String
from sqlalchemy import MetaData
from sqlalchemy import select, insert
from sqlalchemy import BigInteger
from sqlalchemy import Table
from sqlalchemy.ext.asyncio import create_async_engine


QUEUE_URL = "https://sqs.us-west-2.amazonaws.com/396260505786/bolt-ranker-prod"

DB_HOST = "bolt-db.c3s9aj87pxhh.us-west-2.rds.amazonaws.com"
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


@dataclass
class RankerJob:
    media_id: int
    article_id: int
    lang: str


async def process_job(engine: Any, job: RankerJob) -> None:
    async with engine.connect() as conn:
        result = await conn.execute(
            select(user_media.c.user_id).where(
                user_media.c.media_id == job.media_id and user_media.c.lang == job.lang
            )
        )
        user_ids = list(result.fetchall())
        insert_data = [
            {"user_id": user_id, "article_id": job.article_id} for user_id in user_ids
        ]
        await conn.execute(user_article.insert(), insert_data)


async def main() -> None:
    session = get_session()
    async with session.create_client("sqs", region_name="us-west-2") as sqs:
        engine = create_async_engine(
            f"mysql+aiomysql://admin:{DB_PASSWORD}@{DB_HOST}/bolt-db", echo=True
        )
        while True:
            try:
                response = await sqs.receive_message(
                    QueueUrl=QUEUE_URL, WaitTimeSeconds=20
                )
                message: dict = response["Messages"][0]
                json_dict = json.loads(message["Body"])
                job = RankerJob(**json_dict)
                await process_job(engine, job)
            except Exception as e:
                logging.error(f"SQS Error: {e}")
                continue

            await asyncio.sleep(0.5)


asyncio.run(main())
