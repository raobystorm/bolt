from sqlalchemy.orm import sessionmaker

from db.db import Base, get_db_engine


def init_db_tables() -> None:
    engine = get_db_engine()
    sessionmaker(bind=engine)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
