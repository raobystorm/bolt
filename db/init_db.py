from db.db import (
    get_db_engine,
    user_media,
    user_article,
    user,
    article,
    media,
    meta_data,
)


def init_db_tables() -> None:
    engine = get_db_engine()
    with engine.connect() as conn:
        meta_data.drop_all(conn)
        meta_data.create_all(conn)


def inser_test_data() -> None:
    engine = get_db_engine()
    with engine.connect() as conn:
        conn.execute(
            media.insert().values(
                name="NewsWeek", base_url="https://www.newsweek.com/"
            ),
        )
        conn.execute(
            article.insert().values(
                media_id=1,
                title="A Retirement Uprising Could Be on the Cards",
                link_url="https://www.newsweek.com/retirement-pension-reform-france-social-security-1794441",
                s3_prefix="Articles/media=NewsWeek/Year=2023/Month=04/Day=16/Hour=23/A_Retirement_Uprising_Could_Be_on_the_Cards",
            )
        )
        conn.execute(
            user.insert().values(
                lang="zh-CN",
                email="raobystorm@gmail.com",
            )
        )
        conn.execute(user_media.insert().values(user_id=1, media_id=1, lang="zh-CN"))
        conn.execute(user_article.insert().values(user_id=1, article_id=1))
