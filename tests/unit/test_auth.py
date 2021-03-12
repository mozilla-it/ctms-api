"""Test authentication"""

from datetime import datetime, timedelta

import pytest
from jose import jwt
from requests.auth import HTTPBasicAuth

from ctms.app import app, token_settings
from ctms.auth import create_access_token, hash_password, verify_password
from ctms.crud import create_api_client, get_api_client_by_id
from ctms.schemas import ApiClientSchema


@pytest.fixture
def client_id_and_secret(dbsession):
    """Return valid OAuth2 client_id and client_secret."""
    api_client = ApiClientSchema(
        client_id="id_db_api_client", email="db_api_client@example.com", enabled=True
    )
    secret = "secret_what_a_weird_random_string"  # pragma: allowlist secret
    create_api_client(dbsession, api_client, secret)
    dbsession.flush()
    return (api_client.client_id, secret)


@pytest.fixture
def test_token_settings():
    """Set token settings for tests."""

    settings = {
        "expires_delta": timedelta(minutes=5),
        "secret_key": "AN_AWESOME_RANDOM_SECRET_KEY",
    }

    app.dependency_overrides[token_settings] = lambda: settings
    yield settings
    del app.dependency_overrides[token_settings]


def test_post_token_header(anon_client, test_token_settings, client_id_and_secret):
    """A backend client can post crendentials in the header"""
    client_id, client_secret = client_id_and_secret
    resp = anon_client.post(
        "/token",
        {"grant_type": "client_credentials"},
        auth=HTTPBasicAuth(client_id, client_secret),
    )
    assert resp.status_code == 200
    content = resp.json()
    assert content["token_type"] == "bearer"
    assert content["expires_in"] == 5 * 60
    payload = jwt.decode(
        content["access_token"],
        test_token_settings["secret_key"],
    )
    assert payload["sub"] == f"api_client:{client_id}"
    expected_expires = (
        datetime.utcnow() + test_token_settings["expires_delta"]
    ).timestamp()
    assert -2.0 < (expected_expires - payload["exp"]) < 2.0


def test_post_token_form_data(anon_client, test_token_settings, client_id_and_secret):
    """A backend client can post crendentials in body as form data"""

    client_id, client_secret = client_id_and_secret
    resp = anon_client.post(
        "/token",
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )
    assert resp.status_code == 200
    content = resp.json()
    assert content["token_type"] == "bearer"
    payload = jwt.decode(
        content["access_token"],
        test_token_settings["secret_key"],
    )
    assert payload["sub"] == f"api_client:{client_id}"
    expected_expires = (
        datetime.utcnow() + test_token_settings["expires_delta"]
    ).timestamp()
    assert -2.0 < (expected_expires - payload["exp"]) < 2.0


def test_post_token_succeeds_no_grant(anon_client, client_id_and_secret):
    """If grant_type is omitted, client_credentials is assumed."""
    resp = anon_client.post(
        "/token",
        auth=HTTPBasicAuth(*client_id_and_secret),
    )
    assert resp.status_code == 200


def test_post_token_fails_wrong_grant(anon_client, client_id_and_secret):
    """If grant_type is omitted, getting a token fails."""
    resp = anon_client.post(
        "/token",
        {"grant_type": "password"},
        auth=HTTPBasicAuth(*client_id_and_secret),
    )
    assert resp.status_code == 422
    assert resp.json()["detail"][0] == {
        "ctx": {"pattern": "client_credentials"},
        "loc": ["body", "grant_type"],
        "msg": 'string does not match regex "client_credentials"',
        "type": "value_error.str.regex",
    }


def test_post_token_fails_no_credentials(anon_client, dbsession):
    """If no credentials are passed, token generation fails."""
    resp = anon_client.post("/token", {"grant_type": "client_credentials"})
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Incorrect username or password"}


