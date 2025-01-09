"""Logging configuration"""

import logging
import sys
from typing import Any, Dict, Optional

from fastapi import Request
from starlette.routing import Match

from ctms.auth import auth_info_context
from ctms.config import Settings

settings = Settings()


class AuthInfoLogFilter(logging.Filter):
    """Logging filter to attach authentication information to logs"""

    def filter(self, record: "logging.LogRecord") -> bool:
        # All records attributes will be logged as fields.
        auth_info = auth_info_context.get()
        for k, v in auth_info.items():
            setattr(record, k, v)
        # MozLog also recommends using `uid` for user ids.
        record.uid = auth_info.get("client_id")
        return True


CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {
            "()": "dockerflow.logging.RequestIdLogFilter",
        },
        "auth_info": {
            "()": "ctms.log.AuthInfoLogFilter",
        },
    },
    "formatters": {
        "mozlog_json": {
            "()": "dockerflow.logging.JsonLogFormatter",
            "logger_name": "ctms",
        },
        "text": {
            "format": "%(asctime)s %(levelname)-8s [%(rid)s] %(name)-15s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "level": settings.logging_level.name,
            "class": "logging.StreamHandler",
            "filters": ["request_id", "auth_info"],
            "formatter": "mozlog_json" if settings.use_mozlog else "text",
            "stream": sys.stdout,
        },
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "loggers": {
        "": {"handlers": ["console"]},
        "request.summary": {"level": logging.INFO},
        "ctms": {"level": logging.DEBUG},
        "uvicorn": {"level": logging.INFO},
        "uvicorn.access": {"handlers": ["null"], "propagate": False},
        "sqlalchemy.engine": {
            "level": settings.logging_level.name
            if settings.log_sqlalchemy
            else logging.WARNING,
            "propagate": False,
        },
    },
}
