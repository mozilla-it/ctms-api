"""Logging configuration"""

import logging
import sys
from typing import Any, Dict, Optional

from dockerflow.logging import request_id_context
from fastapi import Request
from starlette.routing import Match

from ctms.config import Settings

settings = Settings()

CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {
            "()": "dockerflow.logging.RequestIdLogFilter",
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
            "filters": ["request_id"],
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


def context_from_request(request: Request) -> Dict:
    """Extract data from a log request."""
    host = None
    if request.client:
        host = request.client.host
    context: Dict[str, Any] = {
        "client_host": host,
        "method": request.method,
        "path": request.url.path,
        "rid": request_id_context.get(),
    }

    # Determine the path template, like "/ctms/{email_id}"
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            context["path_template"] = str(route.path)
            break

    if request.path_params:
        context["path_params"] = request.path_params

    # Process headers, omitting security-sensitive values
    headers = {}
    for header_name, header_value in request.headers.items():
        if header_name in {"cookie", "authorization"}:
            headers[header_name] = "[OMITTED]"
        else:
            headers[header_name] = header_value
    if headers:
        context["headers"] = headers

    # Process queries, removing personally-identifiable info
    query = {}
    for query_name, query_value in request.query_params.items():
        if query_name in {"primary_email", "fxa_primary_email"}:
            query[query_name] = "[OMITTED]"
        else:
            query[query_name] = query_value
    if query:
        context["query"] = query

    return context


def get_log_line(
    request: Request, status_code: int, user_id: Optional[str] = None
) -> str:
    """
    Create a log line for a web request

    This is based on the uvicorn log format, but doesn't match exactly.
    Our log looks uses repr, which surrounds the request line with single quotes:

    172.18.0.1:63750 - 'GET /openapi.json HTTP/1.1' 200

    The uvicorn format uses double quotes:

    172.18.0.1:63750 - "GET /openapi.json HTTP/1.1" 200
    """
    request_line = (
        f"{request.method} {request.url.path}" f" HTTP/{request.scope['http_version']}"
    )
    user = user_id or "-"
    host, port = None, None
    if request.client:
        host, port = request.client
    message = f"{host}:{port} {user} {request_line!r}" f" {status_code}"
    return message
