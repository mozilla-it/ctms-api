from datetime import datetime
from typing import Dict
from uuid import UUID

import uvicorn
from fastapi import FastAPI, HTTPException, Path
from fastapi.responses import RedirectResponse
from pydantic import EmailStr

from .models import (
    ContactAddonsSchema,
    ContactCommonVoiceSchema,
    ContactFirefoxAccountsSchema,
    ContactFirefoxPrivateNetworkSchema,
    ContactFirefoxStudentAmbassadorSchema,
    ContactMainSchema,
    ContactSchema,
    CTMSResponse,
    IdentityResponse,
    NotFoundResponse,
)
from .sample_data import SAMPLE_CONTACTS

app = FastAPI(
    title="ConTact Management System (CTMS)",
    description="CTMS API (work in progress)",
    version="0.0.1",
)


async def get_contact_or_404(contact_id) -> ContactSchema:
    """
    Get a contact by ID, or raise a 404 exception.

    TODO: implement a database backend
    """
    try:
        return SAMPLE_CONTACTS[contact_id]
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown contact_id")


@app.get("/")
async def root():
    """GET via root redirects to /docs.

    - Args:

    - Returns:
        - **redirect**: Redirects call to ./docs
    """

    return RedirectResponse(url="./docs")


@app.get(
    "/ctms/{contact_id}",
    summary="Get all contact details in basket format",
    response_model=CTMSResponse,
    responses={404: {"model": NotFoundResponse}},
)
async def read_ctms(contact_id: UUID = Path(..., title="The Contact ID")):
    contact = await get_contact_or_404(contact_id)
    return CTMSResponse(
        id=contact.id,
        amo=contact.amo or ContactAddonsSchema(),
        contact=contact.contact or ContactMainSchema(),
        cv=contact.cv or ContactCommonVoiceSchema(),
        fpn=contact.fpn or ContactFirefoxPrivateNetworkSchema(),
        fsa=contact.fsa or ContactFirefoxStudentAmbassadorSchema(),
        fxa=contact.fxa or ContactFirefoxAccountsSchema(),
        newsletters=contact.newsletters or [],
        status="ok",
    )


@app.get(
    "/identity/{contact_id}",
    summary="Get identities associated with the ID",
    response_model=IdentityResponse,
    responses={404: {"model": NotFoundResponse}},
)
async def read_identity(contact_id: UUID = Path(..., title="The Contact ID")):
    contact = await get_contact_or_404(contact_id)
    return contact.as_identity_response()


@app.get(
    "/contact/main/{contact_id}",
    summary="Get contact's main details",
    response_model=ContactMainSchema,
    responses={404: {"model": NotFoundResponse}},
)
async def read_contact_main(contact_id: UUID = Path(..., title="The Contact ID")):
    contact = await get_contact_or_404(contact_id)
    return contact.contact or ContactMainSchema()


@app.get(
    "/contact/amo/{contact_id}",
    summary="Get contact's add-ons details",
    response_model=ContactAddonsSchema,
    responses={404: {"model": NotFoundResponse}},
)
async def read_contact_amo(contact_id: UUID = Path(..., title="The Contact ID")):
    contact = await get_contact_or_404(contact_id)
    return contact.amo or ContactAddonsSchema()


@app.get(
    "/contact/cv/{contact_id}",
    summary="Get contact's Common Voice details",
    response_model=ContactCommonVoiceSchema,
    responses={404: {"model": NotFoundResponse}},
)
async def read_contact_cv(contact_id: UUID = Path(..., title="The Contact ID")):
    contact = await get_contact_or_404(contact_id)
    return contact.cv or ContactCommonVoiceSchema()


@app.get(
    "/contact/fpn/{contact_id}",
    summary="Get contact's Firefox Private Network details",
    response_model=ContactFirefoxPrivateNetworkSchema,
    responses={404: {"model": NotFoundResponse}},
)
async def read_contact_fpn(contact_id: UUID = Path(..., title="The Contact ID")):
    contact = await get_contact_or_404(contact_id)
    return contact.fpn or ContactFirefoxPrivateNetworkSchema()


@app.get(
    "/contact/fsa/{contact_id}",
    summary="Get contact's FSA details",
    response_model=ContactFirefoxStudentAmbassadorSchema,
    responses={404: {"model": NotFoundResponse}},
)
async def read_contact_fsa(contact_id: UUID = Path(..., title="The Contact ID")):
    contact = await get_contact_or_404(contact_id)
    return contact.fsa or ContactFirefoxStudentAmbassadorSchema()


@app.get(
    "/contact/fxa/{contact_id}",
    summary="Get contact's Firefox Account details",
    response_model=ContactFirefoxAccountsSchema,
    responses={404: {"model": NotFoundResponse}},
)
async def read_contact_fxa(contact_id: UUID = Path(..., title="The Contact ID")):
    contact = await get_contact_or_404(contact_id)
    return contact.fxa or ContactFirefoxAccountsSchema()


# NOTE:  This endpoint should provide a better proxy of "health".  It presently is a
# better proxy for application availability as opposed to health.
@app.get("/health")
async def health():
    return {"health": "OK"}, 200


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=80, reload=True)
