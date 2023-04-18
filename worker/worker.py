import asyncio
from dataclasses import dataclass
import json
import logging
import aiobotocore
from enum import Enum

from langcodes import Language
from worker.io.s3 import get_file_from_s3

from worker.llm.llm import summary_article


QUEUE_URL = "https://sqs.us-west-2.amazonaws.com/396260505786/bolt-worker-prod"


class JobType(Enum):
    SUMMARY = "summary"
    SUMMARY_TITLE = "summary_title"
    TRANSLATE_ARTICLE = "translate_article"


@dataclass
class WorkerJob:
    s3_prefix: str
    job_type: JobType = JobType.SUMMARY
    target_lang: str = "zh-CN"


async def process_job(job: WorkerJob) -> None:
    content = await get_file_from_s3(job.s3_prefix + "/article.txt")
    target_lang = Language.get(job.target_lang).display_name()
    match job.job_type:
        case JobType.SUMMARY:
            text = await summary_article(content, target_lang)
        case JobType.SUMMARY_TITLE:
            return  # TODO: Get title await translate_article()
        case JobType.TRANSLATE_ARTICLE:
            return
        case _:
            raise ValueError(f"Not supported job type: {job.job_type}")


async def main() -> None:
    session = aiobotocore.get_session()
    async with session.create_client("sqs", region_name="us-west-2") as client:
        while True:
            try:
                response = await client.receive_message(
                    QueueUrl=QUEUE_URL, WaitTimeSeconds=20
                )
                message: str = response["Messages"][0]
                json_dict = json.loads(message["Body"])
                job = WorkerJob(**json_dict)
                await process_job(job, session)
                await client.delete_message(
                    QueueUrl=QUEUE_URL, ReceiptHandle=message["ReceiptHandle"]
                )
            except Exception as e:
                logging.error(f"SQS Error: {e}")
                continue

            await asyncio.sleep(0.5)


asyncio.run(main())
