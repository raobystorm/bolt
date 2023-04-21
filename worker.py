import asyncio
import json
import logging
import os
from dataclasses import dataclass

from aiobotocore.session import get_session
from langcodes import Language
from ranker.ranker import RankerJob

from worker.io.s3 import get_file_from_s3, put_file_to_s3, check_file_in_s3
from worker.llm.llm import summary_article, translate_article, translate_title

QUEUE_URL = "https://sqs.us-west-2.amazonaws.com/396260505786/bolt-worker-prod"


@dataclass
class WorkerJob:
    media_id: int
    article_id: int
    title: str
    s3_prefix: str
    job_type: str = "summary_article"
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


async def process_job(job: WorkerJob) -> None:
    """根据SQS job的类型进行原文翻译/摘要生成/标题翻译的工作."""
    article_path = os.path.join(job.s3_prefix, "article.txt")
    target_lang = Language.get(job.target_lang).display_name()
    match job.job_type.lower():
        case "summary_article":
            content = await get_file_from_s3(article_path)
            text = await summary_article(content, target_lang)
            res_path = os.path.join(
                job.s3_prefix, f"lang={job.target_lang}", "summary.txt"
            )
        case "translate_title":
            text = await translate_title(title=job.title, lang=job.target_lang)
            res_path = os.path.join(
                job.s3_prefix, f"lang={job.target_lang}", "title.txt"
            )
        case "translate_article":
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
                if "Messages" in response:
                    for message in response["Messages"]:
                        json_dict = json.loads(message["Body"])
                        job = WorkerJob(**json_dict)
                        logging.info(f"process job: {job}")
                        await process_job(job)
                        logging.info(f"delete message: {message}")
                        await sqs.delete_message(
                            QueueUrl=QUEUE_URL, ReceiptHandle=message["ReceiptHandle"]
                        )
                        send_job = RankerJob(
                            media_id=job.media_id,
                            article_id=job.article_id,
                            lang=job.target_lang,
                        )
                        if await check_finish(job):
                            await sqs.send_message(
                                QueueUrl=QUEUE_URL, MessageBody=json.dumps(send_job)
                            )
                else:
                    logging.info("No messages in queue.")
            except Exception as e:
                logging.error(f"{type(e)}: {e}")
                continue
            finally:
                await asyncio.sleep(0.5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
