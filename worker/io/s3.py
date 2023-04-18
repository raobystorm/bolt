from typing import Any


import aiobotocore


async def get_file_from_s3(file_key: str) -> str:
    session = aiobotocore.get_session()
    async with session.create_client("s3") as client:
        response = await client.get_object(Bucket="bolt-prod", Key=file_key)
        async with response["Body"] as stream:
            file_content = await stream.read()
            return str(file_content)
