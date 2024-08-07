import logging
import time
from contextlib import asynccontextmanager

import sentry_sdk
import uvicorn
from dockerflow.fastapi import router as dockerflow_router
from dockerflow.fastapi.middleware import RequestIdMiddleware
from fastapi import FastAPI, Request
from sentry_sdk.integrations.logging import ignore_logger

from .config import Settings, get_version
from .database import SessionLocal
from .log import CONFIG as LOG_CONFIG
from .log import context_from_request, get_log_line
from .metrics import (
    METRICS_REGISTRY,
    emit_response_metrics,
    get_metrics,
    init_metrics,
    init_metrics_labels,
    set_metrics,
)
from .routers import contacts, platform

logging.config.dictConfig(LOG_CONFIG)

web_logger = logging.getLogger("ctms.web")

settings = Settings()

sentry_sdk.init(
    dsn=settings.sentry_dsn,
    release=get_version()["version"],
    debug=settings.sentry_debug,
    send_default_pii=False,
)
ignore_logger("uvicorn.error")
ignore_logger("ctms.web")


@asynccontextmanager
async def lifespan(app: FastAPI):
    set_metrics(init_metrics(METRICS_REGISTRY))
    init_metrics_labels(SessionLocal(), app, get_metrics())
    yield


app = FastAPI(
    title="ConTact Management System (CTMS)",
    description="CTMS API (work in progress)",
    version=get_version()["version"],
    lifespan=lifespan,
)
app.include_router(dockerflow_router)
app.include_router(platform.router)
app.include_router(contacts.router)


@app.middleware("http")
async def log_request_middleware(request: Request, call_next):
    """Add timing and per-request logging context."""
    start_time = time.monotonic()
    request.state.log_context = context_from_request(request)
    response = None
    try:
        response = await call_next(request)
    finally:
        if response is None:
            status_code = 500
        else:
            status_code = response.status_code

        context = request.state.log_context
        if request.path_params:
            context["path_params"] = request.path_params

        log_line = get_log_line(request, status_code, context.get("client_id"))
        duration = time.monotonic() - start_time
        duration_s = round(duration, 3)

        emit_response_metrics(
            path_template=context.get("path_template"),
            method=context["method"],
            duration_s=duration_s,
            status_code=status_code,
            client_id=context.get("client_id"),
            metrics=get_metrics(),
        )

        context.update({"status_code": status_code, "duration_s": duration_s})
        if response is None:
            web_logger.error(log_line, extra=context)
        else:
            web_logger.info(log_line, extra=context)
    return response


app.add_middleware(RequestIdMiddleware)

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=80, reload=True)
