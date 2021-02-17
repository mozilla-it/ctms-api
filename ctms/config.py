from pydantic import BaseSettings, PostgresDsn


class Settings(BaseSettings):
    db_url: PostgresDsn

    class Config:
        env_prefix = "ctms_"
