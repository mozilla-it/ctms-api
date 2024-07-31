import logging
import time
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPBasicCredentials
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.orm import Session

from ctms.auth import (
    OAuth2ClientCredentialsRequestForm,
    create_access_token,
    verify_password,
)
from ctms.config import Settings, get_version
from ctms.crud import count_total_contacts, get_api_client_by_id, ping
from ctms.dependencies import (
    get_db,
    get_enabled_api_client,
    get_settings,
    get_token_settings,
)
from ctms.metrics import get_metrics, get_metrics_registry, token_scheme
from ctms.schemas.api_client import ApiClientSchema
from ctms.schemas.web import BadRequestResponse, TokenResponse

router = APIRouter()


logger = logging.getLogger(__name__)


@router.get("/", include_in_schema=False)
def root():
    """GET via root redirects to /docs.

    - Args:

    - Returns:
        - **redirect**: Redirects call to ./docs
    """
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


@router.get("/__heartbeat__", tags=["Platform"])
@router.head("/__heartbeat__", tags=["Platform"])
def heartbeat(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Return status of backing services, as required by Dockerflow."""

    result: dict[str, Any] = {}

    start_time = time.monotonic()
    alive = ping(db)
    result["database"] = {
        "up": alive,
        "time_ms": int(round(1000 * time.monotonic() - start_time)),
    }
    if not alive:
        return JSONResponse(content=result, status_code=503)

    appmetrics = get_metrics()
    # Report number of contacts in the database.
    # Sending the metric in this heartbeat endpoint is simpler than reporting
    # it in every write endpoint. Plus, performance does not matter much here
    total_contacts = count_total_contacts(db)
    contact_query_successful = total_contacts >= 0
    if appmetrics and contact_query_successful:
        appmetrics["contacts"].set(total_contacts)

    status_code = 200 if contact_query_successful else 503
    return JSONResponse(content=result, status_code=status_code)


@router.get("/__crash__", tags=["Platform"], include_in_schema=False)
def crash(api_client: ApiClientSchema = Depends(get_enabled_api_client)):
    """Raise an exception to test Sentry integration."""
    raise RuntimeError("Test exception handling")


@router.get("/metrics", tags=["Platform"])
def metrics():
    """Return Prometheus metrics"""
    headers = {"Content-Type": CONTENT_TYPE_LATEST}
    registry = get_metrics_registry()
    return Response(generate_latest(registry), status_code=200, headers=headers)
