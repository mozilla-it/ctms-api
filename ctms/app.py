"""The CTMS application, including middleware and routes."""
# pylint:disable = too-many-lines
# pylint:disable = too-many-statements
import json
import sys
import time
from base64 import b64decode
from collections import defaultdict
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Dict, List, Literal, Optional, Tuple, Union
from uuid import UUID, uuid4

import sentry_sdk
import structlog
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Path, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from google.auth.exceptions import GoogleAuthError
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest
from pydantic import ValidationError
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session
from starlette import status

from . import config
from .auth import (
    OAuth2ClientCredentials,
    OAuth2ClientCredentialsRequestForm,
    create_access_token,
    get_claim_from_pubsub_token,
    get_subject_from_token,
    verify_password,
)
from .config import re_trace_email
from .crud import (
    create_contact,
    create_or_update_contact,
    gdpr_delete,
    get_all_acoustic_fields,
    get_all_acoustic_newsletters_mapping,
    get_api_client_by_id,
    get_bulk_contacts,
    get_contact_by_email_id,
    get_email,
    get_emails_by_any_id,
    schedule_acoustic_record,
    update_contact,
)
from .database import SessionLocal
from .exception_capture import init_sentry
from .ingest_stripe import (
    StripeIngestActions,
    StripeIngestFxAIdConflict,
    StripeIngestUnknownObjectError,
    ingest_stripe_object,
)
from .log import context_from_request, get_log_line
from .metrics import emit_response_metrics, init_metrics, init_metrics_labels
from .models import Email, StripeCustomer
from .monitor import check_database, get_version
from .schemas import (
    AddOnsSchema,
    ApiClientSchema,
    BadRequestResponse,
    BulkRequestSchema,
    ContactInSchema,
    ContactPatchSchema,
    ContactPutSchema,
    ContactSchema,
    CTMSBulkResponse,
    CTMSResponse,
    CTMSSingleResponse,
    EmailSchema,
    FirefoxAccountsSchema,
    GDPRDeleteResponse,
    IdentityResponse,
    MozillaFoundationSchema,
    NotFoundResponse,
    TokenResponse,
    UnauthorizedResponse,
)

version_info = get_version()

app = FastAPI(
    title="ConTact Management System (CTMS)",
    description="CTMS API (work in progress)",
    version=version_info["version"],
)
METRICS_REGISTRY = CollectorRegistry()
METRICS = None

# We could use the default prometheus_client.REGISTRY, but it makes tests
# easier to write if it is possible to replace the registry with a fresh one.
# pylint: disable-next=unnecessary-lambda-assignment
get_metrics_registry = lambda: METRICS_REGISTRY
get_metrics = lambda: METRICS  # pylint: disable=unnecessary-lambda-assignment
oauth2_scheme = OAuth2ClientCredentials(tokenUrl="token")
token_scheme = HTTPBasic(auto_error=False)


@lru_cache()
def get_settings() -> config.Settings:
    return config.Settings()


# Initialize Sentry for each thread, unless we're in tests
if "pytest" not in sys.argv[0]:  # pragma: no cover
    init_sentry()
    app.add_middleware(SentryAsgiMiddleware)


@app.on_event("startup")
def startup_event():  # pragma: no cover
    global METRICS  # pylint:disable = W0603
    METRICS = init_metrics(METRICS_REGISTRY)
    init_metrics_labels(SessionLocal(), app, METRICS)


def get_db():  # pragma: no cover
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _token_settings(
    settings: config.Settings = Depends(get_settings),
) -> Dict[str, Union[str, timedelta]]:
    return {
        "expires_delta": settings.token_expiration,
        "secret_key": settings.secret_key,
    }


def _pubsub_settings(
    settings: config.Settings = Depends(get_settings),
) -> Dict[str, str]:
    return {
        "audience": settings.pubsub_audience or settings.server_prefix,
        "email": settings.pubsub_email,
        "client": settings.pubsub_client,
    }


