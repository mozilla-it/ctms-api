from datetime import timedelta
from functools import lru_cache
from typing import Dict, Union

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ctms.auth import auth_info_context, get_subject_from_token
from ctms.config import Settings
from ctms.crud import get_api_client_by_id, update_api_client_last_access
from ctms.database import SessionLocal
from ctms.metrics import oauth2_scheme
from ctms.schemas import ApiClientSchema


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def get_db():  # pragma: no cover
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_token_settings(
    settings: Settings = Depends(get_settings),
) -> Dict[str, Union[str, timedelta]]:
    return {
        "expires_delta": settings.token_expiration,
        "secret_key": settings.secret_key,
    }


def get_api_client(
    request: Request,
    token: str = Depends(oauth2_scheme),
    token_settings=Depends(get_token_settings),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    namespace, name = get_subject_from_token(
        token,
        secret_key=token_settings["secret_key"],
    )

    auth_info = auth_info_context.get()
    auth_info.clear()
    auth_info["client_allowed"] = False

    if name is None:
        auth_info["auth_fail"] = "No or bad token"
        raise credentials_exception

    auth_info["client_id"] = name
    if namespace != "api_client":
        auth_info["auth_fail"] = "Bad namespace"
        raise credentials_exception

    api_client = get_api_client_by_id(db, name)
    if not api_client:
        auth_info["auth_fail"] = "No client record"
        raise credentials_exception

    # Track last usage of API client.
    update_api_client_last_access(db, api_client)

    return api_client


def get_enabled_api_client(
    request: Request, api_client: ApiClientSchema = Depends(get_api_client)
):
    auth_info = auth_info_context.get()
    auth_info.clear()
    if not auth_info.get("client_id"):
        # get_api_client was overridden by test
        auth_info["client_id"] = api_client.client_id
    if not api_client.enabled:
        auth_info["auth_fail"] = "Client disabled"
        raise HTTPException(status_code=400, detail="API Client has been disabled")
    auth_info["client_allowed"] = True
    return api_client


async def get_json(request: Request) -> Dict:
    """
    Get the request body as JSON.

    If the body is not valid JSON, FastAPI will return a ValidationError or 400
    before this dependency is resolved.
    If the body is form-encoded, it will raise an unknown exception.
    """
    the_json: Dict = await request.json()
    return the_json
