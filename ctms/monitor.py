"""Application monitoring and health utilities"""

import json
import logging
import os.path
import time
from datetime import datetime, timezone
from functools import lru_cache

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func, select

from ctms.crud import get_all_acoustic_records_count, get_all_acoustic_retries_count

logger = logging.getLogger(__name__)


def check_database(db_session, settings):
    """Check database availability and migration state."""
    start_time = time.monotonic()
    try:
        db_session.execute(select([func.now()])).first()
    except SQLAlchemyError as exc:
        logger.exception(exc)
        success = False
    else:
        success = True
    duration_s = time.monotonic() - start_time
    status = {"up": success, "time_ms": int(round(1000 * duration_s))}
    if not success:
        return status

    acoustic_start_time = time.monotonic()
    count = None
    retry_count = None
    retry_limit = settings.acoustic_retry_limit
    try:
        end_time = datetime.now(tz=timezone.utc)
        count = get_all_acoustic_records_count(db_session, end_time, retry_limit)
        retry_count = get_all_acoustic_retries_count(db_session)
    except SQLAlchemyError as exc:
        logger.exception(exc)
        acoustic_success = False
    else:
        acoustic_success = True
    acoustic_duration_s = time.monotonic() - acoustic_start_time
    status["acoustic"] = {
        "success": acoustic_success,
        "backlog": count,
        "max_backlog": settings.acoustic_max_backlog,
        "retry_backlog": retry_count,
        "max_retry_backlog": settings.acoustic_max_retry_backlog,
        "retry_limit": retry_limit,
        "batch_limit": settings.acoustic_batch_limit,
        "loop_min_sec": settings.acoustic_loop_min_secs,
        "time_ms": int(round(1000 * acoustic_duration_s)),
    }

    return status


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
        with open(version_path, "r", encoding="utf8") as version_file:
            info = json.load(version_file)
    return info
