from datetime import timedelta
from functools import lru_cache
from typing import Dict, List, Optional, Union
from uuid import UUID, uuid4

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Path, Response
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import EmailStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

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
    get_contact_by_email_id,
    get_email,
    get_emails_by_any_id,
    update_contact,
)
from .database import get_db_engine
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
    version="0.5.0",
)
SessionLocal = None
oauth2_scheme = OAuth2ClientCredentials(tokenUrl="token")
token_scheme = HTTPBasic(auto_error=False)


@lru_cache()
def get_settings():
    return config.Settings()


@app.on_event("startup")
def startup_event():
    global SessionLocal  # pylint:disable = W0603
    _, session_factory = get_db_engine(get_settings())
    SessionLocal = scoped_session(session_factory)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        SessionLocal.remove()


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
    primary_email: Optional[EmailStr] = None,
    basket_token: Optional[UUID] = None,
    sfdc_id: Optional[str] = None,
    mofo_contact_id: Optional[str] = None,
    mofo_email_id: Optional[str] = None,
    amo_user_id: Optional[str] = None,
    fxa_id: Optional[str] = None,
    fxa_primary_email: Optional[EmailStr] = None,
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
    primary_email: Optional[EmailStr] = None,
    basket_token: Optional[UUID] = None,
    sfdc_id: Optional[str] = None,
    mofo_contact_id: Optional[str] = None,
    mofo_email_id: Optional[str] = None,
    amo_user_id: Optional[str] = None,
    fxa_id: Optional[str] = None,
    fxa_primary_email: Optional[EmailStr] = None,
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


def get_api_client(
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
    if name is None:
        raise credentials_exception
    if namespace != "api_client":
        raise credentials_exception
    api_client = get_api_client_by_id(db, name)
    if not api_client:
        raise credentials_exception
    return api_client


def get_enabled_api_client(api_client: ApiClientSchema = Depends(get_api_client)):
    if not api_client.enabled:
        raise HTTPException(status_code=400, detail="API Client has been disabled")
    return api_client


@app.get("/", include_in_schema=False)
def root():
    """GET via root redirects to /docs.

    - Args:

    - Returns:
        - **redirect**: Redirects call to ./docs
    """

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
    responses={409: {"model": BadRequestResponse}},
    tags=["Public"],
)
def create_ctms_contact(
    contact: ContactInSchema,
    db: Session = Depends(get_db),
    api_client: ApiClientSchema = Depends(get_enabled_api_client),
):
    contact.email.email_id = contact.email.email_id or uuid4()
    email_id = contact.email.email_id
    existing = get_contact_by_email_id(db, email_id)
    if existing:
        if ContactInSchema(**existing).idempotent_equal(contact):
            return RedirectResponse(status_code=303, url=f"/ctms/{email_id}")
        raise HTTPException(status_code=409, detail="Contact already exists")
    try:
        create_contact(db, email_id, contact)
        db.commit()
    except Exception as e:  # pylint:disable = W0703
        db.rollback()
        if isinstance(e, IntegrityError):
            raise HTTPException(status_code=409, detail="Contact already exists") from e
        raise e from e
    return RedirectResponse(status_code=303, url=f"/ctms/{email_id}")


@app.put(
    "/ctms/{email_id}",
    summary="""Create or replace a contact, an email_id must be provided.
               Compare this to POST where we will generate one for you if you want.
               This is intended to be used to send back a contact you have modified locally
               and therefore the input schema is a full Contact.""",
    responses={409: {"model": BadRequestResponse}, 422: {"model": BadRequestResponse}},
    tags=["Public"],
)
def create_or_update_ctms_contact(
    contact: ContactPutSchema,
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
        db.commit()
    except Exception as e:  # pylint:disable = W0703
        db.rollback()
        if isinstance(e, IntegrityError):
            raise HTTPException(
                status_code=409,
                detail="Contact with primary_email or basket_token already exists",
            ) from e
        raise e from e
    return RedirectResponse(status_code=303, url=f"/ctms/{email_id}")


@app.patch(
    "/ctms/{email_id}",
    summary="""Partially update a contact. Provided data will be updated, and omitted
               data will keep existing values.""",
    responses={
        409: {"model": BadRequestResponse},
        404: {"model": NotFoundResponse},
    },
    tags=["Public"],
)
def partial_update_ctms_contact(
    contact: ContactPatchSchema,
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
    db.commit()
    return RedirectResponse(status_code=303, url=f"/ctms/{email_id}")


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
    db: Session = Depends(get_db),
    form_data: OAuth2ClientCredentialsRequestForm = Depends(),
    basic_credentials: Optional[HTTPBasicCredentials] = Depends(token_scheme),
    token_settings=Depends(_token_settings),
):
    failed_auth = HTTPException(
        status_code=400, detail="Incorrect username or password"
    )

    if form_data.client_id and form_data.client_secret:
        client_id = form_data.client_id
        client_secret = form_data.client_secret
    elif basic_credentials:
        client_id = basic_credentials.username
        client_secret = basic_credentials.password
    else:
        raise failed_auth

    api_client = get_api_client_by_id(db, client_id)
    if not api_client or not api_client.enabled:
        raise failed_auth
    if not verify_password(client_secret, api_client.hashed_secret):
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


@app.get("/__heartbeat__", tags=["Platform"])
def heartbeat(response: Response, db: Session = Depends(get_db)):
    """Return status of backing services, as required by Dockerflow."""
    data = {"database": check_database(db)}
    if not data["database"]["up"]:
        response.status_code = 503
    return data


@app.get("/__lbheartbeat__", tags=["Platform"])
def lbheartbeat():
    """Return response when application is running, as required by Dockerflow."""
    return {"status": "OK"}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=80, reload=True)