def get_email_or_404(db: Session, email_id) -> Email:
    """Get an email and related data by email_ID, or raise a 404 exception."""
    email = get_email(db, email_id)
    if email is None:
        raise HTTPException(status_code=404, detail="Unknown email_id")
    return email


def get_contact_or_404(db: Session, email_id) -> ContactSchema:
    """Get a contact by email_ID, or raise a 404 exception."""
    email = get_email_or_404(db, email_id)
    return ContactSchema(
        amo=email.amo,
        email=email,
        fxa=email.fxa,
        mofo=email.mofo,
        newsletters=email.newsletters,
        waitlists=email.waitlists,
    )


def all_ids(
    email_id: Optional[UUID] = None,
    primary_email: Optional[str] = None,
    basket_token: Optional[UUID] = None,
    sfdc_id: Optional[str] = None,
    mofo_contact_id: Optional[str] = None,
    mofo_email_id: Optional[str] = None,
    amo_user_id: Optional[str] = None,
    fxa_id: Optional[str] = None,
    fxa_primary_email: Optional[str] = None,
):
    """Alternate IDs, injected as a dependency."""
    return {
        "email_id": email_id,
        "primary_email": primary_email,
        "basket_token": basket_token,
        "sfdc_id": sfdc_id,
        "mofo_contact_id": mofo_contact_id,
        "mofo_email_id": mofo_email_id,
        "amo_user_id": amo_user_id,
        "fxa_id": fxa_id,
        "fxa_primary_email": fxa_primary_email,
    }


def get_contacts_by_ids(
    db: Session,
    email_id: Optional[UUID] = None,
    primary_email: Optional[str] = None,
    basket_token: Optional[UUID] = None,
    sfdc_id: Optional[str] = None,
    mofo_contact_id: Optional[str] = None,
    mofo_email_id: Optional[str] = None,
    amo_user_id: Optional[str] = None,
    fxa_id: Optional[str] = None,
    fxa_primary_email: Optional[str] = None,
) -> List[ContactSchema]:
    """Get contacts by any ID.

    Callers are expected to set just one ID, but if multiple are set, a contact
    must match all IDs.
    """
    rows = get_emails_by_any_id(
        db,
        email_id,
        primary_email,
        basket_token,
        sfdc_id,
        mofo_contact_id,
        mofo_email_id,
        amo_user_id,
        fxa_id,
        fxa_primary_email,
    )
    return [
        ContactSchema(
            amo=email.amo,
            email=email,
            fxa=email.fxa,
            mofo=email.mofo,
            newsletters=email.newsletters,
            waitlists=email.waitlists,
        )
        for email in rows
    ]


def get_bulk_contacts_by_timestamp_or_4xx(
    db: Session,
    start_time: datetime,
    end_time: datetime,
    limit: int = 10,
    after: str = None,
    mofo_relevant: bool = None,
) -> CTMSBulkResponse:
    """Get bulk contacts by time range."""
    after_email_id = None
    after_start_time = start_time
    if after is not None:
        (
            after_email_id,
            after_start_time,
        ) = BulkRequestSchema.extractor_for_bulk_encoded_details(after)

    results = get_bulk_contacts(
        db=db,
        start_time=after_start_time,
        end_time=end_time,
        limit=limit,
        after_email_id=after_email_id,
        mofo_relevant=mofo_relevant,
    )
    page_length = len(results)
    last_page = page_length < limit
    if page_length > 0:
        results = [
            CTMSResponse(
                amo=contact.amo or AddOnsSchema(),
                email=contact.email or EmailSchema(),
                fxa=contact.fxa or FirefoxAccountsSchema(),
                mofo=contact.mofo or MozillaFoundationSchema(),
                newsletters=contact.newsletters or [],
                waitlists=contact.waitlists or [],
            )
            for contact in results
        ]

    if last_page:
        # No results/end
        after_encoded = None
        next_url = None
    else:
        last_result: CTMSResponse = results[-1]
        after_encoded = BulkRequestSchema.compressor_for_bulk_encoded_details(
            last_email_id=last_result.email.email_id,
            last_update_time=last_result.email.update_timestamp,
        )

        next_url = (
            f"{get_settings().server_prefix}/updates?"
            f"start={start_time.isoformat()}"
            f"&end={end_time.isoformat()}"
            f"&limit={limit}"
            f"&after={after_encoded} "
        )

    return CTMSBulkResponse(
        start=start_time,
        end=end_time,
        after=after_encoded,
        limit=limit,
        items=results,
        next=next_url,
    )


