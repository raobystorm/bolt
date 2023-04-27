from db.db import BOLT_DB, get_db_engine, user_media, media, meta
import asyncio
from sqlalchemy import text


async def init_db_tables() -> None:
    engine = get_db_engine()
    async with engine.connect() as conn:
        await conn.execute(
            text(
                f"DROP DATABASE IF EXISTS {BOLT_DB}; CREATE DATABASE {BOLT_DB}; USE {BOLT_DB};"
            )
        )
        await conn.run_sync(meta.create_all)


async def inser_test_data() -> None:
    engine = get_db_engine()
    media.drop()
    async with engine.connect() as conn:
        await conn.execute(media.insert(), [{"name": "NewsWeek", "base_url": ""}])
        await conn.execute(user_media.insert(), [{}])


if __name__ == "__main__":
    asyncio.run(inser_test_data())
