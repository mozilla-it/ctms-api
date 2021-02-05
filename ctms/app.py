from datetime import datetime
from typing import Dict
from uuid import UUID

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Path
from fastapi.responses import RedirectResponse
from pydantic import EmailStr
from sqlalchemy.orm import Session

from .crud import get_contact_by_email_id
from .db import SessionLocal, engine
from .models import Base as ModelBase
from .schemas import (
    ContactAddonsSchema,
    ContactFirefoxAccountsSchema,
    ContactFirefoxPrivateNetworkSchema,
    ContactSchema,
    CTMSResponse,
    EmailSchema,
    IdentityResponse,
    NotFoundResponse,
)

ModelBase.metadata.create_all(bind=engine)

app = FastAPI(
    title="ConTact Management System (CTMS)",
    description="CTMS API (work in progress)",
    version="0.4.0",
)


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
    contact = get_contact_by_email_id(db, email_id)
    if contact is None:
        raise HTTPException(status_code=404, detail="Unknown email_id")
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
    return get_contact_or_404(db, email_id)


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
    return get_contact_or_404(db, email_id)


@app.get(
    "/contact/amo/{email_id}",
    summary="Get contact's add-ons details",
    response_model=ContactAddonsSchema,
    responses={404: {"model": NotFoundResponse}},
    tags=["Private"],
)
def read_contact_amo(
    email_id: UUID = Path(..., title="The email ID"), db: Session = Depends(get_db)
):
    contact = get_contact_or_404(db, email_id)
    return contact.amo or ContactAddonsSchema()


@app.get(
    "/contact/fpn/{email_id}",
    summary="Get contact's Firefox Private Network details",
    response_model=ContactFirefoxPrivateNetworkSchema,
    responses={404: {"model": NotFoundResponse}},
    tags=["Private"],
)
def read_contact_fpn(
    email_id: UUID = Path(..., title="The email ID"), db: Session = Depends(get_db)
):
    contact = get_contact_or_404(db, email_id)
    return contact.fpn or ContactFirefoxPrivateNetworkSchema()


@app.get(
    "/contact/fxa/{email_id}",
    summary="Get contact's Firefox Account details",
    response_model=ContactFirefoxAccountsSchema,
    responses={404: {"model": NotFoundResponse}},
    tags=["Private"],
)
def read_contact_fxa(
    email_id: UUID = Path(..., title="The email ID"), db: Session = Depends(get_db)
):
    contact = get_contact_or_404(db, email_id)
    return contact.fxa or ContactFirefoxAccountsSchema()


# NOTE:  This endpoint should provide a better proxy of "health".  It presently is a
# better proxy for application availability as opposed to health.
@app.get("/health", tags=["Platform"])
def health():
    return {"health": "OK"}, 200


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=80, reload=True)
