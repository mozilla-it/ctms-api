"""Tests for ctms/bin/client_credentials.py"""

import pytest

from ctms.bin.client_credentials import main
from ctms.config import Settings
from ctms.models import ApiClient


@pytest.fixture
def existing_client(dbsession):
    client = ApiClient(
        client_id="id_existing", email="existing@example.com", hashed_secret="password"
    )
    dbsession.add(client)
    dbsession.flush()
    return client


def test_create(dbsession, settings):
    """New client credentials can be generated, with id_ prefixed to the client_id."""
    ret = main(dbsession, settings, ["test", "--email", "test@example.com"])
    assert ret == 0

    client = dbsession.query(ApiClient).one()
    assert client.client_id == "id_test"
    assert client.email == "test@example.com"
    assert client.enabled == True


def test_create_explicit_id(dbsession, settings):
    """A id_ prefix is not added if it is already there."""
    ret = main(dbsession, settings, ["id_tst", "--email", "test@example.com"])
    assert ret == 0

    client = dbsession.query(ApiClient).one()
    assert client.client_id == "id_tst"
    assert client.email == "test@example.com"
    assert client.enabled == True


def test_create_disabled(dbsession, settings):
    """New client credentials can be generated as disabled."""
    ret = main(
        dbsession, settings, ["test2", "--email", "test@example.com", "--disable"]
    )
    assert ret == 0

    client = dbsession.query(ApiClient).one()
    assert client.client_id == "id_test2"
    assert client.email == "test@example.com"
    assert client.enabled == False


def test_create_email_required(dbsession, settings):
    """The email is required when generating new client credentials."""
    ret = main(dbsession, settings, ["test"])
    assert ret == 1

    assert dbsession.query(ApiClient).first() is None


@pytest.mark.parametrize(
    "client_id", ("service.mozilla.com", "1-800-Contacts", "under_score.js")
)
def test_create_valid_client_id(dbsession, settings, client_id):
    """Some punctuation is allowed."""
    ret = main(dbsession, settings, [client_id, "--email", "test@example.com"])
    assert ret == 0

    client = dbsession.query(ApiClient).one()
    assert client.client_id == f"id_{client_id}"
    assert client.email == "test@example.com"
    assert client.enabled == True


@pytest.mark.parametrize("client_id", ("test@example.com", "Résumé", "💩.la"))
def test_create_bad_client_id_fails(dbsession, settings, client_id):
    """A client_id must be alphanume New client credentials can be generated."""
    ret = main(dbsession, settings, [client_id, "--email", "test@example.com"])
    assert ret == 1
    assert dbsession.query(ApiClient).first() is None


def test_update_email(dbsession, settings, existing_client):
    """The email of an existing client can be changed."""
    new_email = "new@example.com"
    assert existing_client.email != new_email
    ret = main(dbsession, settings, [existing_client.client_id, "--email", new_email])
    assert ret == 0

    client = dbsession.query(ApiClient).one()
    assert client.email == new_email


def test_update_disable(dbsession, settings, existing_client):
    """A client can be disabled."""
    assert existing_client.enabled
    ret = main(dbsession, settings, [existing_client.client_id, "--disable"])
    assert ret == 0

    client = dbsession.query(ApiClient).one()
    assert not client.enabled


def test_update_enable(dbsession, settings, existing_client):
    """A disabled client can be enabled."""
    existing_client.enabled = False
    dbsession.flush()
    ret = main(dbsession, settings, [existing_client.client_id, "--enable"])
    assert ret == 0

    client = dbsession.query(ApiClient).one()
    assert client.enabled


def test_update_enable_and_disable_fails(dbsession, settings, existing_client):
    """Picking enable and disable is an error."""
    ret = main(
        dbsession, settings, [existing_client.client_id, "--disable", "--enable"]
    )
    assert ret == 1
    client = dbsession.query(ApiClient).one()
    assert client.enabled


def test_update_secret(dbsession, settings, existing_client):
    """A client can get new credentials."""
    old_secret = existing_client.hashed_secret
    ret = main(dbsession, settings, [existing_client.client_id, "--rotate-secret"])
    assert ret == 0

    client = dbsession.query(ApiClient).one()
    assert client.hashed_secret != old_secret


def test_update_nothing(dbsession, settings, existing_client):
    """It is valid to do nothing to an existing client."""
    ret = main(dbsession, settings, [existing_client.client_id])
    assert ret == 0

    client = dbsession.query(ApiClient).one()
    assert client.client_id == existing_client.client_id
