import asyncio
import argparse
from enum import StrEnum
import json
import logging
import os
from dataclasses import dataclass

from aiobotocore.session import get_session
from langcodes import Language
from consts import QUEUE_WORKER_URL
from db import get_db_engine_async, user_media, user_article
from sqlalchemy import select


from utils import (
    summarize_article,
    summarize_title,
    translate_article,
    translate_title,
    get_text_file_from_s3,
    put_text_file_to_s3,
    check_file_in_s3,
)


class JobType(StrEnum):
    SUMMARIZE_ARTICLE = "summarize_article"
    TRANSLATE_TITLE = "translate_title"
    TRANSLATE_ARTICLE = "translate_article"
    SUMMARIZE_TITLE = "summarize_title"


@dataclass
class WorkerJob:
    media_id: int
    article_id: int
    title: str
    s3_prefix: str
    job_type: JobType = JobType.SUMMARIZE_ARTICLE
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


async def process_job(job: WorkerJob, use_gpt4: bool) -> None:
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
            res_path = os.path.join(
                job.s3_prefix, f"lang={job.target_lang}", "title.txt"
            )
        case _:
            raise ValueError(f"Not supported job type: {job.job_type}")

    await put_text_file_to_s3(res_path, text)


async def put_user_articles(media_id: int, article_id: int, lang: str) -> None:
    """完成文章的摘要和翻译后将其推送给已订阅的用户."""
    engine = get_db_engine_async()
    async with engine.begin() as conn:
        result = await conn.execute(
            select(user_media.c.user_id).where(
                user_media.c.media_id == media_id and user_media.c.lang == lang
            )
        )
        user_ids = list(result.fetchall())
        insert_data = [
            {"user_id": user_id[0], "article_id": article_id} for user_id in user_ids
        ]
        await conn.execute(user_article.insert(), insert_data)

    await engine.dispose()


async def main(args: argparse.Namespace) -> None:
    session = get_session()
    async with session.create_client("sqs", region_name="us-west-2") as sqs:
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
                        await process_job(job, args.use_gpt4)
                        await sqs.delete_message(
                            QueueUrl=QUEUE_WORKER_URL,
                            ReceiptHandle=message["ReceiptHandle"],
                        )
                        if await check_finish(job):
                            logging.info(
                                f"All jobs of the article {job.article_id} is finished!"
                            )
                            await put_user_articles(
                                job.media_id, job.article_id, job.target_lang
                            )
                else:
                    logging.info("No messages in queue.")
            except Exception as e:
                logging.error(f"{type(e)}: {e}")
                continue
            finally:
                await asyncio.sleep(0.5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--use-gpt4", type=bool, default=False)
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main(parser.parse_args()))
