import logging
import time
from contextlib import asynccontextmanager

import sentry_sdk
import uvicorn
from dockerflow.fastapi import router as dockerflow_router
from dockerflow.fastapi.middleware import (
    MozlogRequestSummaryLogger,
    RequestIdMiddleware,
)
from fastapi import FastAPI, Request
from sentry_sdk.integrations.logging import ignore_logger
from starlette.routing import Match

from .auth import auth_info_context
from .config import Settings, get_version
from .database import SessionLocal
from .log import CONFIG as LOG_CONFIG
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

app.add_middleware(MozlogRequestSummaryLogger)
app.add_middleware(RequestIdMiddleware)


@app.middleware("http")
async def send_metrics(request: Request, call_next):
    """Add timing and per-request logging context."""
    # Determine the path template, like "/ctms/{email_id}"
    path_template = None
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            path_template = str(route.path)
            break

    start_time = time.monotonic()
    response = None
    try:
        response = await call_next(request)
    finally:
        duration = time.monotonic() - start_time
        duration_s = round(duration, 3)
        auth_info = auth_info_context.get()

        emit_response_metrics(
            path_template=path_template,
            method=request.method,
            duration_s=duration_s,
            status_code=response.status_code if response else 500,
            client_id=auth_info.get("client_id"),
            metrics=get_metrics(),
        )

    return response


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=80, reload=True)
