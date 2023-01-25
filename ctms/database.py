from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from . import config


def get_db_engine(settings: config.Settings):
    engine = create_engine(  # https://docs.sqlalchemy.org/en/14/core/engines.html#engine-creation-api
        settings.db_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout_in_seconds,
        pool_recycle=settings.db_pool_recycle_in_seconds,
        echo=settings.log_sqlalchemy,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal


Base = declarative_base()
