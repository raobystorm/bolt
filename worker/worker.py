import argparse
import asyncio
import json
import logging
import os
from dataclasses import dataclass
from enum import StrEnum

from aiobotocore.session import get_session
from langcodes import Language
from sqlalchemy.orm import sessionmaker
from utils import (
    check_file_in_s3,
    get_text_file_from_s3,
    put_text_file_to_s3,
    summarize_article,
    summarize_title,
    translate_article,
    translate_title,
)

from consts import QUEUE_WORKER_URL
from db import UserArticle, UserMedia, get_db_engine


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
        case JobType.GET_IMAGE:
            pass
        case _:
            raise ValueError(f"Not supported job type: {job.job_type}")

    if text != "":
        await put_text_file_to_s3(res_path, text)

    return text != ""


def put_user_articles(media_id: int, article_id: int, lang: str) -> None:
    """完成文章的摘要和翻译后将其推送给已订阅的用户."""
    engine = get_db_engine()
    db_sess = sessionmaker(bind=engine)()
    try:
        user_medias = (
            db_sess.query(UserMedia)
            .filter(UserMedia.media_id == media_id and UserMedia.lang == lang)
            .all()
        )
        user_articles = []
        for user_media in user_medias:
            user_articles.append(
                UserArticle(user_id=user_media.user_id, article_id=article_id)
            )

        db_sess.add_all(user_articles)
        db_sess.commit()
    finally:
        db_sess.close()
        engine.dispose()


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
                        if job.job_type == JobType.GET_IMAGE:
                            continue
                        if await process_job(job, args.use_gpt4):
                            await sqs.delete_message(
                                QueueUrl=QUEUE_WORKER_URL,
                                ReceiptHandle=message["ReceiptHandle"],
                            )
                            if await check_finish(job):
                                logging.info(
                                    f"All jobs of the article {job.article_id} is finished!"
                                )
                                put_user_articles(
                                    job.media_id,
                                    job.article_id,
                                    job.target_lang,
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