def get_api_client(
    request: Request,
    token: str = Depends(oauth2_scheme),
    token_settings=Depends(_token_settings),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    namespace, name = get_subject_from_token(
        token,
        secret_key=token_settings["secret_key"],
    )
    log_context = request.state.log_context
    log_context["client_allowed"] = False

    if name is None:
        log_context["auth_fail"] = "No or bad token"
        raise credentials_exception

    log_context["client_id"] = name
    if namespace != "api_client":
        log_context["auth_fail"] = "Bad namespace"
        raise credentials_exception

    api_client = get_api_client_by_id(db, name)
    if not api_client:
        log_context["auth_fail"] = "No client record"
        raise credentials_exception

    return api_client


def get_enabled_api_client(
    request: Request, api_client: ApiClientSchema = Depends(get_api_client)
):
    log_context = request.state.log_context
    if not log_context.get("client_id"):
        # get_api_client was overridden by test
        log_context["client_id"] = api_client.client_id
    if not api_client.enabled:
        log_context["auth_fail"] = "Client disabled"
        raise HTTPException(status_code=400, detail="API Client has been disabled")
    log_context["client_allowed"] = True
    return api_client


def get_pubsub_claim(
    request: Request,
    token: str = Depends(oauth2_scheme),
    pubsub_settings=Depends(_pubsub_settings),
    pubsub_client: str = None,
):
    for name in ("audience", "email", "client"):
        if not pubsub_settings[name]:
            # pylint: disable-next=broad-exception-raised
            raise Exception(f"PUBSUB_{name.upper()} is unset")

    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    log_context = request.state.log_context
    log_context["client_allowed"] = False

    if pubsub_client != pubsub_settings["client"]:
        log_context["auth_fail"] = "Verification mismatch"
        raise credentials_exception

    try:
        claim = get_claim_from_pubsub_token(token, pubsub_settings["audience"])
    except ValueError as exception:
        sentry_sdk.capture_exception(exception)
        log_context["auth_fail"] = "Unknown key"
        raise credentials_exception from exception
    except GoogleAuthError as exception:
        sentry_sdk.capture_exception(exception)
        log_context["auth_fail"] = "Google authentication failure"
        raise credentials_exception from exception

    # Add claim as context for debugging
    for key, value in claim.items():
        log_context[f"pubsub_{key}"] = value

    if claim.get("email") != pubsub_settings["email"]:
        log_context["auth_fail"] = "Wrong email"
        raise credentials_exception

    if not claim.get("email_verified"):
        log_context["auth_fail"] = "Email not verified"
        raise credentials_exception

    log_context["client_allowed"] = True
    return claim


async def get_json(request: Request) -> Dict:
    """
    Get the request body as JSON.

    If the body is not valid JSON, FastAPI will return a ValidationError or 400
    before this dependency is resolved.
    If the body is form-encoded, it will raise an unknown exception.
    """
    the_json: Dict = await request.json()
    return the_json


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
        if "trivial_code" in context:
            if status_code == context["trivial_code"]:
                context["trivial"] = True
            del context["trivial_code"]
        if context["trivial"] is False:
            del context["trivial"]
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


@app.get("/", include_in_schema=False)
def root(request: Request):
    """GET via root redirects to /docs.

    - Args:

    - Returns:
        - **redirect**: Redirects call to ./docs
    """
    request.state.log_context["trivial_code"] = 307
    return RedirectResponse(url="./docs")


@app.get(
    "/ctms",
    summary="Get all contacts matching alternate IDs",
    response_model=List[CTMSResponse],
    responses={
        400: {"model": BadRequestResponse},
        401: {"model": UnauthorizedResponse},
    },
    tags=["Public"],
)
def read_ctms_by_any_id(
    request: Request,
    db: Session = Depends(get_db),
    api_client: ApiClientSchema = Depends(get_enabled_api_client),
    ids=Depends(all_ids),
):
    if not any(ids.values()):
        detail = (
            f"No identifiers provided, at least one is needed: {', '.join(ids.keys())}"
        )
        raise HTTPException(status_code=400, detail=detail)
    contacts = get_contacts_by_ids(db, **ids)
    traced = set()
    for contact in contacts:
        email = contact.email.primary_email
        if re_trace_email.match(email):
            traced.add(email)
    if traced:
        request.state.log_context["trace"] = ",".join(sorted(traced))
    return [
        CTMSResponse(
            amo=contact.amo or AddOnsSchema(),
            email=contact.email or EmailSchema(),
            fxa=contact.fxa or FirefoxAccountsSchema(),
            mofo=contact.mofo or MozillaFoundationSchema(),
            newsletters=contact.newsletters or [],
            waitlists=contact.waitlists or [],
        )
        for contact in contacts
    ]


@app.get(
    "/ctms/{email_id}",
    summary="Get a contact by email_id",
    response_model=CTMSSingleResponse,
    responses={
        401: {"model": UnauthorizedResponse},
        404: {"model": NotFoundResponse},
    },
    tags=["Public"],
)
def read_ctms_by_email_id(
    request: Request,
    email_id: UUID = Path(..., title="The Email ID"),
    db: Session = Depends(get_db),
    api_client: ApiClientSchema = Depends(get_enabled_api_client),
):
    resp = get_ctms_response_or_404(db, email_id)
    email = resp.email.primary_email
    if re_trace_email.match(email):
        request.state.log_context["trace"] = email
    return resp


def get_ctms_response_or_404(db, email_id):
    contact = get_contact_or_404(db, email_id)
    return CTMSSingleResponse(
        amo=contact.amo or AddOnsSchema(),
        email=contact.email or EmailSchema(),
        fxa=contact.fxa or FirefoxAccountsSchema(),
        mofo=contact.mofo or MozillaFoundationSchema(),
        newsletters=contact.newsletters or [],
        waitlists=contact.waitlists or [],
        status="ok",
    )


@app.post(
    "/ctms",
    summary="Create a contact, generating an id if not specified.",
    response_model=CTMSSingleResponse,
    responses={409: {"model": BadRequestResponse}},
    tags=["Public"],
)
def create_ctms_contact(
    contact: ContactInSchema,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    api_client: ApiClientSchema = Depends(get_enabled_api_client),
    content_json: Optional[Dict] = Depends(get_json),
):
    contact.email.email_id = contact.email.email_id or uuid4()
    email_id = contact.email.email_id
    existing = get_contact_by_email_id(db, email_id)
    if existing:
        email = existing["email"].primary_email
        if re_trace_email.match(email):
            request.state.log_context["trace"] = email
            request.state.log_context["trace_json"] = content_json
        if ContactInSchema(**existing).idempotent_equal(contact):
            response.headers["Location"] = f"/ctms/{email_id}"
            response.status_code = 200
            return get_ctms_response_or_404(db=db, email_id=email_id)
        raise HTTPException(status_code=409, detail="Contact already exists")
    try:
        create_contact(db, email_id, contact, get_metrics())
        schedule_acoustic_record(db, email_id, get_metrics())
        db.commit()
    except Exception as e:  # pylint:disable = W0703
        db.rollback()
        if isinstance(e, IntegrityError):
            raise HTTPException(status_code=409, detail="Contact already exists") from e
        raise e from e
    response.headers["Location"] = f"/ctms/{email_id}"
    response.status_code = 201
    resp_data = get_ctms_response_or_404(db=db, email_id=email_id)
    email = resp_data.email.primary_email
    if re_trace_email.match(email):
        request.state.log_context["trace"] = email
        request.state.log_context["trace_json"] = content_json
    return resp_data


@app.put(
    "/ctms/{email_id}",
    summary="""Create or replace a contact, an email_id must be provided.
               Compare this to POST where we will generate one for you if you want.
               This is intended to be used to send back a contact you have modified locally
               and therefore the input schema is a full Contact.""",
    response_model=CTMSSingleResponse,
    responses={409: {"model": BadRequestResponse}, 422: {"model": BadRequestResponse}},
    tags=["Public"],
)
def create_or_update_ctms_contact(
    contact: ContactPutSchema,
    request: Request,
    response: Response,
    email_id: UUID = Path(..., title="The Email ID"),
    db: Session = Depends(get_db),
    api_client: ApiClientSchema = Depends(get_enabled_api_client),
    content_json: Optional[Dict] = Depends(get_json),
):
    if contact.email.email_id:
        if contact.email.email_id != email_id:
            raise HTTPException(
                status_code=422,
                detail="email_id in path must match email_id in contact",
            )
    else:
        contact.email.email_id = email_id
    email = contact.email.primary_email
    if re_trace_email.match(email):
        request.state.log_context["trace"] = email
        request.state.log_context["trace_json"] = content_json
    try:
        create_or_update_contact(db, email_id, contact, get_metrics())
        schedule_acoustic_record(db, email_id, get_metrics())
        db.commit()
    except Exception as e:  # pylint:disable = W0703
        db.rollback()
        if isinstance(e, IntegrityError):
            raise HTTPException(
                status_code=409,
                detail="Contact with primary_email or basket_token already exists",
            ) from e
        raise e from e
    response.status_code = 201
    return get_ctms_response_or_404(db=db, email_id=email_id)


@app.patch(
    "/ctms/{email_id}",
    summary="""Partially update a contact. Provided data will be updated, and omitted
               data will keep existing values.""",
    response_model=CTMSSingleResponse,
    responses={
        409: {"model": BadRequestResponse},
        404: {"model": NotFoundResponse},
    },
    tags=["Public"],
)
def partial_update_ctms_contact(
    contact: ContactPatchSchema,
    request: Request,
    response: Response,
    email_id: UUID = Path(..., title="The Email ID"),
    db: Session = Depends(get_db),
    api_client: ApiClientSchema = Depends(get_enabled_api_client),
    content_json: Optional[Dict] = Depends(get_json),
):
    if (
        contact.email
        and getattr(contact.email, "email_id")
        and contact.email.email_id != email_id
    ):
        raise HTTPException(
            status_code=422,
            detail="cannot change email_id",
        )
    current_email = get_email_or_404(db, email_id)
    update_data = contact.dict(exclude_unset=True)
    update_contact(db, current_email, update_data, get_metrics())
    email = current_email.primary_email
    if re_trace_email.match(email):
        request.state.log_context["trace"] = email
        request.state.log_context["trace_json"] = content_json
    schedule_acoustic_record(db, email_id, get_metrics())
    try:
        db.commit()
    except Exception as e:  # pylint:disable = W0703
        db.rollback()
        if isinstance(e, IntegrityError):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Contact with primary_email, basket_token, mofo_email_id,"
                    " or fxa_id already exists"
                ),
            ) from e
        raise
    response.status_code = 200
    return get_ctms_response_or_404(db=db, email_id=email_id)


