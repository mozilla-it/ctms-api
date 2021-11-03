"""Test authentication"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from google.auth.exceptions import TransportError
from jose import jwt
from requests.auth import HTTPBasicAuth
from structlog.testing import capture_logs

from ctms.app import _pubsub_settings, _token_settings, app, get_settings
from ctms.auth import create_access_token, hash_password, verify_password
from ctms.crud import get_api_client_by_id
from tests.unit.test_api_stripe import pubsub_wrap
from tests.unit.test_ingest_stripe import stripe_customer_data

# Sample token claim from https://cloud.google.com/pubsub/docs/push
SAMPLE_GCP_JWT_CLAIM = {
    "aud": "https://example.com",
    "azp": "113774264463038321964",
    "email": "gae-gcp@appspot.gserviceaccount.com",
    "sub": "113774264463038321964",
    "email_verified": True,
    "exp": 1550185935,
    "iat": 1550182335,
    "iss": "https://accounts.google.com",
}


@pytest.fixture
def test_token_settings():
    """Set token settings for tests."""

    settings = {
        "expires_delta": timedelta(minutes=5),
        "secret_key": "AN_AWESOME_RANDOM_SECRET_KEY",
    }

    app.dependency_overrides[_token_settings] = lambda: settings
    yield settings
    del app.dependency_overrides[_token_settings]


@pytest.fixture
def test_pubsub_settings():
    """Set pubsub settings for tests."""

    settings = {
        "audience": "https://example.com",
        "email": "gae-gcp@appspot.gserviceaccount.com",
        "client": "a_shared_secret",
    }

    app.dependency_overrides[_pubsub_settings] = lambda: settings
    yield settings
    del app.dependency_overrides[_pubsub_settings]


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
        datetime.now(timezone.utc) + test_token_settings["expires_delta"]
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
        datetime.now(timezone.utc) + test_token_settings["expires_delta"]
    ).timestamp()
    assert -2.0 < (expected_expires - payload["exp"]) < 2.0


def test_post_token_succeeds_no_grant(anon_client, client_id_and_secret):
    """If grant_type is omitted, client_credentials is assumed."""
    resp = anon_client.post(
        "/token",
        auth=HTTPBasicAuth(*client_id_and_secret),
    )
    assert resp.status_code == 200


def test_post_token_succeeds_refresh_grant(
    anon_client, test_token_settings, client_id_and_secret
):
    """If grant_type is refresh_token, the token grant is successful."""
    client_id, client_secret = client_id_and_secret
    resp = anon_client.post(
        "/token",
        {
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
        {"grant_type": "password"},
        auth=HTTPBasicAuth(*client_id_and_secret),
    )
    assert resp.status_code == 422
    pattern = "^(client_credentials|refresh_token)$"
    assert resp.json()["detail"][0] == {
        "ctx": {"pattern": pattern},
        "loc": ["body", "grant_type"],
        "msg": f'string does not match regex "{pattern}"',
        "type": "value_error.str.regex",
    }


def test_post_token_fails_no_credentials(anon_client, dbsession):
    """If no credentials are passed, token generation fails."""
    with capture_logs() as caplog:
        resp = anon_client.post("/token", {"grant_type": "client_credentials"})
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Incorrect username or password"}
    assert caplog[0]["token_fail"] == "No credentials"


def test_post_token_fails_unknown_api_client(
    dbsession, anon_client, client_id_and_secret
):
    """Authentication failes on unknown api_client ID."""
    good_id, good_secret = client_id_and_secret
    with capture_logs() as caplog:
        resp = anon_client.post(
            "/token", auth=HTTPBasicAuth(good_id + "x", good_secret)
        )
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Incorrect username or password"}
    assert caplog[0]["token_creds_from"] == "header"
    assert caplog[0]["token_fail"] == "No client record"


def test_post_token_fails_bad_credentials(anon_client, client_id_and_secret):
    """Authentication fails on bad credentials."""
    good_id, good_secret = client_id_and_secret
    with capture_logs() as caplog:
        resp = anon_client.post(
            "/token", auth=HTTPBasicAuth(good_id, good_secret + "x")
        )
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Incorrect username or password"}
    assert caplog[0]["token_creds_from"] == "header"
    assert caplog[0]["token_fail"] == "Bad credentials"


def test_post_token_fails_disabled_client(dbsession, anon_client, client_id_and_secret):
    """Authentication fails when the client is disabled."""
    client_id, client_secret = client_id_and_secret
    api_client = get_api_client_by_id(dbsession, client_id)
    api_client.enabled = False
    dbsession.commit()
    with capture_logs() as caplog:
        resp = anon_client.post("/token", auth=HTTPBasicAuth(client_id, client_secret))
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Incorrect username or password"}
    assert caplog[0]["token_creds_from"] == "header"
    assert caplog[0]["token_fail"] == "Client disabled"


def test_get_ctms_with_token(
    example_contact, anon_client, test_token_settings, client_id_and_secret
):
    """An authenticated API can be fetched with a valid token"""
    client_id = client_id_and_secret[0]
    token = create_access_token(
        {"sub": f"api_client:{client_id}"}, **test_token_settings
    )
    token_headers = jwt.get_unverified_headers(token)
    assert token_headers == {
        "alg": "HS256",
        "typ": "JWT",
    }
    resp = anon_client.get(
        f"/ctms/{example_contact.email.email_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


def test_get_ctms_with_invalid_token_fails(
    example_contact, anon_client, test_token_settings, client_id_and_secret
):
    """Calling an authenticated API with an invalid token is an error"""
    client_id = client_id_and_secret[0]
    token = create_access_token(
        {"sub": f"api_client:{client_id}"},
        secret_key="secret_key_from_other_deploy",
        expires_delta=test_token_settings["expires_delta"],
    )
    with capture_logs() as caplog:
        resp = anon_client.get(
            f"/ctms/{example_contact.email.email_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Could not validate credentials"}
    assert caplog[0]["auth_fail"] == "No or bad token"


def test_get_ctms_with_invalid_namespace_fails(
    example_contact, anon_client, test_token_settings, client_id_and_secret
):
    """Calling an authenticated API with an unexpected namespace is an error"""
    client_id = client_id_and_secret[0]
    token = create_access_token({"sub": f"unknown:{client_id}"}, **test_token_settings)
    with capture_logs() as caplog:
        resp = anon_client.get(
            f"/ctms/{example_contact.email.email_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Could not validate credentials"}
    assert caplog[0]["auth_fail"] == "Bad namespace"


def test_get_ctms_with_unknown_client_fails(
    example_contact, anon_client, test_token_settings, client_id_and_secret
):
    """A token with an unknown (deleted?) API client name is an error"""
    client_id = client_id_and_secret[0]
    token = create_access_token(
        {"sub": f"api_client:not_{client_id}"}, **test_token_settings
    )
    with capture_logs() as caplog:
        resp = anon_client.get(
            f"/ctms/{example_contact.email.email_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Could not validate credentials"}
    assert caplog[0]["auth_fail"] == "No client record"


def test_get_ctms_with_expired_token_fails(
    example_contact, anon_client, test_token_settings, client_id_and_secret
):
    """Calling an authenticated API with an expired token is an error"""
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    client_id = client_id_and_secret[0]
    token = create_access_token(
        {"sub": f"api_client:{client_id}"}, **test_token_settings, now=yesterday
    )
    with capture_logs() as caplog:
        resp = anon_client.get(
            f"/ctms/{example_contact.email.email_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Could not validate credentials"}
    assert caplog[0]["auth_fail"] == "No or bad token"


def test_get_ctms_with_disabled_client_fails(
    dbsession, example_contact, anon_client, test_token_settings, client_id_and_secret
):
    """Calling an authenticated API with a valid token for an expired client is an error."""
    client_id = client_id_and_secret[0]
    token = create_access_token(
        {"sub": f"api_client:{client_id}"}, **test_token_settings
    )
    api_client = get_api_client_by_id(dbsession, client_id)
    api_client.enabled = False
    dbsession.commit()

    with capture_logs() as caplog:
        resp = anon_client.get(
            f"/ctms/{example_contact.email.email_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400
    assert resp.json() == {"detail": "API Client has been disabled"}
    assert caplog[0]["auth_fail"] == "Client disabled"


def test_hashed_passwords():
    """Hashed passwords have unique salts"""
    hashed1 = hash_password("password")
    assert hashed1 != "password"
    assert verify_password("password", hashed1)
    assert not verify_password("xpassword", hashed1)

    hashed2 = hash_password("password")
    assert verify_password("password", hashed1)
    assert hashed1 != hashed2


def test_post_pubsub_token(dbsession, anon_client, test_pubsub_settings):
    """A PubSub client can authenticate."""

    with patch("ctms.app.get_claim_from_pubsub_token") as mock_get:
        mock_get.return_value = SAMPLE_GCP_JWT_CLAIM
        with capture_logs() as caplog:
            resp = anon_client.post(
                "/stripe_from_pubsub?pubsub_client=a_shared_secret",
                headers={"Authorization": "Bearer gcp_generated_token"},
                json=pubsub_wrap(stripe_customer_data()),
            )
    assert resp.status_code == 200, resp.json()
    assert len(caplog) == 1
    log = caplog[0]
    assert "auth_fail" not in log
    assert log["client_allowed"]
    assert log["pubsub_email"] == "gae-gcp@appspot.gserviceaccount.com"


@pytest.mark.parametrize("name", ("pubsub_email", "pubsub_client"))
def test_post_pubsub_token_checks_settings(dbsession, anon_client, name):
    """PubSub fails if settings are unset."""

    class FakeSettings:
        pubsub_audience = "https://example.com"  # Unchecked due to fallback
        pubsub_email = "gae-gcp@appspot.gserviceaccount.com"
        pubsub_client = "a_shared_secret"

    settings = FakeSettings()
    setattr(settings, name, None)
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with pytest.raises(Exception, match=f"{name.upper()} is unset"):
            resp = anon_client.post(
                "/stripe_from_pubsub?pubsub_client=a_shared_secret",
                headers={"Authorization": "Bearer a_fake_token"},
                json=pubsub_wrap(stripe_customer_data()),
            )
            assert resp.status_code == 500
    finally:
        del app.dependency_overrides[get_settings]


def test_post_pubsub_token_fail_client(dbsession, anon_client, test_pubsub_settings):
    """An error is returned if pubsub_client is incorrect."""
    with patch("ctms.app.get_claim_from_pubsub_token") as mock_get:
        mock_get.side_effect = Exception("Should not be called.")
        with capture_logs() as caplog:
            resp = anon_client.post(
                "/stripe_from_pubsub?pubsub_client=the_wrong_secret",
                headers={"Authorization": "Bearer a_fake_token"},
                json=pubsub_wrap(stripe_customer_data()),
            )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Could not validate credentials"}
    assert len(caplog) == 1
    assert caplog[0]["auth_fail"] == "Verification mismatch"


def test_post_pubsub_token_unknown_key(dbsession, anon_client, test_pubsub_settings):
    """An error is returned if the jwt 'kid' doesn't refer to a known cert."""
    with patch("ctms.app.get_claim_from_pubsub_token") as mock_get:
        mock_get.side_effect = ValueError(
            "Certificate for key id the_kid_value not found."
        )
        with capture_logs() as caplog:
            resp = anon_client.post(
                "/stripe_from_pubsub?pubsub_client=a_shared_secret",
                headers={"Authorization": "Bearer a_fake_token"},
                json=pubsub_wrap(stripe_customer_data()),
            )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Could not validate credentials"}
    assert len(caplog) == 1
    assert caplog[0]["auth_fail"] == "Unknown key"


