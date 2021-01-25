from typing import List, Optional
from uuid import UUID

import uvicorn
from fastapi import Body, FastAPI, HTTPException, Path, Query
from fastapi.responses import RedirectResponse

from ctms_spike.models import (
    APIRequest,
    APIResponse,
    ExampleAPIRequest,
    ExampleAPIResponse,
)

app = FastAPI(
    title="Contact Management System (CTMS)",
    description="Spike of CTMS API for task 185.",
    version="0.0.1",
)


@app.get("/")
def root():
    """GET via root redirects to /docs.

    - Args:

    - Returns:
        - **redirect**: Redirects call to ./docs
    """

    return RedirectResponse(url="./docs")


SAMPLE_USERS = {
    UUID("93db83d4-4119-4e0c-af87-a713786fa81d"): {
        "amo_id": None,
        "country": "us",
        "created_date": "2014-01-22T15:24:00.000+0000",
        "cv_created_at": None,
        "cv_days_interval": None,
        "cv_first_contribution_date": None,
        "cv_goal_reached_at": None,
        "cv_last_active_date": None,
        "cv_two_day_streak": None,
        "email": "ctms-user@example.com",
        "fxa_id": None,
        "fxa_primary_email": None,
        "id": "001A000001aABcDEFG",
        "lang": "en",
        "last_modified_date": "2020-01-22T15:24:00.000+0000",
        "optin": True,
        "optout": False,
        "payee_id": None,
        "postal_code": "666",
        "reason": None,
        "record_type": "0124A0000001aABCDE",
        "token": "142e20b6-1ef5-43d8-b5f4-597430e956d7",
    }
}


@app.get(
    "/identity/{contact_id}",
    summary="Get identities associated with the ID",
)
def read_identity(contact_id: UUID = Path(..., title="The Contact ID")):
    try:
        user = SAMPLE_USERS[contact_id]
    except KeyError:
        raise HTTPException(status_code=404, detail="Contact not found")
    fields = [
        "id",
        "amo_id",
        "fxa_id",
        "fxa_primary_email",
        "token",
    ]
    return {field: user[field] for field in fields}


@app.get("/contact/main/{contact_id}", summary="Get contact by ID")
def read_contact_main(contact_id: UUID = Path(..., title="The Contact ID")):
    try:
        user = SAMPLE_USERS[contact_id]
    except KeyError:
        raise HTTPException(status_code=404, detail="Contact not found")

    fields = [
        "postal_code",
        "cv_created_at",
        "cv_days_interval",
        "cv_first_contribution_date",
        "cv_goal_reached_at",
        "cv_last_active_date",
        "cv_two_day_streak",
        "email",
        "token",
        "country",
        "created_date",
        "lang",
        "last_modified_date",
        "optin",
        "optout",
        "reason",
        "record_type",
        "id",
    ]
    return {field: user[field] for field in fields}


# NOTE:  This endpoint should provide a better proxy of "health".  It presently is a
# better proxy for application availability as opposed to health.
@app.get("/health")
def health():
    return {"health": "OK"}, 200


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=80, reload=True)
