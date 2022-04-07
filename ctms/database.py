from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from . import config


def get_db_engine(settings: config.Settings):
    engine = create_engine(  # https://docs.sqlalchemy.org/en/14/core/engines.html#engine-creation-api
        settings.db_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout_in_seconds,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal


Base = declarative_base()
