import asyncio
from dataclasses import dataclass
import json
import logging
import aiobotocore
from enum import Enum


QUEUE_URL = 'https://sqs.us-west-2.amazonaws.com/396260505786/bolt-worker-prod'


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
    match job.job_type:
        case JobType.SUMMARY:
            return
        case JobType.SUMMARY_TITLE:
            return
        case JobType.TRANSLATE_ARTICLE:
            return
        case _:
            raise ValueError(f"Not supported job type: {job.job_type}")


async def main() -> None:
    session = aiobotocore.get_session()
    async with session.create_client('sqs', region_name='us-west-2') as client:
        while True:
            try:
                response = await client.receive_message(QueueUrl=QUEUE_URL, WaitTimeSeconds=20)
                message: str = response['Messages'][0]
                json_dict = json.loads(message['Body'])
                job = WorkerJob(**json_dict)
                await process_job(job)
                await client.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=message['ReceiptHandle'])
            except Exception as e:
                logging.error(f"SQS Error: {e}")
                continue

            await asyncio.sleep(0.5)

asyncio.run(main())
