from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from .config import Settings


def engine_factory(settings):
    return create_engine(
        settings.db_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout_in_seconds,
        pool_recycle=settings.db_pool_recycle_in_seconds,
        echo=settings.log_sqlalchemy,
    )


engine = engine_factory(Settings())
SessionLocal = sessionmaker(autoflush=False, bind=engine)
# Used for testing
ScopedSessionLocal = scoped_session(SessionLocal)
