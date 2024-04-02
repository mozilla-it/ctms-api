# pylint:disable = too-many-statements
import json
from typing import Dict, Optional
from uuid import UUID

import sentry_sdk
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from google.auth.exceptions import GoogleAuthError
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.util import b64decode

from ctms.auth import get_claim_from_pubsub_token
from ctms.config import Settings, re_trace_email
from ctms.dependencies import get_db, get_enabled_api_client, get_json, get_settings
from ctms.ingest_stripe import (
    StripeIngestActions,
    StripeIngestFxAIdConflict,
    StripeIngestUnknownObjectError,
    ingest_stripe_object,
)
from ctms.metrics import oauth2_scheme
from ctms.models import StripeCustomer
from ctms.schemas import ApiClientSchema

router = APIRouter()


def _pubsub_settings(
    settings: Settings = Depends(get_settings),
) -> Dict[str, str]:
    return {
        "audience": settings.pubsub_audience or settings.server_prefix,
        "email": settings.pubsub_email,
        "client": settings.pubsub_client,
    }


def get_pubsub_claim(
    request: Request,
    token: str = Depends(oauth2_scheme),
    pubsub_settings=Depends(_pubsub_settings),
    pubsub_client: str = None,
):
    for name in ("audience", "email", "client"):
        if not pubsub_settings[name]:
            # pylint: disable-next=broad-exception-raised
            raise Exception(f"PUBSUB_{name.upper()} is unset")

    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    log_context = request.state.log_context
    log_context["client_allowed"] = False

    if pubsub_client != pubsub_settings["client"]:
        log_context["auth_fail"] = "Verification mismatch"
        raise credentials_exception

    try:
        claim = get_claim_from_pubsub_token(token, pubsub_settings["audience"])
    except ValueError as exception:
        sentry_sdk.capture_exception(exception)
        log_context["auth_fail"] = "Unknown key"
        raise credentials_exception from exception
    except GoogleAuthError as exception:
        sentry_sdk.capture_exception(exception)
        log_context["auth_fail"] = "Google authentication failure"
        raise credentials_exception from exception

    # Add claim as context for debugging
    for key, value in claim.items():
        log_context[f"pubsub_{key}"] = value

    if claim.get("email") != pubsub_settings["email"]:
        log_context["auth_fail"] = "Wrong email"
        raise credentials_exception

    if not claim.get("email_verified"):
        log_context["auth_fail"] = "Email not verified"
        raise credentials_exception

    log_context["client_allowed"] = True
    return claim


def _process_stripe_object(
    db_session: Session, data: Dict
) -> tuple[Optional[UUID], Optional[str], Optional[str], StripeIngestActions]:
    """
    Ingest a Stripe Object and extract related data.

    If a Stripe customer has an FxA ID that matches a current (but different)
    customer, then the existing customer is deleted. This matches the FxA
    Firestore cache of Stripe customers, which index by FxA ID. This has
    occured occasionally in stage, due to bugs or manual interaction with the
    Stripe API.

    Return is a tuple:
    - email_id - The related Contact email_id, or None if no contact.
    - trace_email - The email to trace, or None if not Customer or doesn't match
    - fxa_conflict - The FxA ID if there was a collision, otherwise None
    - actions - The actions taken by the Stripe ingesters

    Raises:
    - StripeIngestBadObjectError if the data isn't a Stripe object
    - StripeIngestUnknownObjectError if the data is an unhandled Stripe object
    - Other errors (ValueError, KeyError) if the Stripe object has unexpected
      data for keys that CTMS examines. Extra data is ignored.
    """

    fxa_conflict = None
    try:
        obj, actions = ingest_stripe_object(db_session, data)
    except StripeIngestFxAIdConflict as e:
        # Delete the existing Stripe customer with that FxA ID
        stripe_id = e.stripe_id
        fxa_conflict = e.fxa_id
        stmt = (
            delete(StripeCustomer)
            .where(StripeCustomer.stripe_id == stripe_id)
            .execution_options(synchronize_session="evaluate")
        )
        db_session.execute(stmt)

        obj, actions = ingest_stripe_object(db_session, data)
        actions.setdefault("deleted", set()).add(f"customer:{stripe_id}")

    try:
        db_session.commit()
    except IntegrityError as e:
        db_session.rollback()
        structlog.get_logger("ctms.web").exception("IntegrityError converted to 409")
        raise HTTPException(status_code=409, detail="Write conflict, try again") from e
    except OperationalError as e:
        db_session.rollback()
        structlog.get_logger("ctms.web").exception("OperationalError converted to 409")
        raise HTTPException(
            status_code=409, detail="Deadlock or other issue, try again"
        ) from e

    email_id = obj.get_email_id() if obj else None
    if data["object"] == "customer" and re_trace_email.match(data.get("email", "")):
        trace_email = data["email"]
    else:
        trace_email = None
    return email_id, trace_email, fxa_conflict, actions


