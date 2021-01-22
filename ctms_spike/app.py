from typing import List, Optional

import uvicorn
from fastapi import Body, FastAPI, Path, Query
from fastapi.responses import RedirectResponse

from ctms_spike.models import (
    APIRequest,
    APIResponse,
    ExampleAPIRequest,
    ExampleAPIResponse,
)

app = FastAPI(
    title="Containerized Microservice",
    description="Containerized microservice template with some examples.",
    version="0.1.0",
)


@app.get("/")
def root():
    """GET via root redirects to /docs.

    - Args:

    - Returns:
        - **redirect**: Redirects call to ./docs
    """

    return RedirectResponse(url="./docs")


@app.get(
    "/identity/{contact_id}",
    summary="Get identities associated with the ID",
)
def read_identity(contact_id: str):
    return {
        "id": "001A000001aABcDEFG",
        "amo_id": None,
        "fxa_id": None,
        "payee_id": None,
        "email": "ctms-user@example.com",
        "fxa_primary_email": None,
        "token": "142e20b6-1ef5-43d8-b5f4-597430e956d7",
    }


@app.get("/contact/main/{contact_id}", summary="Get contact by ID")
def read_contact_main(contact_id: str):
    return {
        "postal_code": "666",
        "cv_created_at": None,
        "cv_days_interval": None,
        "cv_first_contribution_date": None,
        "cv_goal_reached_at": None,
        "cv_last_active_date": None,
        "cv_two_day_streak": None,
        "email": "ctms-user@example.com",
        "token": "142e20b6-1ef5-43d8-b5f4-597430e956d7",
        "country": "us",
        "created_date": "2014-01-22T15:24:00.000+0000",
        "lang": "en",
        "last_modified_date": "2020-01-22T15:24:00.000+0000",
        "optin": True,
        "optout": False,
        "reason": None,
        "record_type": "0124A0000001aABCDE",
        "id": "001A000001aABcDEFG",
    }


# NOTE:  This endpoint should provide a better proxy of "health".  It presently is a
# better proxy for application availability as opposed to health.
@app.get("/health")
def health():
    return {"health": "OK"}, 200


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=80, reload=True)
