import re
from datetime import timedelta
from enum import Enum
from typing import Optional

from pydantic import BaseSettings, DirectoryPath, PostgresDsn

# If primary email matches, then add trace to logs
re_trace_email = re.compile(r".*\+trace-me-mozilla-.*@.*")


class LogLevel(str, Enum):
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


class Settings(BaseSettings):
    db_url: PostgresDsn
    db_pool_size: int = 5  # Default value from sqlalchemy
    db_max_overflow: int = 10  # Default value from sqlalchemy
    db_pool_timeout_in_seconds: int = 30  # Default value from sqlalchemy
    secret_key: str
    token_expiration: timedelta = timedelta(minutes=60)
    server_prefix: str = "http://localhost:8000"
    use_mozlog: bool = True
    logging_level: LogLevel = LogLevel.INFO
    sentry_debug: bool = False

    fastapi_env: Optional[str] = None
    is_gunicorn: bool = False
    prometheus_multiproc_dir: Optional[DirectoryPath] = None

    pubsub_audience: Optional[str] = None
    pubsub_email: Optional[str] = None
    pubsub_client: Optional[str] = None

    # Background settings
    acoustic_sync_feature_flag: bool = False  # Enable/disable whole background sync job
    acoustic_integration_feature_flag: bool = (
        False  # Enable/disable integration w/ Acoustic
    )
    acoustic_retry_limit: int = 6
    acoustic_batch_limit: int = 20
    acoustic_server_number: int = 6
    acoustic_loop_min_secs: int = 5
    acoustic_max_backlog: Optional[int] = None
    acoustic_max_retry_backlog: Optional[int] = None

    # Background settings, optional for API
    acoustic_client_id: Optional[str] = None
    acoustic_client_secret: Optional[str] = None
    acoustic_refresh_token: Optional[str] = None
    acoustic_main_table_id: Optional[int] = None
    acoustic_newsletter_table_id: Optional[int] = None
    acoustic_product_subscriptions_id: Optional[int] = None
    prometheus_pushgateway_url: Optional[str] = None
    background_healthcheck_path: Optional[str] = None
    background_healthcheck_age_s: Optional[int] = None
    acoustic_timeout_s: float = 5.0

    class Config:
        # The attributes of this class extract from the Env Var's that are `(prefix)(attr_name)` within the environment
        env_prefix = "ctms_"

        fields = {
            "fastapi_env": {"env": "fastapi_env"},
            "is_gunicorn": {"env": "is_gunicorn"},
            "prometheus_multiproc_dir": {"env": "prometheus_multiproc_dir"},
        }


class BackgroundSettings(Settings):
    # Required background settings
    acoustic_client_id: str
    acoustic_client_secret: str
    acoustic_refresh_token: str
    acoustic_main_table_id: int
    acoustic_newsletter_table_id: int
    acoustic_product_subscriptions_id: int
    prometheus_pushgateway_url: str

    logging_level: LogLevel = LogLevel.DEBUG  # Overloaded Default for Background Job