@app.get(
    "/updates",
    summary="Get all contacts within provided timeframe",
    response_model=CTMSBulkResponse,
    responses={
        400: {"model": BadRequestResponse},
        401: {"model": UnauthorizedResponse},
    },
    tags=["Public"],
)
def read_ctms_in_bulk_by_timestamps_and_limit(
    start: datetime,
    end: Optional[Union[datetime, Literal[""]]] = None,
    limit: Optional[Union[int, Literal[""]]] = None,
    after: Optional[str] = None,
    mofo_relevant: Optional[Union[bool, Literal[""]]] = None,
    db: Session = Depends(get_db),
    api_client: ApiClientSchema = Depends(get_enabled_api_client),
):
    try:
        bulk_request = BulkRequestSchema(
            start_time=start,
            end_time=end,
            limit=limit,
            after=after,
            mofo_relevant=mofo_relevant,
        )
        return get_bulk_contacts_by_timestamp_or_4xx(db=db, **bulk_request.dict())
    except ValidationError as e:
        detail = {"errors": e.errors()}
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail
        ) from e


@app.get(
    "/identities",
    summary="Get identities associated with alternate IDs",
    response_model=List[IdentityResponse],
    responses={
        400: {"model": BadRequestResponse},
        401: {"model": UnauthorizedResponse},
    },
    tags=["Private"],
)
def read_identities(
    db: Session = Depends(get_db),
    api_client: ApiClientSchema = Depends(get_enabled_api_client),
    ids=Depends(all_ids),
):
    if not any(ids.values()):
        detail = (
            f"No identifiers provided, at least one is needed: {', '.join(ids.keys())}"
        )
        raise HTTPException(status_code=400, detail=detail)
    contacts = get_contacts_by_ids(db, **ids)
    return [contact.as_identity_response() for contact in contacts]


