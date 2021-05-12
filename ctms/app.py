import base64
import sys
import time
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid4

import dateutil.parser
import sentry_sdk
import structlog
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Path, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import ValidationError
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from sentry_sdk.integrations.logging import ignore_logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import config
from .auth import (
    OAuth2ClientCredentials,
    OAuth2ClientCredentialsRequestForm,
    create_access_token,
    get_subject_from_token,
    verify_password,
)
from .crud import (
    create_contact,
    create_or_update_contact,
    get_api_client_by_id,
    get_bulk_contacts,
    get_contact_by_email_id,
    get_email,
    get_emails_by_any_id,
    schedule_acoustic_record,
    update_contact,
)
from .database import get_db_engine
from .log import configure_logging, context_from_request, get_log_line
from .metrics import (
    emit_response_metrics,
    init_metrics,
    init_metrics_labels,
    init_metrics_registry,
)
from .models import Email
from .monitor import check_database, get_version
from .schemas import (
    AddOnsSchema,
    ApiClientSchema,
    BadRequestResponse,
    ContactInSchema,
    ContactPatchSchema,
    ContactPutSchema,
    ContactSchema,
    CTMSBulkResponse,
    CTMSResponse,
    CTMSSingleResponse,
    EmailSchema,
    FirefoxAccountsSchema,
    IdentityResponse,
    MozillaFoundationSchema,
    NotFoundResponse,
    TokenResponse,
    UnauthorizedResponse,
    VpnWaitlistSchema,
)

app = FastAPI(
    title="ConTact Management System (CTMS)",
    description="CTMS API (work in progress)",
    version="0.7.2",
)
SessionLocal = None
METRICS_REGISTRY = None
METRICS = None
get_metrics_registry = lambda: METRICS_REGISTRY
get_metrics = lambda: METRICS
oauth2_scheme = OAuth2ClientCredentials(tokenUrl="token")
token_scheme = HTTPBasic(auto_error=False)


@lru_cache()
def get_settings():
    return config.Settings()


def init_sentry():
    """
    Initialize Sentry integrations for capturing exceptions.

    Because FastAPI uses threads to integrate async and sync code, this needs
    to be called at module import.

    sentry_sdk.init needs a data source name (DSN) URL, which it reads from the
    environment variable SENTRY_DSN.
    """
    try:
        settings = get_settings()
    except ValidationError:
        sentry_debug = False
    else:
        sentry_debug = settings.sentry_debug

    # pylint: disable=abstract-class-instantiated
    sentry_sdk.init(
        release=get_version().get("commit", None),
        debug=sentry_debug,
        send_default_pii=False,
    )
    ignore_logger("uvicorn.error")
    ignore_logger("ctms.web")


# Initialize Sentry / Metrics for each thread, unless we're in tests
if "pytest" not in sys.argv[0]:
    init_sentry()
    app.add_middleware(SentryAsgiMiddleware)
    METRICS_REGISTRY = init_metrics_registry()


@app.on_event("startup")
def startup_event():
    global SessionLocal, METRICS  # pylint:disable = W0603
    settings = get_settings()
    configure_logging(settings.use_mozlog, settings.logging_level)
    _, SessionLocal = get_db_engine(get_settings())
    METRICS = init_metrics(METRICS_REGISTRY)
    init_metrics_labels(SessionLocal(), app, METRICS)


def get_db():
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
        vpn_waitlist=email.vpn_waitlist,
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
            vpn_waitlist=email.vpn_waitlist,
        )
        for email in rows
    ]


def extractor_for_bulk_encoded_details(after: str) -> Tuple[str, datetime]:
    str_decode = base64.urlsafe_b64decode(after)
    result_after_list = str(str_decode.decode("utf-8")).split(",")
    after_email_id = result_after_list[0]
    after_start_time = dateutil.parser.parse(result_after_list[1])
    return after_email_id, after_start_time


def compressor_for_bulk_encoded_details(last_result: CTMSResponse):
    last_email_id = last_result.email.email_id
    last_update_time = last_result.email.update_timestamp
    result_after_encoded = base64.urlsafe_b64encode(
        f"{last_email_id},{last_update_time}".encode("utf-8")
    )
    return result_after_encoded.decode()


def get_bulk_contacts_by_timestamp(
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
        after_email_id, after_start_time = extractor_for_bulk_encoded_details(
            after=after
        )

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
                vpn_waitlist=contact.vpn_waitlist or VpnWaitlistSchema(),
            )
            for contact in results
        ]

    if last_page:
        # No results/end
        after_encoded = None
        next_url = None
    else:
        last_result: CTMSResponse = results[-1]
        after_encoded = compressor_for_bulk_encoded_details(last_result)
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


def updates_helper(value, default):
    blank_vals = ["", None]
    if value in blank_vals:
        return default
    return value


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


