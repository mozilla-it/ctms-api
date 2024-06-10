from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

from .config import Settings


def get_engine():
    settings = Settings()
    return create_engine(
        settings.db_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout_in_seconds,
        pool_recycle=settings.db_pool_recycle_in_seconds,
        echo=settings.log_sqlalchemy,
    )


def session_factory(scoped: bool = False):
    factory = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    if scoped:
        factory = scoped_session(factory)
    return factory


Base = declarative_base()
