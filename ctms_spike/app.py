from datetime import datetime
from typing import Dict
from uuid import UUID

import uvicorn
from fastapi import FastAPI, HTTPException, Path
from fastapi.responses import RedirectResponse
from pydantic import EmailStr

from ctms_spike.models import (
    ContactAmoSchema,
    ContactCVSchema,
    ContactFpnSchema,
    ContactFsaSchema,
    ContactFxaSchema,
    ContactMainSchema,
    ContactSchema,
    CTMSResponse,
    IdentityResponse,
)

app = FastAPI(
    title="Contact Management System (CTMS)",
    description="Spike of CTMS API for task 185.",
    version="0.0.1",
)


@app.get("/")
async def root():
    """GET via root redirects to /docs.

    - Args:

    - Returns:
        - **redirect**: Redirects call to ./docs
    """

    return RedirectResponse(url="./docs")


SAMPLE_CONTACT = ContactSchema(
    id="93db83d4-4119-4e0c-af87-a713786fa81d",
    contact=ContactMainSchema(
        id="001A000001aABcDEFG",
        country="us",
        created_date="2014-01-22T15:24:00+00:00",
        email="ctms-user@example.com",
        lang="en",
        last_modified_date="2020-01-22T15:24:00.000+0000",
        optin=True,
        optout=False,
        postal_code="666",
        record_type="0124A0000001aABCDE",
        token="142e20b6-1ef5-43d8-b5f4-597430e956d7",
    ),
    newsletters=[
        "app-dev",
        "maker-party",
        "mozilla-foundation",
        "mozilla-learning-network",
    ],
)
SAMPLE_CONTACTS = {SAMPLE_CONTACT.id: SAMPLE_CONTACT}


@app.get(
    "/ctms/{contact_id}",
    summary="Get all contact details in basket format",
    response_model=CTMSResponse,
)
async def read_ctms(contact_id: UUID = Path(..., title="The Contact ID")):
    try:
        contact = SAMPLE_CONTACTS[contact_id]
    except KeyError:
        raise HTTPException(status_code=404, detail="Contact not found")
    return CTMSResponse(
        id=contact.id,
        amo=contact.amo or ContactAmoSchema(),
        contact=contact.contact or ContactMainSchema(),
        cv=contact.cv or ContactCVSchema(),
        fpn=contact.fpn or ContactFpnSchema(),
        fsa=contact.fsa or ContactFsaSchema(),
        fxa=contact.fxa or ContactFxaSchema(),
        newsletters=contact.newsletters or [],
        status="ok",
    )


@app.get(
    "/identity/{contact_id}",
    summary="Get identities associated with the ID",
    response_model=IdentityResponse,
)
async def read_identity(contact_id: UUID = Path(..., title="The Contact ID")):
    try:
        contact = SAMPLE_CONTACTS[contact_id]
    except KeyError:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact.as_identity_response()


@app.get(
    "/contact/main/{contact_id}",
    summary="Get contact's main details",
    response_model=ContactMainSchema,
)
async def read_contact_main(contact_id: UUID = Path(..., title="The Contact ID")):
    try:
        contact = SAMPLE_CONTACTS[contact_id]
    except KeyError:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact.contact or ContactMainSchema()


@app.get(
    "/contact/amo/{contact_id}",
    summary="Get contact's add-ons details",
    response_model=ContactAmoSchema,
)
async def read_contact_amo(contact_id: UUID = Path(..., title="The Contact ID")):
    try:
        contact = SAMPLE_CONTACTS[contact_id]
    except KeyError:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact.amo or ContactAmoSchema()


@app.get(
    "/contact/cv/{contact_id}",
    summary="Get contact's Common Voice details",
    response_model=ContactCVSchema,
)
async def read_contact_cv(contact_id: UUID = Path(..., title="The Contact ID")):
    try:
        contact = SAMPLE_CONTACTS[contact_id]
    except KeyError:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact.cv or ContactCVSchema()


@app.get(
    "/contact/fpn/{contact_id}",
    summary="Get contact's Firefox Private Network details",
    response_model=ContactFpnSchema,
)
async def read_contact_fpn(contact_id: UUID = Path(..., title="The Contact ID")):
    try:
        contact = SAMPLE_CONTACTS[contact_id]
    except KeyError:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact.fpn or ContactFpnSchema()


@app.get(
    "/contact/fsa/{contact_id}",
    summary="Get contact's FSA details",
    response_model=ContactFsaSchema,
)
async def read_contact_fsa(contact_id: UUID = Path(..., title="The Contact ID")):
    try:
        contact = SAMPLE_CONTACTS[contact_id]
    except KeyError:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact.fsa or ContactFsaSchema()


@app.get(
    "/contact/fxa/{contact_id}",
    summary="Get contact's Firefox Account details",
    response_model=ContactFxaSchema,
)
async def read_contact_fxa(contact_id: UUID = Path(..., title="The Contact ID")):
    try:
        contact = SAMPLE_CONTACTS[contact_id]
    except KeyError:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact.fxa or ContactFxaSchema()


# NOTE:  This endpoint should provide a better proxy of "health".  It presently is a
# better proxy for application availability as opposed to health.
@app.get("/health")
async def health():
    return {"health": "OK"}, 200


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=80, reload=True)