@router.post(
    "/stripe",
    summary="Add or update Stripe data",
    tags=["Public"],
)
def stripe(
    request: Request,
    db_session: Session = Depends(get_db),
    api_client: ApiClientSchema = Depends(get_enabled_api_client),
    data: Optional[Dict] = Depends(get_json),
):
    if not ("object" in data and "id" in data):
        raise HTTPException(status_code=400, detail="Request JSON is not recognized.")
    try:
        _, trace_email, fxa_conflict, actions = _process_stripe_object(db_session, data)
    except (KeyError, ValueError, TypeError) as exception:
        raise HTTPException(
            400, detail="Unable to process Stripe object."
        ) from exception
    if trace_email:
        request.state.log_context["trace"] = trace_email
        request.state.log_context["trace_json"] = data
    if fxa_conflict:
        request.state.log_context["fxa_id_conflict"] = fxa_conflict
    if actions:
        ingest_actions = {}
        for key in sorted(actions.keys()):
            ingest_actions[key] = sorted(actions[key])
        request.state.log_context["ingest_actions"] = ingest_actions

    return {"status": "OK"}


@router.post(
    "/stripe_from_pubsub",
    summary="Add or update Stripe data from PubSub",
    tags=["Private"],
)
def stripe_pubsub(
    request: Request,
    db_session: Session = Depends(get_db),
    pubsub_claim=Depends(get_pubsub_claim),
    wrapped_data: Optional[Dict] = Depends(get_json),
):
    if not ("message" in wrapped_data and "subscription" in wrapped_data):
        content = {
            "status": "Accepted but not processed",
            "message": "Message does not appear to be from pubsub, do not send again.",
        }
        return JSONResponse(content=content, status_code=202)
    payload = json.loads(b64decode(wrapped_data["message"]["data"]).decode())
    if hasattr(payload, "keys"):
        if all(key.count(":") == 1 for key in payload.keys()):
            # Item dictionary, "firebase_table:id" -> Stripe object
            items = []
            for key, value in payload.items():
                if value:
                    items.append(value)
                else:
                    structlog.get_logger("ctms.web").warning(
                        f"PubSub key {key} had empty value {value}"
                    )
        else:
            items = [payload]  # One Stripe object, or maybe unknown dictionary
    else:
        content = {
            "status": "Accepted but not processed",
            "message": "Unknown payload type, do not send again.",
        }
        return JSONResponse(content=content, status_code=202)

    email_ids = set()
    fxa_conflicts = set()
    trace = None
    has_error = False
    count = 0
    actions: StripeIngestActions = {}
    for item in items:
        try:
            email_id, trace_email, fxa_conflict, item_actions = _process_stripe_object(
                db_session, item
            )
        except StripeIngestUnknownObjectError as exception:
            actions.setdefault("skipped", set()).add(
                f"{exception.object_value}:{exception.object_id}"
            )
        except (KeyError, ValueError, TypeError) as exception:
            sentry_sdk.capture_exception(exception)
            has_error = True
        else:
            count += 1
            if email_id:
                email_ids.add(email_id)
            if trace_email:
                trace = trace_email
            if fxa_conflict:
                fxa_conflicts.add(fxa_conflict)
            for key, values in item_actions.items():
                actions.setdefault(key, set()).update(values)

    if trace:
        request.state.log_context["trace"] = trace
        request.state.log_context["trace_json"] = payload
    if fxa_conflicts:
        request.state.log_context["fxa_id_conflict"] = ",".join(sorted(fxa_conflicts))
    if actions:
        ingest_actions = {}
        for key in sorted(actions.keys()):
            ingest_actions[key] = sorted(actions[key])
        request.state.log_context["ingest_actions"] = ingest_actions

    if has_error:
        content = {
            "status": "Accepted but not processed",
            "message": "Errors processing the data, do not send again.",
        }
        return JSONResponse(content=content, status_code=202)
    return {"status": "OK", "count": count}
