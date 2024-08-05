import logging
import sys
import time


import uvicorn
from dockerflow.fastapi import router as dockerflow_router
from dockerflow.fastapi.middleware import RequestIdMiddleware
from fastapi import FastAPI, Request
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from .config import get_version
from .database import SessionLocal
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


web_logger = logging.getLogger("ctms.web")

app = FastAPI(
    title="ConTact Management System (CTMS)",
    description="CTMS API (work in progress)",
    version=get_version()["version"],
)
app.include_router(dockerflow_router)
app.include_router(platform.router)
app.include_router(contacts.router)


# Initialize Sentry for each thread, unless we're in tests
if "pytest" not in sys.argv[0]:  # pragma: no cover
    init_sentry()
    app.add_middleware(SentryAsgiMiddleware)


@app.on_event("startup")
def startup_event():  # pragma: no cover
    set_metrics(init_metrics(METRICS_REGISTRY))
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
