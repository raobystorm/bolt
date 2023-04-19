import asyncio
from dataclasses import dataclass
import json
import logging
from aiobotocore import get_session


QUEUE_URL = "https://sqs.us-west-2.amazonaws.com/396260505786/bolt-ranker-prod"


@dataclass
class RankerJob:
    media_id: int
    article_id: int


async def process_job(job: RankerJob) -> None:
    ...


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
                job = RankerJob(**json_dict)
                await process_job(job)
            except Exception as e:
                logging.error(f"SQS Error: {e}")
                continue

            await asyncio.sleep(0.5)


asyncio.run(main())
