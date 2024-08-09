import logging
from typing import Optional

from dockerflow import checks as dockerflow_checks
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasicCredentials
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.orm import Session

from ctms.auth import (
    OAuth2ClientCredentialsRequestForm,
    auth_info_context,
    create_access_token,
    verify_password,
)
from ctms.crud import count_total_contacts, get_api_client_by_id, ping
from ctms.database import SessionLocal
from ctms.dependencies import get_db, get_enabled_api_client, get_token_settings
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
    auth_info = auth_info_context.get()
    failed_auth = HTTPException(
        status_code=400, detail="Incorrect username or password"
    )

    if form_data.client_id and form_data.client_secret:
        client_id = form_data.client_id
        client_secret = form_data.client_secret
        auth_info["token_creds_from"] = "form"
    elif basic_credentials:
        client_id = basic_credentials.username
        client_secret = basic_credentials.password
        auth_info["token_creds_from"] = "header"
    else:
        auth_info["token_fail"] = "No credentials"
        raise failed_auth

    auth_info["client_id"] = client_id
    api_client = get_api_client_by_id(db, client_id)
    if not api_client:
        auth_info["token_fail"] = "No client record"
        raise failed_auth
    if not api_client.enabled:
        auth_info["token_fail"] = "Client disabled"
        raise failed_auth
    if not verify_password(client_secret, api_client.hashed_secret):
        auth_info["token_fail"] = "Bad credentials"
        raise failed_auth

    access_token = create_access_token(
        data={"sub": f"api_client:{client_id}"}, **token_settings
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": int(token_settings["expires_delta"].total_seconds()),
    }


@dockerflow_checks.register
def database():
    result = []

    with SessionLocal() as db:
        alive = ping(db)
        if not alive:
            result.append(
                dockerflow_checks.Error("Database not reachable", id="db.0001")
            )
            return result
        # Report number of contacts in the database.
        # Sending the metric in this heartbeat endpoint is simpler than reporting
        # it in every write endpoint. Plus, performance does not matter much here
        total_contacts = count_total_contacts(db)

    contact_query_successful = total_contacts >= 0
    if contact_query_successful:
        appmetrics = get_metrics()
        if appmetrics:
            appmetrics["contacts"].set(total_contacts)
    else:
        result.append(dockerflow_checks.Error("Contacts table empty", id="db.0002"))

    return result


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
