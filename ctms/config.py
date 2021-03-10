from datetime import timedelta

from pydantic import BaseSettings, PostgresDsn


class Settings(BaseSettings):
    db_url: PostgresDsn
    secret_key: str
    token_expiration: timedelta = timedelta(minutes=60)

    class Config:
        env_prefix = "ctms_"
