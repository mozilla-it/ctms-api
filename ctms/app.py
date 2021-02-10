from datetime import datetime
from typing import Dict
from uuid import UUID

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Path
from fastapi.responses import RedirectResponse
from pydantic import EmailStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .crud import create_email, get_email_by_email_id
from .database import SessionLocal, engine
from .models import Base as ModelBase
from .sample_data import SAMPLE_CONTACTS
from .schemas import (
    AddOnsSchema,
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
    version="0.4.0",
)


### TODO: temporary until we have migrations, etc ###
ModelBase.metadata.drop_all(bind=engine)
ModelBase.metadata.create_all(bind=engine)

for contact in SAMPLE_CONTACTS.values():
    if not contact.email:
        raise Exception("SAMPLE_CONTACTS must all include emails")
    try:
        create_email(SessionLocal(), contact.email)
    except IntegrityError:
        print("Demo data already loaded")
#####################################################


def get_db():
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


@app.get("/", include_in_schema=False)
def root():
    """GET via root redirects to /docs.

    - Args:

    - Returns:
        - **redirect**: Redirects call to ./docs
    """

    return RedirectResponse(url="./docs")


@app.get(
    "/ctms/{email_id}",
    summary="Get all contact details in basket format",
    response_model=CTMSResponse,
    responses={404: {"model": NotFoundResponse}},
    tags=["Public"],
)
def read_ctms(
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
