import json
import re
from datetime import timedelta
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Optional

from pydantic import AfterValidator, Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

# If primary email matches, then add trace to logs
re_trace_email = re.compile(r".*\+trace-me-mozilla-.*@.*")

PostgresDsnStr = Annotated[PostgresDsn, AfterValidator(str)]


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


class Settings(BaseSettings):
    db_url: PostgresDsnStr
    db_pool_size: int = 5  # Default value from sqlalchemy
    db_max_overflow: int = 10  # Default value from sqlalchemy
    db_pool_timeout_in_seconds: int = 30  # Default value from sqlalchemy
    db_pool_recycle_in_seconds: int = 900  # 15 minutes
    secret_key: str
    token_expiration: timedelta = timedelta(minutes=60)
    server_prefix: str = "http://localhost:8000"
    use_mozlog: bool = True
    log_sqlalchemy: bool = False
    logging_level: LogLevel = LogLevel.INFO
    sentry_debug: bool = False

    fastapi_env: Optional[str] = Field(default=None, alias="FASTAPI_ENV")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    prometheus_pushgateway_url: Optional[str] = None

    model_config = SettingsConfigDict(env_prefix="ctms_")
