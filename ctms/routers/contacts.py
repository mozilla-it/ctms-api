import json
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette import status

from ctms.crud import (
    create_contact,
    create_or_update_contact,
    delete_contact,
    get_bulk_contacts,
    get_contact_by_email_id,
    get_contacts_by_any_id,
    get_email,
    update_contact,
)
from ctms.dependencies import get_db, get_enabled_api_client, get_json, get_settings
from ctms.metrics import get_metrics
from ctms.models import Email
from ctms.schemas import (
    ApiClientSchema,
    BadRequestResponse,
    BulkRequestSchema,
    ContactInSchema,
    ContactPatchSchema,
    ContactPutSchema,
    ContactSchema,
    CTMSBulkResponse,
    CTMSResponse,
    CTMSSingleResponse,
    IdentityResponse,
    NotFoundResponse,
    UnauthorizedResponse,
)

router = APIRouter()


def get_email_or_404(db: Session, email_id) -> Email:
    """Get an email and related data by email_ID, or raise a 404 exception."""
    email = get_email(db, email_id)
    if email is None:
        raise HTTPException(status_code=404, detail="Unknown email_id")
    return email


def get_contact_or_404(db: Session, email_id) -> ContactSchema:
    """Get a contact by email_ID, or raise a 404 exception."""
    email = get_email_or_404(db, email_id)
    return ContactSchema.from_email(email)


