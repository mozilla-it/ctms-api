"""Test authentication"""

import logging
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from requests.auth import HTTPBasicAuth

from ctms.app import app
from ctms.auth import create_access_token, hash_password, verify_password
from ctms.crud import get_api_client_by_id
from ctms.dependencies import get_token_settings


@pytest.fixture
def test_token_settings():
    """Set token settings for tests."""

    settings = {
        "expires_delta": timedelta(minutes=5),
        "secret_key": "AN_AWESOME_RANDOM_SECRET_KEY",
    }

    app.dependency_overrides[get_token_settings] = lambda: settings
    yield settings
    del app.dependency_overrides[get_token_settings]


def test_post_token_header(anon_client, test_token_settings, client_id_and_secret):
    """A backend client can post crendentials in the header"""
    client_id, client_secret = client_id_and_secret
    resp = anon_client.post(
        "/token",
        data={"grant_type": "client_credentials"},
        auth=HTTPBasicAuth(client_id, client_secret),
    )
    assert resp.status_code == 200
    content = resp.json()
    assert content["token_type"] == "bearer"
    assert content["expires_in"] == 5 * 60
    payload = jwt.decode(content["access_token"], test_token_settings["secret_key"], algorithms=["HS256"])
    assert payload["sub"] == f"api_client:{client_id}"
    expected_expires = (datetime.now(timezone.utc) + test_token_settings["expires_delta"]).timestamp()
    assert -2.0 < (expected_expires - payload["exp"]) < 2.0


