from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPBasicCredentials
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.orm import Session
from structlog.testing import capture_logs

from ctms.auth import (
    OAuth2ClientCredentialsRequestForm,
    create_access_token,
    verify_password,
)
from ctms.config import Settings
from ctms.crud import (
    get_all_acoustic_fields,
    get_all_acoustic_newsletters_mapping,
    get_api_client_by_id,
)
from ctms.dependencies import (
    get_db,
    get_enabled_api_client,
    get_settings,
    get_token_settings,
)
from ctms.metrics import get_metrics_registry, token_scheme
from ctms.monitor import check_database, get_version
from ctms.schemas.api_client import ApiClientSchema
from ctms.schemas.web import BadRequestResponse, TokenResponse

version_info = get_version()

router = APIRouter()


@router.get("/", include_in_schema=False)
def root(request: Request):
    """GET via root redirects to /docs.

    - Args:

    - Returns:
        - **redirect**: Redirects call to ./docs
    """
    request.state.log_context["trivial_code"] = 307
    return RedirectResponse(url="./docs")


@router.post(
    "/token",
    include_in_schema=False,
    summary="Get OAuth2 access token",
    response_model=TokenResponse,
    responses={400: {"model": BadRequestResponse}},
)
def login(
    request: Request,
    db: Session = Depends(get_db),
    form_data: OAuth2ClientCredentialsRequestForm = Depends(),
    basic_credentials: Optional[HTTPBasicCredentials] = Depends(token_scheme),
    token_settings=Depends(get_token_settings),
):
    log_context = request.state.log_context
    failed_auth = HTTPException(
        status_code=400, detail="Incorrect username or password"
    )

    if form_data.client_id and form_data.client_secret:
        client_id = form_data.client_id
        client_secret = form_data.client_secret
        log_context["token_creds_from"] = "form"
    elif basic_credentials:
        client_id = basic_credentials.username
        client_secret = basic_credentials.password
        log_context["token_creds_from"] = "header"
    else:
        log_context["token_fail"] = "No credentials"
        raise failed_auth

    log_context["client_id"] = client_id
    api_client = get_api_client_by_id(db, client_id)
    if not api_client:
        log_context["token_fail"] = "No client record"
        raise failed_auth
    if not api_client.enabled:
        log_context["token_fail"] = "Client disabled"
        raise failed_auth
    if not verify_password(client_secret, api_client.hashed_secret):
        log_context["token_fail"] = "Bad credentials"
        raise failed_auth

    access_token = create_access_token(
        data={"sub": f"api_client:{client_id}"}, **token_settings
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": int(token_settings["expires_delta"].total_seconds()),
    }


@router.get("/__version__", tags=["Platform"])
def version():
    """Return version.json, as required by Dockerflow."""
    return version_info


@router.get("/__heartbeat__", tags=["Platform"])
@router.head("/__heartbeat__", tags=["Platform"])
def heartbeat(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Return status of backing services, as required by Dockerflow."""
    x_nr_synthetics = request.headers.get("x-newrelic-synthetics", "")
    x_abuse_info = request.headers.get("x-abuse-info", "")
    user_agent = request.headers.get("user-agent", "")
    is_newrelic = x_nr_synthetics != "" and x_abuse_info.startswith(
        "Request sent by a New Relic Synthetics Monitor ("
    )
    is_amazon = user_agent.startswith("Amazon-Route53-Health-Check-Service (")
    if is_newrelic or is_amazon:
        request.state.log_context["trivial_code"] = 200
    data = {"database": check_database(db, settings)}
    status_code = 200
    if not data["database"]["up"]:
        status_code = 503
    if "acoustic" in data["database"]:
        backlog = data["database"]["acoustic"]["backlog"]
        retry_backlog = data["database"]["acoustic"]["retry_backlog"]
        max_backlog = data["database"]["acoustic"]["max_backlog"]
        max_retry_backlog = data["database"]["acoustic"]["max_retry_backlog"]

        if max_backlog is not None and max_backlog > backlog:
            status_code = 503
        if max_retry_backlog is not None and max_retry_backlog > retry_backlog:
            status_code = 503
    return JSONResponse(content=data, status_code=status_code)


@router.get("/__lbheartbeat__", tags=["Platform"])
@router.head("/__lbheartbeat__", tags=["Platform"])
def lbheartbeat(request: Request):
    """Return response when application is running, as required by Dockerflow."""
    user_agent = request.headers.get("user-agent", "")
    if user_agent.startswith("kube-probe/"):
        request.state.log_context["trivial_code"] = 200
    return {"status": "OK"}


@router.get("/__crash__", tags=["Platform"], include_in_schema=False)
def crash(api_client: ApiClientSchema = Depends(get_enabled_api_client)):
    """Raise an exception to test Sentry integration."""
    raise RuntimeError("Test exception handling")


@router.get("/metrics", tags=["Platform"])
def metrics(request: Request):
    """Return Prometheus metrics"""
    agent = request.headers.get("user-agent", "")
    if agent.startswith("Prometheus/"):
        request.state.log_context["trivial_code"] = 200
    headers = {"Content-Type": CONTENT_TYPE_LATEST}
    registry = get_metrics_registry()
    return Response(generate_latest(registry), status_code=200, headers=headers)


@router.get("/acoustic_configuration", tags=["Platform"])
def configuration(
    request: Request,
    db_session: Session = Depends(get_db),
):
    """Return Acoustic configuration, publicly readable"""
    all_fields = get_all_acoustic_fields(db_session)
    fields_grouped_by_tablename = defaultdict(list)
    for entry in all_fields:
        fields_grouped_by_tablename[entry.tablename].append(entry.field)

    newsletter_mappings = {
        entry.source: entry.destination
        for entry in get_all_acoustic_newsletters_mapping(db_session)
    }

    return {
        "sync_fields": fields_grouped_by_tablename,
        "newsletter_mappings": newsletter_mappings,
    }


def test_get_metrics(anon_client, setup_metrics):
    """An anonoymous user can request metrics."""
    with capture_logs() as cap_logs:
        resp = anon_client.get("/metrics")
    assert resp.status_code == 200
    assert len(cap_logs) == 1
    assert "trivial" not in cap_logs[0]


def test_prometheus_metrics_is_logged_as_trivial(anon_client, setup_metrics):
    """When Prometheus requests metrics, it is logged as trivial."""
    headers = {"user-agent": "Prometheus/2.26.0"}
    with capture_logs() as cap_logs:
        resp = anon_client.get("/metrics", headers=headers)
    assert resp.status_code == 200
    assert len(cap_logs) == 1
    assert cap_logs[0]["trivial"] is True