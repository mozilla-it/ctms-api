import uvicorn

from ctms.config import AppSettings
from ctms.log import configure_logging

settings = AppSettings()


if __name__ == "__main__":
    logging_config = configure_logging(
        settings.use_mozlog, settings.logging_level.name, settings.log_sqlalchemy
    )

    server = uvicorn.Server(
        uvicorn.Config(
            "ctms.app:app",
            host=settings.host,
            port=settings.port,
            log_config=logging_config,
        )
    )
    server.run()
