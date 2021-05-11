from datetime import timedelta
from typing import Literal, Optional

from pydantic import BaseSettings, DirectoryPath, PostgresDsn


class Settings(BaseSettings):
    db_url: PostgresDsn
    secret_key: str
    token_expiration: timedelta = timedelta(minutes=60)
    server_prefix: str = "http://localhost:8000"
    use_mozlog: bool = True
    logging_level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"] = "INFO"
    sentry_debug: bool = False

    fastapi_env: Optional[str] = None
    is_gunicorn: bool = False
    prometheus_multiproc_dir: Optional[DirectoryPath] = None

    class Config:
        env_prefix = "ctms_"

        fields = {
            "fastapi_env": {"env": "fastapi_env"},
            "is_gunicorn": {"env": "is_gunicorn"},
            "prometheus_multiproc_dir": {"env": "prometheus_multiproc_dir"},
        }


class BackgroundSettings(Settings):
    acoustic_sync_feature_flag: bool = False
    acoustic_retry_limit: int = 6
    acoustic_server_number: int = 6
    acoustic_loop_min_secs: int = 5
    acoustic_client_id: str
    acoustic_client_secret: str
    acoustic_refresh_token: str
    acoustic_main_table_id: int
    acoustic_newsletter_table_id: int
