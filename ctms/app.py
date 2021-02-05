from datetime import datetime
from typing import Dict
from uuid import UUID

import uvicorn
from fastapi import FastAPI, HTTPException, Path
from fastapi.responses import RedirectResponse
from pydantic import EmailStr

from .sample_data import SAMPLE_CONTACTS
from .schemas import (
    AddOnsSchema,
    ContactFirefoxPrivateNetworkSchema,
    ContactSchema,
    CTMSResponse,
    EmailSchema,
    FirefoxAccountsSchema,
    IdentityResponse,
    NotFoundResponse,
)

app = FastAPI(
    title="ConTact Management System (CTMS)",
    description="CTMS API (work in progress)",
    version="0.4.0",
)


def get_contact_or_404(email_id) -> ContactSchema:
    """
    Get a contact by email_ID, or raise a 404 exception.

    TODO: implement a database backend
    """
    try:
        return SAMPLE_CONTACTS[email_id]
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown email_id")


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
def read_ctms(email_id: UUID = Path(..., title="The Email ID")):
    contact = get_contact_or_404(email_id)
    return CTMSResponse(
        amo=contact.amo or AddOnsSchema(),
        email=contact.email or EmailSchema(),
        fpn=contact.fpn or ContactFirefoxPrivateNetworkSchema(),
        fxa=contact.fxa or FirefoxAccountsSchema(),
        newsletters=contact.newsletters or [],
        status="ok",
    )


@app.get(
    "/identity/{email_id}",
    summary="Get identities associated with the ID",
    response_model=IdentityResponse,
    responses={404: {"model": NotFoundResponse}},
    tags=["Private"],
)
def read_identity(email_id: UUID = Path(..., title="The email ID")):
    contact = get_contact_or_404(email_id)
    return contact.as_identity_response()


@app.get(
    "/contact/email/{email_id}",
    summary="Get contact's main details",
    response_model=EmailSchema,
    responses={404: {"model": NotFoundResponse}},
    tags=["Private"],
)
def read_contact_main(email_id: UUID = Path(..., title="The email ID")):
    contact = get_contact_or_404(email_id)
    return contact.email or EmailSchema()


@app.get(
    "/contact/amo/{email_id}",
    summary="Get contact's add-ons details",
    response_model=AddOnsSchema,
    responses={404: {"model": NotFoundResponse}},
    tags=["Private"],
)
def read_contact_amo(email_id: UUID = Path(..., title="The email ID")):
    contact = get_contact_or_404(email_id)
    return contact.amo or AddOnsSchema()


@app.get(
    "/contact/fpn/{email_id}",
    summary="Get contact's Firefox Private Network details",
    response_model=ContactFirefoxPrivateNetworkSchema,
    responses={404: {"model": NotFoundResponse}},
    tags=["Private"],
)
def read_contact_fpn(email_id: UUID = Path(..., title="The email ID")):
    contact = get_contact_or_404(email_id)
    return contact.fpn or ContactFirefoxPrivateNetworkSchema()


@app.get(
    "/contact/fxa/{email_id}",
    summary="Get contact's Firefox Account details",
    response_model=FirefoxAccountsSchema,
    responses={404: {"model": NotFoundResponse}},
    tags=["Private"],
)
def read_contact_fxa(email_id: UUID = Path(..., title="The email ID")):
    contact = get_contact_or_404(email_id)
    return contact.fxa or FirefoxAccountsSchema()


# NOTE:  This endpoint should provide a better proxy of "health".  It presently is a
# better proxy for application availability as opposed to health.
@app.get("/health", tags=["Platform"])
def health():
    return {"health": "OK"}, 200


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=80, reload=True)
