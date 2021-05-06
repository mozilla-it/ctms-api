"""Prometheus metrics for instrumentation and monitoring."""

from itertools import product
from typing import Dict, Optional, cast

from fastapi import FastAPI
from fastapi.requests import Request
from prometheus_client import CollectorRegistry, Counter, Histogram
from prometheus_client.metrics import MetricWrapperBase
from prometheus_client.multiprocess import MultiProcessCollector
from prometheus_client.utils import INF
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette.routing import Match, Route

from ctms import config
from ctms.crud import get_active_api_client_ids

METRICS_PARAMS = {
    "requests": (
        Counter,
        {
            "name": "ctms_requests_total",
            "documentation": "Total count of requests by method, path, and status code.",
            "labelnames": ["method", "path_template", "status_code"],
        },
    ),
    "requests_duration": (
        Histogram,
        {
            "name": "ctms_requests_duration_seconds",
            "documentation": "Histogram of requests processing time by path (in seconds)",
            "labelnames": ["method", "path_template"],
            "buckets": (0.01, 0.05, 0.1, 0.5, 1, 5, 10, INF),
        },
    ),
    "api_requests": (
        Counter,
        {
            "name": "ctms_api_requests_total",
            "documentation": "Total count of API requests by method, path, client ID, and status code family",
            "labelnames": [
                "method",
                "path_template",
                "client_id",
                "status_code_family",
            ],
        },
    ),
}


def init_metrics_registry() -> CollectorRegistry:
    """
    Initialize a metrics registry.

    If we're running under gunicorn, we need a multiprocess collector that
    points to a folder that was created empty at startup.

    If we're not running under gunicorn, we could use the default REGISTRY, but
    a fresh registry is easier to reset for tests, and forcing the web code to
    go through this method will ensure we're using roughly the same code paths
    in development and production.
    """
    try:
        settings = config.Settings()
        prometheus_multiproc_dir = settings.prometheus_multiproc_dir
    except ValidationError:
        prometheus_multiproc_dir = None

    registry = CollectorRegistry()
    if prometheus_multiproc_dir:
        MultiProcessCollector(registry, path=prometheus_multiproc_dir)
    return registry


def init_metrics(registry: CollectorRegistry) -> Dict[str, MetricWrapperBase]:
    """Initialize the metrics with the registry."""
    metrics = {}
    for name, init_bits in METRICS_PARAMS.items():
        metric_type, params = init_bits
        metrics[name] = metric_type(registry=registry, **params)
    return metrics


def init_metrics_labels(
    dbsession: Session, app: FastAPI, metrics: Dict[str, MetricWrapperBase]
) -> None:
    """Create the initial metric combinations."""
    openapi = app.openapi()
    client_ids = get_active_api_client_ids(dbsession) or ["none"]
    request_metric = metrics["requests"]
    timing_metric = metrics["requests_duration"]
    api_request_metric = metrics["api_requests"]
    for route in app.routes:
        assert isinstance(route, Route)
        route = cast(Route, route)  # Route defines.methods and .path_format
        methods = list(route.methods)
        path = route.path_format

        api_spec = openapi["paths"].get(path)
        is_api = False
        if api_spec:
            status_codes = []
            for method_lower, mspec in api_spec.items():
                if method_lower.upper() in methods:
                    status_codes.extend(
                        [int(code) for code in list(mspec.get("responses", [200]))]
                    )
                    is_api |= "security" in mspec
            status_code_families = sorted(
                {str(code)[0] + "xx" for code in status_codes}
            )
        elif path == "/":
            status_codes = [307]
        else:
            status_codes = [200]

        for combo in product(methods, status_codes):
            method, status_code = combo
            request_metric.labels(method, path, status_code)
        for method in methods:
            timing_metric.labels(method, path)
        if is_api:
            for api_combo in product(methods, status_code_families):
                method, status_code_family = api_combo
                for client_id in client_ids:
                    api_request_metric.labels(
                        method, path, client_id, status_code_family
                    )


def emit_response_metrics(
    request: Request, status_code: int, metrics: Dict[str, MetricWrapperBase]
) -> None:
    """Emit metrics for a response."""
    if not metrics:
        return
    path_template = get_path_template(request)
    if path_template is None:
        return
    method = request.method
    metrics["requests"].labels(
        method=method, path_template=path_template, status_code=status_code
    ).inc()

    duration_s = request.state.log_context["duration_s"]
    metrics["requests_duration"].labels(
        method=method, path_template=path_template
    ).observe(duration_s)

    client_id = request.state.log_context.get("client_id")
    if client_id:
        status_code_family = str(status_code)[0] + "xx"
        metrics["api_requests"].labels(
            method=method,
            path_template=path_template,
            client_id=client_id,
            status_code_family=status_code_family,
        ).inc()


def get_path_template(request: Request) -> Optional[str]:
    """Get the path template for the request, or fall back to plain path."""
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return str(route.path)

    return None  # Not a known application route
