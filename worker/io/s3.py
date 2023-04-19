from aiobotocore.session import get_session
from boto3 import S3


BOLT_BUCKET = "bolt-prod"


async def check_file_in_s3(file_key: str) -> bool:
    session = get_session()
    async with session.create_client("s3") as s3:
        try:
            await s3.head_object(Bucket=BOLT_BUCKET, Key=file_key)
        except S3.Client.exceptions.NoSuchKey:
            return False
        else:
            return True


async def put_file_to_s3(file_key: str, data: str) -> None:
    session = get_session()
    async with session.create_client("s3") as s3:
        await s3.put_object(Bucket=BOLT_BUCKET, Key=file_key, body=data)


async def get_file_from_s3(file_key: str) -> str:
    session = get_session()
    async with session.create_client("s3") as s3:
        response = await s3.get_object(Bucket=BOLT_BUCKET, Key=file_key)
        async with response["Body"] as stream:
            file_content = await stream.read()
            return str(file_content)
