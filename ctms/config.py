from pydantic import BaseSettings


class Settings(BaseSettings):
    db_url = "db_url"

    class Config:
        env_prefix = "ctms_"
