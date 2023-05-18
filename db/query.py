from .db import get_db_engine, media
from sqlalchemy import select


def read_all_media() -> list:
    engine = get_db_engine()
    with engine.connect() as conn:
        result = conn.execute(
            select(
                media.c.id,
                media.c.name,
                media.c.base_url,
                media.c.rss_url,
                media.c.text_selector,
                media.c.title_selector,
                media.c.author_selector,
            )
        )
    return result.fetchall()
