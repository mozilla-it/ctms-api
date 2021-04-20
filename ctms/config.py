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

    class Config:
        env_prefix = "ctms_"
