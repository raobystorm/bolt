import asyncio
import json
import logging
import os
from dataclasses import dataclass
from enum import Enum

from aiobotocore.session import get_session
from langcodes import Language
from ranker.ranker import RankerJob

from worker.io.s3 import check_file_in_s3, get_file_from_s3, put_file_to_s3
from worker.llm.llm import summary_article, translate_article, translate_title

QUEUE_URL = "https://sqs.us-west-2.amazonaws.com/396260505786/bolt-worker-prod"


class JobType(Enum):
    SUMMARY = "summary"
    SUMMARY_TITLE = "summary_title"
    TRANSLATE_ARTICLE = "translate_article"


@dataclass
class WorkerJob:
    media_id: int
    article_id: int
    title: str
    s3_prefix: str
    job_type: JobType = JobType.SUMMARY
    target_lang: str = "zh-CN"


async def check_finish(job: WorkerJob) -> bool:
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


async def process_job(job: WorkerJob) -> None:
    article_path = os.path.join(job.s3_prefix, "article.txt")
    target_lang = Language.get(job.target_lang).display_name()
    match job.job_type:
        case JobType.SUMMARY:
            content = await get_file_from_s3(article_path)
            text = await summary_article(content, target_lang)
            res_path = os.path.join(
                job.s3_prefix, f"lang={job.target_lang}", "summary.txt"
            )
        case JobType.SUMMARY_TITLE:
            text = await translate_title(title=job.title, lang=job.target_lang)
            res_path = os.path.join(
                job.s3_prefix, f"lang={job.target_lang}", "title.txt"
            )
        case JobType.TRANSLATE_ARTICLE:
            content = await get_file_from_s3(article_path)
            text = await translate_article(content, job.target_lang)
            res_path = os.path.join(
                job.s3_prefix, f"lang={job.target_lang}", "article.txt"
            )
        case _:
            raise ValueError(f"Not supported job type: {job.job_type}")

    await put_file_to_s3(res_path, text)


async def main() -> None:
    session = get_session()
    async with session.create_client("sqs", region_name="us-west-2") as sqs:
        while True:
            try:
                response = await sqs.receive_message(
                    QueueUrl=QUEUE_URL, WaitTimeSeconds=20
                )
                message: str = response["Messages"][0]
                json_dict = json.loads(message["Body"])
                job = WorkerJob(**json_dict)
                await process_job(job)
                await sqs.delete_message(
                    QueueUrl=QUEUE_URL, ReceiptHandle=message["ReceiptHandle"]
                )
                send_job = RankerJob(media_id=job.media_id, article_id=job.article_id)
                if await check_finish(job):
                    await sqs.send_message(
                        QueueUrl=QUEUE_URL, MessageBody=json.dumps(send_job)
                    )
            except Exception as e:
                logging.error(f"SQS Error: {e}")
                continue

            await asyncio.sleep(0.5)


asyncio.run(main())
