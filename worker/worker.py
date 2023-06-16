import argparse
import asyncio
import io
import json
import logging
import os
import traceback
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse

import aiohttp
from aiobotocore.session import get_session
from langcodes import Language
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from consts import BOLT_PUBLIC_BUCKET, QUEUE_WORKER_URL
from db import ArticleTranslation, UserArticle, UserMedia, get_db_engine_async
from utils import (
    check_file_in_s3,
    get_text_file_from_s3,
    put_text_file_to_s3,
    summarize_article,
    summarize_title,
    translate_article,
    translate_title,
)


class JobType(StrEnum):
    SUMMARIZE_ARTICLE = "summarize_article"
    TRANSLATE_TITLE = "translate_title"
    TRANSLATE_ARTICLE = "translate_article"
    SUMMARIZE_TITLE = "summarize_title"
    GET_IMAGE = "get_image"


@dataclass
class WorkerJob:
    media_id: int
    article_id: int
    title: str
    s3_prefix: str
    job_type: JobType = JobType.SUMMARIZE_ARTICLE
    image_link: str = ""
    target_lang: str = "zh-CN"


async def check_finish(job: WorkerJob) -> bool:
    """检查文章的翻译是否完成（原文翻译，摘要生成，标题翻译）."""
    trans_summary_path = os.path.join(
        job.s3_prefix, f"lang={job.target_lang}", "summary.txt"
    )
    trans_title_path = os.path.join(
        job.s3_prefix, f"lang={job.target_lang}", "title.txt"
    )
    trans_article_path = os.path.join(
        job.s3_prefix, f"lang={job.target_lang}", "article.txt"
    )
    return (
        await check_file_in_s3(trans_summary_path)
        and await check_file_in_s3(trans_title_path)
        and await check_file_in_s3(trans_article_path)
    )


async def download_image(job: WorkerJob) -> None:
    parsed_url = urlparse(job.image_link)
    if not parsed_url.path.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp")):
        return

    async with aiohttp.ClientSession() as sess:
        async with sess.get(url=parsed_url.geturl()) as resp:
            if resp.status == 200:
                image_content = await resp.read()
            else:
                logging.error(f"Status code: {resp.status}, url: {parsed_url.geturl()}")

    file_key = os.path.join(job.s3_prefix, "thumbnail.webp")
    async with get_session().create_client("s3") as s3:
        with Image.open(io.BytesIO(image_content)) as im:
            output_bytes = io.BytesIO()
            im.save(output_bytes, "webp")

        await s3.put_object(
            Body=output_bytes.getvalue(), Bucket=BOLT_PUBLIC_BUCKET, Key=file_key
        )


async def process_job(job: WorkerJob, use_gpt4: bool) -> bool:
    """根据SQS job的类型进行原文翻译/摘要生成/标题翻译的工作."""
    article_path = os.path.join(job.s3_prefix, "article.txt")
    target_lang = Language.get(job.target_lang).display_name()
    match job.job_type:
        case JobType.SUMMARIZE_ARTICLE:
            content = await get_text_file_from_s3(article_path)
            text = await summarize_article(content, target_lang, use_gpt4=use_gpt4)
            res_path = os.path.join(
                job.s3_prefix, f"lang={job.target_lang}", "summary.txt"
            )
        case JobType.TRANSLATE_TITLE:
            text = await translate_title(title=job.title, lang=job.target_lang)
            text = text.replace(",", "").replace(".", "").replace(";", "")
            res_path = os.path.join(
                job.s3_prefix, f"lang={job.target_lang}", "title.txt"
            )
        case JobType.TRANSLATE_ARTICLE:
            content = await get_text_file_from_s3(article_path)
            text = await translate_article(content, job.target_lang, use_gpt4=use_gpt4)
            res_path = os.path.join(
                job.s3_prefix, f"lang={job.target_lang}", "article.txt"
            )
        case JobType.SUMMARIZE_TITLE:
            content = await get_text_file_from_s3(article_path)
            text = await summarize_title(content, job.target_lang, use_gpt4=use_gpt4)
            text = text.replace(",", "").replace(".", "").replace(";", "")
            res_path = os.path.join(
                job.s3_prefix, f"lang={job.target_lang}", "title.txt"
            )
        case JobType.GET_IMAGE:
            await download_image(job)
            return True
        case _:
            raise ValueError(f"Not supported job type: {job.job_type}")

    if text != "":
        await put_text_file_to_s3(res_path, text)

    return text != ""


async def put_article_translation(job: WorkerJob) -> None:
    engine = get_db_engine_async()
    try:
        title_path = os.path.join(job.s3_prefix, f"lang={job.target_lang}", "title.txt")
        title = await get_text_file_from_s3(title_path)
        summary_path = os.path.join(
            job.s3_prefix, f"lang={job.target_lang}", "summary.txt"
        )
        summary = await get_text_file_from_s3(summary_path)
        async with async_sessionmaker(engine).begin() as db_sess:
            article_translation = ArticleTranslation(
                article_id=job.article_id,
                lang=job.target_lang,
                title=title,
                summary=summary,
            )
            db_sess.add(article_translation)
    except Exception:
        print(traceback.format_exc())
    finally:
        await engine.dispose()


async def put_user_articles(job: WorkerJob) -> None:
    """完成文章的摘要和翻译后将其推送给已订阅的用户."""
    engine = get_db_engine_async()
    try:
        async with async_sessionmaker(engine).begin() as db_sess:
            stmt = select(UserMedia.user_id).where(
                UserMedia.media_id == job.media_id and UserMedia.lang == job.target_lang
            )
            user_ids = await db_sess.execute(stmt)
            user_articles = []
            for user_id in user_ids:
                user_articles.append(
                    UserArticle(user_id=user_id[0], article_id=job.article_id)
                )

            db_sess.add_all(user_articles)
    except Exception:
        print(traceback.format_exc())
    finally:
        await engine.dispose()


async def main(args: argparse.Namespace) -> None:
    aio_sess = get_session()
    async with aio_sess.create_client("sqs", region_name="us-west-2") as sqs:
        while True:
            try:
                response = await sqs.receive_message(
                    QueueUrl=QUEUE_WORKER_URL, WaitTimeSeconds=20
                )
                if "Messages" in response:
                    for message in response["Messages"]:
                        json_dict = json.loads(message["Body"])
                        job = WorkerJob(**json_dict)
                        logging.info(f"process job: {job}")
                        if await process_job(job, args.use_gpt4):
                            await sqs.delete_message(
                                QueueUrl=QUEUE_WORKER_URL,
                                ReceiptHandle=message["ReceiptHandle"],
                            )
                            if await check_finish(job):
                                logging.info(
                                    f"All jobs of the article {job.article_id} is finished!"
                                )
                                await put_article_translation(job)
                                await put_user_articles(job)
                else:
                    logging.info("No messages in queue.")
            except Exception:
                logging.error(traceback.format_exc())
                continue
            finally:
                await asyncio.sleep(0.5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--use-gpt4", type=bool, default=False)
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main(parser.parse_args()))
