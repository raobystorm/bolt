import csv

from sqlalchemy.orm import sessionmaker

from db.db import Base, Media, get_db_engine


def init_db_tables() -> None:
    engine = get_db_engine()
    sessionmaker(bind=engine)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def insert_media_list() -> None:
    engine = get_db_engine()
    session = sessionmaker(bind=engine)()
    with open("db/row.csv", "r") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            data = Media(
                name=row[0],
                base_url=row[1],
                rss_url=row[2],
                xpath_title=row[3],
                xpath_publish_date=row[4],
                xpath_author=row[5],
                xpath_image_url=row[6],
                xpath_content=row[7],
                selector_title=row[8],
                selector_publish_date=row[9],
                selector_author=row[10],
                selector_image_url=row[11],
                selector_content=row[12],
            )
            session.add(data)

    session.commit()
