from datetime import timedelta
from typing import Literal

from pydantic import BaseSettings, PostgresDsn


class Settings(BaseSettings):
    db_url: PostgresDsn
    secret_key: str
    token_expiration: timedelta = timedelta(minutes=60)
    server_prefix: str = "http://localhost:8000"
    use_mozlog: bool = True
    logging_level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"] = "INFO"
    sentry_debug: bool = False

    class Config:
        env_prefix = "ctms_"


class BackgroundSettings(Settings):
    acoustic_loop_min_secs: int = 5
    acoustic_client_id: str
    acoustic_client_secret: str
    acoustic_refresh_token: str
    acoustic_main_table_id: str
    acoustic_newsletter_table_id: str