def all_ids(
    email_id: UUID | None = None,
    primary_email: str | None = None,
    basket_token: UUID | None = None,
    sfdc_id: str | None = None,
    mofo_contact_id: str | None = None,
    mofo_email_id: str | None = None,
    amo_user_id: str | None = None,
    fxa_id: str | None = None,
    fxa_primary_email: str | None = None,
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


def get_bulk_contacts_by_timestamp_or_4xx(
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
        (
            after_email_id,
            after_start_time,
        ) = BulkRequestSchema.extractor_for_bulk_encoded_details(after)

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
        results = [CTMSResponse(**contact.model_dump()) for contact in results]

    if last_page:
        # No results/end
        after_encoded = None
        next_url = None
    else:
        last_result: CTMSResponse = results[-1]
        after_encoded = BulkRequestSchema.compressor_for_bulk_encoded_details(
            last_email_id=last_result.email.email_id,
            last_update_time=last_result.email.update_timestamp,
        )

        next_url = (
            f"{get_settings().server_prefix}/updates?start={start_time.isoformat()}&end={end_time.isoformat()}&limit={limit}&after={after_encoded} "
        )

    return CTMSBulkResponse(
        start=start_time,
        end=end_time,
        after=after_encoded,
        limit=limit,
        items=results,
        next=next_url,
    )


@router.get(
    "/ctms",
    summary="Get all contacts matching alternate IDs",
    response_model=list[CTMSResponse],
    responses={
        400: {"model": BadRequestResponse},
        401: {"model": UnauthorizedResponse},
    },
    tags=["Public"],
)
def read_ctms_by_any_id(
    request: Request,
    db: Session = Depends(get_db),
    api_client: ApiClientSchema = Depends(get_enabled_api_client),
    ids=Depends(all_ids),
):
    if not any(ids.values()):
        detail = f"No identifiers provided, at least one is needed: {', '.join(ids.keys())}"
        raise HTTPException(status_code=400, detail=detail)
    contacts = get_contacts_by_any_id(db, **ids)
    return [CTMSResponse(**contact.model_dump()) for contact in contacts]


@router.get(
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
    request: Request,
    email_id: UUID = Path(..., title="The Email ID"),
    db: Session = Depends(get_db),
    api_client: ApiClientSchema = Depends(get_enabled_api_client),
):
    resp = get_ctms_response_or_404(db, email_id)
    return resp


def get_ctms_response_or_404(db, email_id):
    contact = get_contact_or_404(db, email_id)
    return CTMSSingleResponse(**contact.model_dump(), status="ok")


@router.post(
    "/ctms",
    summary="Create a contact, generating an id if not specified.",
    response_model=CTMSSingleResponse,
    responses={409: {"model": BadRequestResponse}},
    tags=["Public"],
)
def create_ctms_contact(
    contact: ContactInSchema,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    api_client: ApiClientSchema = Depends(get_enabled_api_client),
    content_json: dict | None = Depends(get_json),
):
    contact.email.email_id = contact.email.email_id or uuid4()
    email_id = contact.email.email_id
    existing = get_contact_by_email_id(db, email_id)
    if existing:
        if ContactInSchema(**existing.model_dump()).idempotent_equal(contact):
            response.headers["Location"] = f"/ctms/{email_id}"
            response.status_code = 200
            return get_ctms_response_or_404(db=db, email_id=email_id)
        raise HTTPException(status_code=409, detail="Contact already exists")
    try:
        create_contact(db, email_id, contact, get_metrics())
        db.commit()
    except Exception as e:
        db.rollback()
        if isinstance(e, IntegrityError):
            raise HTTPException(status_code=409, detail="Contact already exists") from e
        raise e from e
    response.headers["Location"] = f"/ctms/{email_id}"
    response.status_code = 201
    resp_data = get_ctms_response_or_404(db=db, email_id=email_id)
    return resp_data


@router.put(
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
    request: Request,
    response: Response,
    email_id: UUID = Path(..., title="The Email ID"),
    db: Session = Depends(get_db),
    api_client: ApiClientSchema = Depends(get_enabled_api_client),
    content_json: dict | None = Depends(get_json),
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
        create_or_update_contact(db, email_id, contact, get_metrics())
        db.commit()
    except Exception as e:
        db.rollback()
        if isinstance(e, IntegrityError):
            raise HTTPException(
                status_code=409,
                detail="Contact with primary_email or basket_token already exists",
            ) from e
        raise e from e
    response.status_code = 201
    return get_ctms_response_or_404(db=db, email_id=email_id)


@router.patch(
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
    request: Request,
    response: Response,
    email_id: UUID = Path(..., title="The Email ID"),
    db: Session = Depends(get_db),
    api_client: ApiClientSchema = Depends(get_enabled_api_client),
    content_json: dict | None = Depends(get_json),
):
    if contact.email and getattr(contact.email, "email_id") and contact.email.email_id != email_id:
        raise HTTPException(
            status_code=422,
            detail="cannot change email_id",
        )
    current_email = get_email_or_404(db, email_id)
    update_data = contact.model_dump(exclude_unset=True)
    update_contact(db, current_email, update_data, get_metrics())

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        if isinstance(e, IntegrityError):
            raise HTTPException(
                status_code=409,
                detail="Contact with primary_email, basket_token, mofo_email_id, or fxa_id already exists",
            ) from e
        raise
    response.status_code = 200
    return get_ctms_response_or_404(db=db, email_id=email_id)


@router.delete(
    "/ctms/{primary_email}",
    summary="Delete all contact information from primary email",
    response_model=list[IdentityResponse],
    responses={
        404: {"model": NotFoundResponse},
    },
    tags=["Public"],
)
def delete_contact_by_primary_email(
    primary_email: str,
    db: Session = Depends(get_db),
    api_client: ApiClientSchema = Depends(get_enabled_api_client),
):
    ids = all_ids(primary_email=primary_email.lower())
    contacts = get_contacts_by_any_id(db, **ids)

    if not contacts:
        raise HTTPException(status_code=404, detail=f"email {primary_email} not found!")

    for contact in contacts:
        delete_contact(db=db, email_id=contact.email.email_id)

    return [contact.as_identity_response() for contact in contacts]


@router.get(
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
    end: datetime | Literal[""] | None = None,
    limit: int | Literal[""] | None = None,
    after: str | None = None,
    mofo_relevant: bool | Literal[""] | None = None,
    db: Session = Depends(get_db),
    api_client: ApiClientSchema = Depends(get_enabled_api_client),
):
    try:
        bulk_request = BulkRequestSchema(
            start_time=start,
            end_time=end,
            limit=limit,
            after=after,
            mofo_relevant=mofo_relevant,
        )
        return get_bulk_contacts_by_timestamp_or_4xx(db=db, **bulk_request.model_dump())
    except ValidationError as e:
        detail = {"errors": json.loads(e.json())}
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail) from e


@router.get(
    "/identities",
    summary="Get identities associated with alternate IDs",
    response_model=list[IdentityResponse],
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
        detail = f"No identifiers provided, at least one is needed: {', '.join(ids.keys())}"
        raise HTTPException(status_code=400, detail=detail)
    contacts = get_contacts_by_any_id(db, **ids)
    return [contact.as_identity_response() for contact in contacts]


@router.get(
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