def test_post_token_form_data(anon_client, test_token_settings, client_id_and_secret):
    """A backend client can post crendentials in body as form data"""

    client_id, client_secret = client_id_and_secret
    resp = anon_client.post(
        "/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )
    assert resp.status_code == 200
    content = resp.json()
    assert content["token_type"] == "bearer"
    payload = jwt.decode(content["access_token"], test_token_settings["secret_key"], algorithms=["HS256"])
    assert payload["sub"] == f"api_client:{client_id}"
    expected_expires = (datetime.now(timezone.utc) + test_token_settings["expires_delta"]).timestamp()
    assert -2.0 < (expected_expires - payload["exp"]) < 2.0


def test_post_token_succeeds_no_grant(anon_client, client_id_and_secret):
    """If grant_type is omitted, client_credentials is assumed."""
    resp = anon_client.post(
        "/token",
        auth=HTTPBasicAuth(*client_id_and_secret),
    )
    assert resp.status_code == 200


def test_post_token_succeeds_refresh_grant(anon_client, test_token_settings, client_id_and_secret):
    """If grant_type is refresh_token, the token grant is successful."""
    client_id, client_secret = client_id_and_secret
    resp = anon_client.post(
        "/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": None,
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )
    assert resp.status_code == 200


def test_post_token_fails_wrong_grant(anon_client, client_id_and_secret):
    """If grant_type is omitted, getting a token fails."""
    resp = anon_client.post(
        "/token",
        data={"grant_type": "password"},
        auth=HTTPBasicAuth(*client_id_and_secret),
    )
    assert resp.status_code == 422
    pattern = "^(client_credentials|refresh_token)$"
    assert resp.json()["detail"][0] == {
        "ctx": {"pattern": pattern},
        "input": "password",
        "loc": ["body", "grant_type"],
        "msg": f"String should match pattern '{pattern}'",
        "type": "string_pattern_mismatch",
    }


def test_post_token_fails_no_credentials(anon_client, caplog):
    """If no credentials are passed, token generation fails."""
    with caplog.at_level(logging.INFO):
        resp = anon_client.post("/token", data={"grant_type": "client_credentials"})
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Incorrect username or password"}
    assert caplog.records[0].token_fail == "No credentials"


def test_post_token_fails_unknown_api_client(anon_client, client_id_and_secret, caplog):
    """Authentication failes on unknown api_client ID."""
    good_id, good_secret = client_id_and_secret
    with caplog.at_level(logging.INFO):
        resp = anon_client.post("/token", auth=HTTPBasicAuth(good_id + "x", good_secret))
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Incorrect username or password"}
    assert caplog.records[0].token_creds_from == "header"
    assert caplog.records[0].token_fail == "No client record"


def test_post_token_fails_bad_credentials(anon_client, client_id_and_secret, caplog):
    """Authentication fails on bad credentials."""
    good_id, good_secret = client_id_and_secret
    with caplog.at_level(logging.INFO):
        resp = anon_client.post("/token", auth=HTTPBasicAuth(good_id, good_secret + "x"))
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Incorrect username or password"}
    assert caplog.records[0].token_creds_from == "header"
    assert caplog.records[0].token_fail == "Bad credentials"


def test_post_token_fails_disabled_client(dbsession, anon_client, client_id_and_secret, caplog):
    """Authentication fails when the client is disabled."""
    client_id, client_secret = client_id_and_secret
    api_client = get_api_client_by_id(dbsession, client_id)
    api_client.enabled = False
    dbsession.commit()
    with caplog.at_level(logging.INFO):
        resp = anon_client.post("/token", auth=HTTPBasicAuth(client_id, client_secret))
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Incorrect username or password"}
    assert caplog.records[0].token_creds_from == "header"
    assert caplog.records[0].token_fail == "Client disabled"


def test_get_ctms_with_token(email_factory, anon_client, test_token_settings, client_id_and_secret):
    """An authenticated API can be fetched with a valid token"""
    email = email_factory()

    client_id = client_id_and_secret[0]
    token = create_access_token({"sub": f"api_client:{client_id}"}, **test_token_settings)
    token_headers = jwt.get_unverified_header(token)
    assert token_headers == {
        "alg": "HS256",
        "typ": "JWT",
    }
    resp = anon_client.get(
        f"/ctms/{email.email_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


def test_successful_login_tracks_last_access(dbsession, email_factory, anon_client, test_token_settings, client_id_and_secret):
    client_id = client_id_and_secret[0]
    email = email_factory()

    api_client = get_api_client_by_id(dbsession, client_id)
    before = api_client.last_access

    token = create_access_token({"sub": f"api_client:{client_id}"}, **test_token_settings)
    anon_client.get(
        f"/ctms/{email.email_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    dbsession.flush()
    after = get_api_client_by_id(dbsession, client_id).last_access
    assert before != after


def test_get_ctms_with_invalid_token_fails(email_factory, anon_client, test_token_settings, client_id_and_secret, caplog):
    """Calling an authenticated API with an invalid token is an error"""
    email = email_factory()

    client_id = client_id_and_secret[0]
    token = create_access_token(
        {"sub": f"api_client:{client_id}"},
        secret_key="secret_key_from_other_deploy",  # pragma: allowlist secret
        expires_delta=test_token_settings["expires_delta"],
    )
    with caplog.at_level(logging.INFO):
        resp = anon_client.get(
            f"/ctms/{email.email_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Could not validate credentials"}
    assert caplog.records[0].auth_fail == "No or bad token"


def test_get_ctms_with_invalid_namespace_fails(email_factory, anon_client, test_token_settings, client_id_and_secret, caplog):
    """Calling an authenticated API with an unexpected namespace is an error"""
    email = email_factory()

    client_id = client_id_and_secret[0]
    token = create_access_token({"sub": f"unknown:{client_id}"}, **test_token_settings)
    with caplog.at_level(logging.INFO):
        resp = anon_client.get(
            f"/ctms/{email.email_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Could not validate credentials"}
    assert caplog.records[0].auth_fail == "Bad namespace"


def test_get_ctms_with_unknown_client_fails(email_factory, anon_client, test_token_settings, client_id_and_secret, caplog):
    """A token with an unknown (deleted?) API client name is an error"""
    email = email_factory()

    client_id = client_id_and_secret[0]
    token = create_access_token({"sub": f"api_client:not_{client_id}"}, **test_token_settings)
    with caplog.at_level(logging.INFO):
        resp = anon_client.get(
            f"/ctms/{email.email_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Could not validate credentials"}
    assert caplog.records[0].auth_fail == "No client record"


def test_get_ctms_with_expired_token_fails(email_factory, anon_client, test_token_settings, client_id_and_secret, caplog):
    """Calling an authenticated API with an expired token is an error"""
    email = email_factory()

    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    client_id = client_id_and_secret[0]
    token = create_access_token({"sub": f"api_client:{client_id}"}, **test_token_settings, now=yesterday)
    with caplog.at_level(logging.INFO):
        resp = anon_client.get(
            f"/ctms/{email.email_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Could not validate credentials"}
    assert caplog.records[0].auth_fail == "No or bad token"


def test_get_ctms_with_disabled_client_fails(
    dbsession,
    email_factory,
    anon_client,
    test_token_settings,
    client_id_and_secret,
    caplog,
):
    """Calling an authenticated API with a valid token for an expired client is an error."""
    email = email_factory()

    client_id = client_id_and_secret[0]
    token = create_access_token({"sub": f"api_client:{client_id}"}, **test_token_settings)
    api_client = get_api_client_by_id(dbsession, client_id)
    api_client.enabled = False
    dbsession.commit()

    with caplog.at_level(logging.INFO):
        resp = anon_client.get(
            f"/ctms/{email.email_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400
    assert resp.json() == {"detail": "API Client has been disabled"}
    assert caplog.records[0].auth_fail == "Client disabled"


def test_hashed_passwords():
    """Hashed passwords have unique salts"""
    hashed1 = hash_password("password")
    assert hashed1 != "password"
    assert verify_password("password", hashed1)
    assert not verify_password("xpassword", hashed1)

    hashed2 = hash_password("password")
    assert verify_password("password", hashed1)
    assert hashed1 != hashed2
