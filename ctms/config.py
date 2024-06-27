import json
import re
from datetime import timedelta
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseSettings, PostgresDsn

# If primary email matches, then add trace to logs
re_trace_email = re.compile(r".*\+trace-me-mozilla-.*@.*")


@lru_cache()
def get_version():
    """
    Return contents of version.json.

    This has generic data in repo, but gets the build details in CI.
    """
    ctms_root = Path(__file__).parent.parent
    version_path = ctms_root / "version.json"
    if version_path.exists():
        return json.loads(version_path.read_text())
    return {}


class LogLevel(str, Enum):
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


class DBSettings(BaseSettings):
    db_url: PostgresDsn
    db_pool_size: int = 5  # Default value from sqlalchemy
    db_max_overflow: int = 10  # Default value from sqlalchemy
    db_pool_timeout_in_seconds: int = 30  # Default value from sqlalchemy
    db_pool_recycle_in_seconds: int = 900  # 15 minutes
    log_sqlalchemy: bool = False

    class Config:
        # The attributes of this class extract from the Env Var's that are `(prefix)(attr_name)` within the environment
        env_prefix = "ctms_"


class AppSettings(BaseSettings):
    secret_key: str
    token_expiration: timedelta = timedelta(minutes=60)
    server_prefix: str = "http://localhost:8000"
    use_mozlog: bool = True
    logging_level: LogLevel = LogLevel.INFO
    sentry_debug: bool = False

    fastapi_env: Optional[str] = None
    host: str = "0.0.0.0"
    port: int = 8000

    prometheus_pushgateway_url: Optional[str] = None

    class Config:
        env_prefix = "ctms_"

        fields = {
            "fastapi_env": {"env": "fastapi_env"},
            "host": {"env": "host"},
            "port": {"env": "port"},
        }