def test_post_pubsub_token_fail_ssl_fetch(dbsession, anon_client, test_pubsub_settings):
    """An error is returned if there is an issue fetching certs."""
    with patch("ctms.app.get_claim_from_pubsub_token") as mock_get:
        mock_get.side_effect = TransportError(
            "Could not fetch certificates at https://example.com"
        )
        with capture_logs() as caplog:
            resp = anon_client.post(
                "/stripe_from_pubsub?pubsub_client=a_shared_secret",
                headers={"Authorization": "Bearer a_fake_token"},
                json=pubsub_wrap(stripe_customer_data()),
            )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Could not validate credentials"}
    assert len(caplog) == 1
    assert caplog[0]["auth_fail"] == "Google authentication failure"


def test_post_pubsub_token_fail_wrong_email(
    dbsession, anon_client, test_pubsub_settings
):
    """An error is returned if the claim email doesn't match."""
    claim = SAMPLE_GCP_JWT_CLAIM.copy()
    claim["email"] = "different_email@example.com"
    with patch("ctms.app.get_claim_from_pubsub_token") as mock_get:
        mock_get.return_value = claim
        with capture_logs() as caplog:
            resp = anon_client.post(
                "/stripe_from_pubsub?pubsub_client=a_shared_secret",
                headers={"Authorization": "Bearer a_fake_token"},
                json=pubsub_wrap(stripe_customer_data()),
            )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Could not validate credentials"}
    assert len(caplog) == 1
    log = caplog[0]
    assert log["auth_fail"] == "Wrong email"
    assert log["pubsub_email"] == "different_email@example.com"
    assert log["pubsub_email_verified"]


def test_post_pubsub_token_fail_unverified_email(
    dbsession, anon_client, test_pubsub_settings
):
    """An error is returned if the claim email isn't verified."""
    claim = SAMPLE_GCP_JWT_CLAIM.copy()
    del claim["email_verified"]
    with patch("ctms.app.get_claim_from_pubsub_token") as mock_get:
        mock_get.return_value = claim
        with capture_logs() as caplog:
            resp = anon_client.post(
                "/stripe_from_pubsub?pubsub_client=a_shared_secret",
                headers={"Authorization": "Bearer a_fake_token"},
                json=pubsub_wrap(stripe_customer_data()),
            )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Could not validate credentials"}
    assert len(caplog) == 1
    log = caplog[0]
    assert log["auth_fail"] == "Email not verified"
    assert log["pubsub_email"] == "gae-gcp@appspot.gserviceaccount.com"
    assert "pubsub_email_verified" not in log