def test_post_token_fails_bad_credentials(anon_client, client_id_and_secret):
    """Authentication fails on bad credentials."""
    good_id, good_secret = client_id_and_secret
    resp = anon_client.post("/token", auth=HTTPBasicAuth(good_id, good_secret + "x"))
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Incorrect username or password"}


def test_post_token_fails_disabled_client(dbsession, anon_client, client_id_and_secret):
    """Authentication fails when the client is disabled."""
    client_id, client_secret = client_id_and_secret
    api_client = get_api_client_by_id(dbsession, client_id)
    api_client.enabled = False
    dbsession.commit()
    resp = anon_client.post("/token", auth=HTTPBasicAuth(client_id, client_secret))
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Incorrect username or password"}


def test_get_ctms_with_token(
    example_contact, anon_client, test_token_settings, client_id_and_secret
):
    """An authenticated API can be fetched with a valid token"""
    client_id, client_secret = client_id_and_secret
    token = create_access_token(
        {"sub": f"api_client:{client_id}"}, **test_token_settings
    )
    resp = anon_client.get(
        f"/ctms/{example_contact.email.email_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


def test_get_ctms_with_invalid_token_fails(
    example_contact, anon_client, test_token_settings, client_id_and_secret
):
    """Calling an authenticated API with an invalid token is an error"""
    client_id, client_secret = client_id_and_secret
    token = create_access_token(
        {"sub": f"api_client:{client_id}"},
        secret_key="secret_key_from_other_deploy",
        expires_delta=test_token_settings["expires_delta"],
    )
    resp = anon_client.get(
        f"/ctms/{example_contact.email.email_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Could not validate credentials"}


def test_get_ctms_with_invalid_namespace_fails(
    example_contact, anon_client, test_token_settings, client_id_and_secret
):
    """Calling an authenticated API with an unexpected namespace is an error"""
    client_id, client_secret = client_id_and_secret
    token = create_access_token({"sub": f"unknown:{client_id}"}, **test_token_settings)
    resp = anon_client.get(
        f"/ctms/{example_contact.email.email_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Could not validate credentials"}


def test_get_ctms_with_unknown_client_fails(
    example_contact, anon_client, test_token_settings, client_id_and_secret
):
    """A token with an unknown (deleted?) API client name is an error"""
    client_id, client_secret = client_id_and_secret
    token = create_access_token(
        {"sub": f"api_client:not_{client_id}"}, **test_token_settings
    )
    resp = anon_client.get(
        f"/ctms/{example_contact.email.email_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Could not validate credentials"}


def test_get_ctms_with_expired_token_fails(
    example_contact, anon_client, test_token_settings, client_id_and_secret
):
    """Calling an authenticated API with an expired token is an error"""
    yesterday = datetime.utcnow() - timedelta(days=1)
    client_id, client_secret = client_id_and_secret
    token = create_access_token(
        {"sub": f"api_client:{client_id}"}, **test_token_settings, now=yesterday
    )
    resp = anon_client.get(
        f"/ctms/{example_contact.email.email_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Could not validate credentials"}


def test_get_ctms_with_disabled_client_fails(
    dbsession, example_contact, anon_client, test_token_settings, client_id_and_secret
):
    """Calling an authenticated API with a valid token for an expired client is an error."""
    client_id, client_secret = client_id_and_secret
    token = create_access_token(
        {"sub": f"api_client:{client_id}"}, **test_token_settings
    )
    api_client = get_api_client_by_id(dbsession, client_id)
    api_client.enabled = False
    dbsession.commit()

    resp = anon_client.get(
        f"/ctms/{example_contact.email.email_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert resp.json() == {"detail": "API Client has been disabled"}


def test_hashed_passwords():
    """Hashed passwords have unique salts"""
    hashed1 = hash_password("password")
    assert hashed1 != "password"
    assert verify_password("password", hashed1)
    assert not verify_password("xpassword", hashed1)

    hashed2 = hash_password("password")
    assert verify_password("password", hashed1)
    assert hashed1 != hashed2
