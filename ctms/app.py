from datetime import datetime
from functools import lru_cache
from typing import Dict, List, Optional
from uuid import UUID

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Path
from fastapi.responses import RedirectResponse
from pydantic import EmailStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import config
from .crud import get_email_by_email_id
from .database import get_db_engine
from .models import Base as ModelBase
from .sample_data import SAMPLE_CONTACTS
from .schemas import (
    AddOnsSchema,
    BadRequestResponse,
    ContactSchema,
    CTMSResponse,
    EmailSchema,
    FirefoxAccountsSchema,
    IdentityResponse,
    NotFoundResponse,
    VpnWaitlistSchema,
)

app = FastAPI(
    title="ConTact Management System (CTMS)",
    description="CTMS API (work in progress)",
    version="0.5.0",
)
SessionLocal = None
TestSessionLocal = None


@lru_cache()
def get_settings():
    return config.Settings()


@app.on_event("startup")
def startup_event():
    global SessionLocal
    engine, SessionLocal = get_db_engine(get_settings())


def set_test_session(test_session):
    """Set the database session for tests."""
    global TestSessionLocal
    TestSessionLocal = test_session


def get_db():
    if TestSessionLocal:
        db = TestSessionLocal()
    else:
        db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_contact_or_404(db: Session, email_id) -> ContactSchema:
    """
    Get a contact by email_ID, or raise a 404 exception.

    """
    contact = SAMPLE_CONTACTS.get(email_id)
    if contact is None:
        raise HTTPException(status_code=404, detail="Unknown email_id")
    contact.email = EmailSchema.from_orm(get_email_by_email_id(db, email_id))
    return contact


def all_ids(
    email_id: Optional[UUID] = None,
    primary_email: Optional[EmailStr] = None,
    basket_token: Optional[UUID] = None,
    sfdc_id: Optional[str] = None,
    mofo_id: Optional[str] = None,
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
        "mofo_id": mofo_id,
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
    mofo_id: Optional[str] = None,
    amo_user_id: Optional[str] = None,
    fxa_id: Optional[str] = None,
    fxa_primary_email: Optional[EmailStr] = None,
) -> List[ContactSchema]:
    """Get contacts by any ID.

    Callers are expected to set just one ID, but if multiple are set, a contact
    must match all IDs.
    """
    assert any(
        (
            email_id,
            primary_email,
            basket_token,
            sfdc_id,
            mofo_id,
            amo_user_id,
            fxa_id,
            fxa_primary_email,
        )
    )

    # TODO: Replace with database query
    contacts = []
    for contact_email_id, contact in SAMPLE_CONTACTS.items():
        if (
            (email_id is None or contact.email.email_id == email_id)
            and (primary_email is None or contact.email.primary_email == primary_email)
            and (basket_token is None or contact.email.basket_token == basket_token)
            and (sfdc_id is None or contact.email.sfdc_id == sfdc_id)
            and (mofo_id is None or contact.email.mofo_id == mofo_id)
            and (
                amo_user_id is None
                or bool(contact.amo and contact.amo.user_id == amo_user_id)
            )
            and (fxa_id is None or bool(contact.fxa and contact.fxa.fxa_id == fxa_id))
            and (
                fxa_primary_email is None
                or bool(contact.fxa and contact.fxa.primary_email == fxa_primary_email)
            )
        ):
            contact.email = EmailSchema.from_orm(
                get_email_by_email_id(db, contact_email_id)
            )
            contacts.append(contact)

    return contacts


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
    response_model=List[ContactSchema],
    responses={400: {"model": BadRequestResponse}},
    tags=["Public"],
)
def read_ctms_by_any_id(db: Session = Depends(get_db), ids=Depends(all_ids)):
    if not any(ids.values()):
        detail = (
            f"No identifiers provided, at least one is needed: {', '.join(ids.keys())}"
        )
        raise HTTPException(status_code=400, detail=detail)
    contacts = get_contacts_by_ids(db, **ids)
    return [
        ContactSchema(
            amo=contact.amo or AddOnsSchema(),
            email=contact.email or EmailSchema(),
            fxa=contact.fxa or FirefoxAccountsSchema(),
            newsletters=contact.newsletters or [],
            vpn_waitlist=contact.vpn_waitlist or VpnWaitlistSchema(),
        )
        for contact in contacts
    ]


@app.get(
    "/ctms/{email_id}",
    summary="Get a contact by email_id",
    response_model=CTMSResponse,
    responses={404: {"model": NotFoundResponse}},
    tags=["Public"],
)
def read_ctms_by_email_id(
    email_id: UUID = Path(..., title="The Email ID"), db: Session = Depends(get_db)
):
    contact = get_contact_or_404(db, email_id)
    return CTMSResponse(
        amo=contact.amo or AddOnsSchema(),
        email=contact.email or EmailSchema(),
        fxa=contact.fxa or FirefoxAccountsSchema(),
        newsletters=contact.newsletters or [],
        vpn_waitlist=contact.vpn_waitlist or VpnWaitlistSchema(),
        status="ok",
    )


@app.get(
    "/identities",
    summary="Get identities associated with alternate IDs",
    response_model=List[IdentityResponse],
    responses={400: {"model": BadRequestResponse}},
    tags=["Private"],
)
def read_identities(db: Session = Depends(get_db), ids=Depends(all_ids)):
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
    responses={404: {"model": NotFoundResponse}},
    tags=["Private"],
)
def read_identity(
    email_id: UUID = Path(..., title="The email ID"), db: Session = Depends(get_db)
):
    contact = get_contact_or_404(db, email_id)
    return contact.as_identity_response()


@app.get(
    "/contact/email/{email_id}",
    summary="Get contact's main details",
    response_model=EmailSchema,
    responses={404: {"model": NotFoundResponse}},
    tags=["Private"],
)
def read_contact_main(
    email_id: UUID = Path(..., title="The email ID"), db: Session = Depends(get_db)
):
    contact = get_contact_or_404(db, email_id)
    return contact.email


@app.get(
    "/contact/amo/{email_id}",
    summary="Get contact's add-ons details",
    response_model=AddOnsSchema,
    responses={404: {"model": NotFoundResponse}},
    tags=["Private"],
)
def read_contact_amo(
    email_id: UUID = Path(..., title="The email ID"), db: Session = Depends(get_db)
):
    contact = get_contact_or_404(db, email_id)
    return contact.amo or AddOnsSchema()


@app.get(
    "/contact/vpn_waitlist/{email_id}",
    summary="Get contact's Mozilla VPN Waitlist details",
    response_model=VpnWaitlistSchema,
    responses={404: {"model": NotFoundResponse}},
    tags=["Private"],
)
def read_contact_fpn(
    email_id: UUID = Path(..., title="The email ID"), db: Session = Depends(get_db)
):
    contact = get_contact_or_404(db, email_id)
    return contact.vpn_waitlist or VpnWaitlistSchema()


@app.get(
    "/contact/fxa/{email_id}",
    summary="Get contact's Firefox Account details",
    response_model=FirefoxAccountsSchema,
    responses={404: {"model": NotFoundResponse}},
    tags=["Private"],
)
def read_contact_fxa(
    email_id: UUID = Path(..., title="The email ID"), db: Session = Depends(get_db)
):
    contact = get_contact_or_404(db, email_id)
    return contact.fxa or FirefoxAccountsSchema()


# NOTE:  This endpoint should provide a better proxy of "health".  It presently is a
# better proxy for application availability as opposed to health.
@app.get("/health", tags=["Platform"])
def health():
    return {"health": "OK"}, 200


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=80, reload=True)
