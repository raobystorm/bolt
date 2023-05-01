from aiobotocore.session import get_session
from consts import BOLT_BUCKET


async def check_file_in_s3(file_key: str) -> bool:
    session = get_session()
    async with session.create_client("s3") as s3:
        try:
            await s3.head_object(Bucket=BOLT_BUCKET, Key=file_key)
        except s3.exceptions.ClientError:
            return False
        else:
            return True


async def put_text_file_to_s3(file_key: str, data: str) -> None:
    session = get_session()
    async with session.create_client("s3") as s3:
        await s3.put_object(Bucket=BOLT_BUCKET, Key=file_key, Body=data)


async def get_text_file_from_s3(file_key: str) -> str:
    session = get_session()
    async with session.create_client("s3") as s3:
        response = await s3.get_object(Bucket=BOLT_BUCKET, Key=file_key)
        async with response["Body"] as stream:
            file_content = await stream.read()
            return file_content.decode("utf-8")
