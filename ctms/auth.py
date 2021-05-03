"""
Implement OAuth2 client credentials.

A backend client POSTs to the /token endpoint, sending client_id and
client_secret, either as form fields in the body, or in the Authentication
header. A JWT token is returned that expires after a short time. To renew,
the client POSTs to /token again.
"""
import warnings
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from fastapi.exceptions import HTTPException
from fastapi.param_functions import Form
from fastapi.security.oauth2 import OAuth2, OAuthFlowsModel
from fastapi.security.utils import get_authorization_scheme_param
from passlib.context import CryptContext
from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED

with warnings.catch_warnings():
    # TODO: remove when fixed: https://github.com/mpdavis/python-jose/issues/208
    warnings.filterwarnings("ignore", message="int_from_bytes is deprecated")
    from jose import JWTError, jwt

# Argon2 is the winner of the 2015 password hashing competion.
# It is supported by passlib with the recommended argon2_cffi library.
pwd_context = CryptContext(schemes=["argon2"], deprecated=["auto"])


def verify_password(plain_password, hashed_password):
    """Verify the password, using a constant time equality check."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(plain_password):
    """Hash the password, using the pre-configured CryptContext."""
    return pwd_context.hash(plain_password)


def create_access_token(
    data: dict,
    expires_delta: timedelta,
    secret_key: str,
    now: Optional[datetime] = None,
) -> str:
    """Create a JWT string to act as an OAuth2 access token."""
    to_encode = data.copy()
    expire = (now or datetime.now(timezone.utc)) + expires_delta
    to_encode["exp"] = expire
    encoded_jwt: str = jwt.encode(to_encode, secret_key, algorithm="HS256")
    return encoded_jwt


def get_subject_from_token(token: str, secret_key: str):
    """Get the parts of a valid token subject.

    Returns (namespace, identity) if the token is valid
    Returns (None, None) if the token is expired or invalid, or the payload is invalid.
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
    except JWTError:
        return None, None
    sub = payload["sub"]
    if ":" not in sub:
        return None, None
    return sub.split(":", 1)


class OAuth2ClientCredentialsRequestForm:
    """
    Expect OAuth2 client credentials as form request parameters

    This is a dependency class, modeled after OAuth2PasswordRequestForm and similar.
    Use it like:

        @app.post("/login")
        def login(form_data: OAuth2ClientCredentialsRequestForm = Depends()):
            data = form_data.parse()
            print(data.client_id)
            for scope in data.scopes:
                print(scope)
            return data

    It creates the following Form request parameters in your endpoint:
    grant_type: the OAuth2 spec says it is required and MUST be the fixed string "client_credentials".
        Nevertheless, this dependency class is permissive and allows not passing it.
    scope: Optional string. Several scopes (each one a string) separated by spaces. Currently unused.
    client_id: optional string. OAuth2 recommends sending the client_id and client_secret (if any)
        using HTTP Basic auth, as: client_id:client_secret
    client_secret: optional string. OAuth2 recommends sending the client_id and client_secret (if any)
        using HTTP Basic auth, as: client_id:client_secret
    """

    def __init__(
        self,
        grant_type: str = Form(None, regex="^(client_credentials|refresh_token)$"),
        scope: str = Form(""),
        client_id: Optional[str] = Form(None),
        client_secret: Optional[str] = Form(None),
    ):
        self.grant_type = grant_type
        self.scopes = scope.split()
        self.client_id = client_id
        self.client_secret = client_secret


class OAuth2ClientCredentials(OAuth2):
    """
    Implement OAuth2 client_credentials workflow.

    This is modeled after the OAuth2PasswordBearer and OAuth2AuthorizationCodeBearer
    classes from FastAPI, but sets auto_error to True to avoid uncovered branches.
    See https://github.com/tiangolo/fastapi/issues/774 for original implementation,
    and to check if FastAPI added a similar class.

    See RFC 6749 for details of the client credentials authorization grant.
    """

    def __init__(
        self,
        tokenUrl: str,
        scheme_name: Optional[str] = None,
        scopes: Optional[Dict[str, str]] = None,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(
            clientCredentials={"tokenUrl": tokenUrl, "scopes": scopes}
        )
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=True)

    async def __call__(self, request: Request) -> Optional[str]:
        authorization: str = request.headers.get("Authorization")

        # TODO: Try combining these lines after FastAPI 0.61.2 / mypy update
        scheme_param = get_authorization_scheme_param(authorization)
        scheme: str = scheme_param[0]
        param: str = scheme_param[1]

        if not authorization or scheme.lower() != "bearer":
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return param