@app.middleware("http")
async def log_request_middleware(request: Request, call_next):
    """Add timing and per-request logging context."""
    start_time = time.monotonic()
    request.state.log_context = context_from_request(request)
    has_error = False

    try:
        response = await call_next(request)
    except Exception as e:
        has_error = True
        raise e from None
    finally:
        if has_error:
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
        if has_error:
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
    return [
        CTMSResponse(
            amo=contact.amo or AddOnsSchema(),
            email=contact.email or EmailSchema(),
            fxa=contact.fxa or FirefoxAccountsSchema(),
            mofo=contact.mofo or MozillaFoundationSchema(),
            newsletters=contact.newsletters or [],
            vpn_waitlist=contact.vpn_waitlist or VpnWaitlistSchema(),
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
    email_id: UUID = Path(..., title="The Email ID"),
    db: Session = Depends(get_db),
    api_client: ApiClientSchema = Depends(get_enabled_api_client),
):
    return get_ctms_response_or_404(db, email_id)


def get_ctms_response_or_404(db, email_id):
    contact = get_contact_or_404(db, email_id)
    return CTMSSingleResponse(
        amo=contact.amo or AddOnsSchema(),
        email=contact.email or EmailSchema(),
        fxa=contact.fxa or FirefoxAccountsSchema(),
        mofo=contact.mofo or MozillaFoundationSchema(),
        newsletters=contact.newsletters or [],
        vpn_waitlist=contact.vpn_waitlist or VpnWaitlistSchema(),
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
    response: Response,
    db: Session = Depends(get_db),
    api_client: ApiClientSchema = Depends(get_enabled_api_client),
):
    contact.email.email_id = contact.email.email_id or uuid4()
    email_id = contact.email.email_id
    existing = get_contact_by_email_id(db, email_id)
    if existing:
        if ContactInSchema(**existing).idempotent_equal(contact):
            response.headers["Location"] = f"/ctms/{email_id}"
            response.status_code = 200
            return get_ctms_response_or_404(db=db, email_id=email_id)
        raise HTTPException(status_code=409, detail="Contact already exists")
    try:
        create_contact(db, email_id, contact)
        schedule_acoustic_record(db, email_id)
        db.commit()
    except Exception as e:  # pylint:disable = W0703
        db.rollback()
        if isinstance(e, IntegrityError):
            raise HTTPException(status_code=409, detail="Contact already exists") from e
        raise e from e
    response.headers["Location"] = f"/ctms/{email_id}"
    response.status_code = 201
    return get_ctms_response_or_404(db=db, email_id=email_id)


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
    response: Response,
    email_id: UUID = Path(..., title="The Email ID"),
    db: Session = Depends(get_db),
    api_client: ApiClientSchema = Depends(get_enabled_api_client),
):
    if contact.email.email_id:
        if contact.email.email_id != email_id:
            raise HTTPException(
                status_code=422,
                detail="email_id in path must match email_id in contact",
            )
    else:
        contact.email.email_id = email_id
    try:
        create_or_update_contact(db, email_id, contact)
        schedule_acoustic_record(db, email_id)
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
    response: Response,
    email_id: UUID = Path(..., title="The Email ID"),
    db: Session = Depends(get_db),
    api_client: ApiClientSchema = Depends(get_enabled_api_client),
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
    update_contact(db, current_email, update_data)
    schedule_acoustic_record(db, email_id)
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
    end: Optional[Union[datetime, str]] = None,
    limit: Optional[Union[int, str]] = None,
    after: Optional[str] = None,
    mofo_relevant: Optional[Union[bool, str]] = None,
    db: Session = Depends(get_db),
    api_client: ApiClientSchema = Depends(get_enabled_api_client),
):
    after_param = updates_helper(value=after, default=None)
    limit_param = updates_helper(value=limit, default=10)
    end_param = updates_helper(value=end, default=datetime.now(timezone.utc))
    mofo_relevant_param = updates_helper(value=mofo_relevant, default=None)
    return get_bulk_contacts_by_timestamp(
        db=db,
        start_time=start,
        end_time=end_param,
        after=after_param,
        limit=limit_param,
        mofo_relevant=mofo_relevant_param,
    )


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
    return get_version()


def heartbeat(request: Request, response: Response, db: Session):
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
    data = {"database": check_database(db)}
    if not data["database"]["up"]:
        response.status_code = 503
    return data


@app.get("/__heartbeat__", tags=["Platform"])
def get_heartbeat(request: Request, response: Response, db: Session = Depends(get_db)):
    return heartbeat(request, response, db)


@app.head("/__heartbeat__", tags=["Platform"])
def head_heartbeat(request: Request, response: Response, db: Session = Depends(get_db)):
    return heartbeat(request, response, db)


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
    return Response(
        generate_latest(get_metrics_registry()), status_code=200, headers=headers
    )


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=80, reload=True)
