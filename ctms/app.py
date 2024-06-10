import sys
import time
from secrets import token_hex

import structlog
import uvicorn
from fastapi import FastAPI, Request
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from .config import get_version
from .database import session_factory
from .exception_capture import init_sentry
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

app = FastAPI(
    title="ConTact Management System (CTMS)",
    description="CTMS API (work in progress)",
    version=get_version()["version"],
)
app.include_router(platform.router)
app.include_router(contacts.router)


# Initialize Sentry for each thread, unless we're in tests
if "pytest" not in sys.argv[0]:  # pragma: no cover
    init_sentry()
    app.add_middleware(SentryAsgiMiddleware)


@app.on_event("startup")
def startup_event():  # pragma: no cover
    set_metrics(init_metrics(METRICS_REGISTRY))
    SessionLocal = session_factory()
    init_metrics_labels(SessionLocal(), app, get_metrics())


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
        context.update({"status_code": status_code, "duration_s": duration_s})

        emit_response_metrics(context, get_metrics())
        logger = structlog.get_logger("ctms.web")
        if response is None:
            logger.error(log_line, **context)
        else:
            logger.info(log_line, **context)
    return response


@app.middleware("http")
async def request_id(request: Request, call_next):
    """Read the request id from headers. This is set by NGinx."""
    request.state.rid = request.headers.get("X-Request-Id", token_hex(16))
    response = await call_next(request)
    return response


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=80, reload=True)
