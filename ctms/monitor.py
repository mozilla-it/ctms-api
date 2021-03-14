"""Application monitoring and health utilities"""

import json
import os.path
import time
from functools import lru_cache

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func, select


def check_database(db_session):
    """Check database availability and migration state."""
    start_time = time.monotonic()
    try:
        db_session.execute(select([func.now()])).first()
    except SQLAlchemyError:
        success = False
    else:
        success = True
    duration_s = time.monotonic() - start_time
    return {"up": success, "time_ms": int(round(1000 * duration_s))}


@lru_cache()
def get_version():
    """
    Return contents of version.json.

    This has generic data in repo, but gets the build details in CI.
    """
    ctms_root = os.path.dirname(os.path.dirname(__file__))
    version_path = os.path.join(ctms_root, "version.json")
    info = {}
    if os.path.exists(version_path):
        with open(version_path, "r") as version_file:
            info = json.load(version_file)
    return info
