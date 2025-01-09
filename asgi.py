import uvicorn

from ctms.config import Settings

settings = Settings()


if __name__ == "__main__":
    server = uvicorn.Server(
        uvicorn.Config(
            "ctms.app:app",
            host=settings.host,
            port=settings.port,
            log_config=None,
        )
    )
    server.run()