@app.get(
    "/identity/{email_id}",
    summary="Get identities associated with the ID",
    response_model=IdentityResponse,
    responses={
        401: {"model": UnauthorizedResponse},
        404: {"model": NotFoundResponse},
    },
    tags=["Private"],
)
def read_identity(
    email_id: UUID = Path(..., title="The email ID"),
    db: Session = Depends(get_db),
    api_client: ApiClientSchema = Depends(get_enabled_api_client),
):
    contact = get_contact_or_404(db, email_id)
    return contact.as_identity_response()


@app.post(
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
    token_settings=Depends(_token_settings),
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


@app.get("/__version__", tags=["Platform"])
def version():
    """Return version.json, as required by Dockerflow."""
    return version_info


def heartbeat(request: Request, db: Session, settings: config.Settings):
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


@app.get("/__heartbeat__", tags=["Platform"])
def get_heartbeat(
    request: Request,
    db: Session = Depends(get_db),
    settings: config.Settings = Depends(get_settings),
):
    return heartbeat(request, db, settings)


@app.head("/__heartbeat__", tags=["Platform"])
def head_heartbeat(
    request: Request,
    db: Session = Depends(get_db),
    settings: config.Settings = Depends(get_settings),
):
    return heartbeat(request, db, settings)


def lbheartbeat(request: Request):
    """Return response when application is running, as required by Dockerflow."""
    user_agent = request.headers.get("user-agent", "")
    if user_agent.startswith("kube-probe/"):
        request.state.log_context["trivial_code"] = 200
    return {"status": "OK"}


@app.get("/__lbheartbeat__", tags=["Platform"])
def get_lbheartbeat(request: Request):
    return lbheartbeat(request)


@app.head("/__lbheartbeat__", tags=["Platform"])
def head_lbheartbeat(request: Request):
    return lbheartbeat(request)


@app.get("/__crash__", tags=["Platform"], include_in_schema=False)
def crash(api_client: ApiClientSchema = Depends(get_enabled_api_client)):
    """Raise an exception to test Sentry integration."""
    raise RuntimeError("Test exception handling")


@app.get("/metrics", tags=["Platform"])
def metrics(request: Request):
    """Return Prometheus metrics"""
    agent = request.headers.get("user-agent", "")
    if agent.startswith("Prometheus/"):
        request.state.log_context["trivial_code"] = 200
    headers = {"Content-Type": CONTENT_TYPE_LATEST}
    registry = get_metrics_registry()
    return Response(generate_latest(registry), status_code=200, headers=headers)


@app.get("/acoustic_configuration", tags=["Platform"])
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


def _process_stripe_object(
    db_session: Session, data: Dict
) -> Tuple[Optional[UUID], Optional[str], Optional[str], StripeIngestActions]:
    """
    Ingest a Stripe Object and extract related data.

    If a Stripe customer has an FxA ID that matches a current (but different)
    customer, then the existing customer is deleted. This matches the FxA
    Firestore cache of Stripe customers, which index by FxA ID. This has
    occured occasionally in stage, due to bugs or manual interaction with the
    Stripe API.

    Return is a tuple:
    - email_id - The related Contact email_id, or None if no contact.
    - trace_email - The email to trace, or None if not Customer or doesn't match
    - fxa_conflict - The FxA ID if there was a collision, otherwise None
    - actions - The actions taken by the Stripe ingesters

    Raises:
    - StripeIngestBadObjectError if the data isn't a Stripe object
    - StripeIngestUnknownObjectError if the data is an unhandled Stripe object
    - Other errors (ValueError, KeyError) if the Stripe object has unexpected
      data for keys that CTMS examines. Extra data is ignored.
    """
    fxa_conflict = None
    try:
        obj, actions = ingest_stripe_object(db_session, data)
    except StripeIngestFxAIdConflict as e:
        # Delete the existing Stripe customer with that FxA ID
        stripe_id = e.stripe_id
        fxa_conflict = e.fxa_id
        stmt = (
            delete(StripeCustomer)
            .where(StripeCustomer.stripe_id == stripe_id)
            .execution_options(synchronize_session="evaluate")
        )
        db_session.execute(stmt)

        obj, actions = ingest_stripe_object(db_session, data)
        actions.setdefault("deleted", set()).add(f"customer:{stripe_id}")

    try:
        db_session.commit()
    except IntegrityError as e:
        db_session.rollback()
        structlog.get_logger("ctms.web").exception("IntegrityError converted to 409")
        raise HTTPException(status_code=409, detail="Write conflict, try again") from e
    except OperationalError as e:
        db_session.rollback()
        structlog.get_logger("ctms.web").exception("OperationalError converted to 409")
        raise HTTPException(
            status_code=409, detail="Deadlock or other issue, try again"
        ) from e

    email_id = obj.get_email_id() if obj else None
    if data["object"] == "customer" and re_trace_email.match(data.get("email", "")):
        trace_email = data["email"]
    else:
        trace_email = None
    return email_id, trace_email, fxa_conflict, actions


@app.post(
    "/stripe",
    summary="Add or update Stripe data",
    tags=["Public"],
)
def stripe(
    request: Request,
    db_session: Session = Depends(get_db),
    api_client: ApiClientSchema = Depends(get_enabled_api_client),
    data: Optional[Dict] = Depends(get_json),
):
    if not ("object" in data and "id" in data):
        raise HTTPException(status_code=400, detail="Request JSON is not recognized.")
    try:
        email_id, trace_email, fxa_conflict, actions = _process_stripe_object(
            db_session, data
        )
    except (KeyError, ValueError, TypeError) as exception:
        raise HTTPException(
            400, detail="Unable to process Stripe object."
        ) from exception
    if email_id:
        schedule_acoustic_record(db_session, email_id, get_metrics())
        db_session.commit()
    if trace_email:
        request.state.log_context["trace"] = trace_email
        request.state.log_context["trace_json"] = data
    if fxa_conflict:
        request.state.log_context["fxa_id_conflict"] = fxa_conflict
    if actions:
        ingest_actions = {}
        for key in sorted(actions.keys()):
            ingest_actions[key] = sorted(actions[key])
        request.state.log_context["ingest_actions"] = ingest_actions

    return {"status": "OK"}


@app.post(
    "/stripe_from_pubsub",
    summary="Add or update Stripe data from PubSub",
    tags=["Private"],
)
def stripe_pubsub(
    request: Request,
    db_session: Session = Depends(get_db),
    pubsub_claim=Depends(get_pubsub_claim),
    wrapped_data: Optional[Dict] = Depends(get_json),
):
    if not ("message" in wrapped_data and "subscription" in wrapped_data):
        content = {
            "status": "Accepted but not processed",
            "message": "Message does not appear to be from pubsub, do not send again.",
        }
        return JSONResponse(content=content, status_code=202)

    payload = json.loads(b64decode(wrapped_data["message"]["data"]).decode())
    if hasattr(payload, "keys"):
        if all(key.count(":") == 1 for key in payload.keys()):
            # Item dictionary, "firebase_table:id" -> Stripe object
            items = []
            for key, value in payload.items():
                if value:
                    items.append(value)
                else:
                    structlog.get_logger("ctms.web").warning(
                        f"PubSub key {key} had empty value {value}"
                    )
        else:
            items = [payload]  # One Stripe object, or maybe unknown dictionary
    else:
        content = {
            "status": "Accepted but not processed",
            "message": "Unknown payload type, do not send again.",
        }
        return JSONResponse(content=content, status_code=202)

    email_ids = set()
    fxa_conflicts = set()
    trace = None
    has_error = False
    count = 0
    actions: StripeIngestActions = {}
    for item in items:
        try:
            email_id, trace_email, fxa_conflict, item_actions = _process_stripe_object(
                db_session, item
            )
        except StripeIngestUnknownObjectError as exception:
            actions.setdefault("skipped", set()).add(
                f"{exception.object_value}:{exception.object_id}"
            )
        except (KeyError, ValueError, TypeError) as exception:
            sentry_sdk.capture_exception(exception)
            has_error = True
        else:
            count += 1
            if email_id:
                email_ids.add(email_id)
            if trace_email:
                trace = trace_email
            if fxa_conflict:
                fxa_conflicts.add(fxa_conflict)
            for key, values in item_actions.items():
                actions.setdefault(key, set()).update(values)

    if email_ids:
        for email_id in email_ids:
            schedule_acoustic_record(db_session, email_id, get_metrics())
        db_session.commit()
    if trace:
        request.state.log_context["trace"] = trace
        request.state.log_context["trace_json"] = payload
    if fxa_conflicts:
        request.state.log_context["fxa_id_conflict"] = ",".join(sorted(fxa_conflicts))
    if actions:
        ingest_actions = {}
        for key in sorted(actions.keys()):
            ingest_actions[key] = sorted(actions[key])
        request.state.log_context["ingest_actions"] = ingest_actions

    if has_error:
        content = {
            "status": "Accepted but not processed",
            "message": "Errors processing the data, do not send again.",
        }
        return JSONResponse(content=content, status_code=202)
    return {"status": "OK", "count": count}


@app.delete(
    "/ctms/gdpr/{email}",
    tags=["Public"],
    summary="delete email from database",
    responses={
        404: {"model": NotFoundResponse},
    },
    response_model=GDPRDeleteResponse,
)
def gdpr_delete_email(
    email: str,
    db: Session = Depends(get_db),
    api_client: ApiClientSchema = Depends(get_enabled_api_client),
):
    email_to_find = email.lower()
    ids = all_ids(primary_email=email_to_find)
    contacts = get_contacts_by_ids(db, **ids)

    if not contacts:
        raise HTTPException(status_code=404, detail=f"email {email} not found!")

    dropped = list()

    for contact in contacts:
        gdpr_delete(db=db, email_id=contact.email.email_id)

        dropped.append(
            {
                "primary_email": contact.email.primary_email,
                "email_id": str(contact.email.email_id),
            }
        )

    return GDPRDeleteResponse(status="ok", dropped=dropped)


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=80, reload=True)
