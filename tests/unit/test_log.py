"""Tests for logging helpers"""

import logging

import pytest
from dockerflow.logging import JsonLogFormatter
from requests.auth import HTTPBasicAuth

from tests.conftest import FuzzyAssert


def test_request_log(client, email_factory, caplog):
    """A request is logged."""
    email = email_factory()
    email_id = str(email.email_id)

    with caplog.at_level(logging.INFO, logger="request.summary"):
        resp = client.get(
            f"/ctms/{email_id}",
            headers={
                "X-Request-Id": "foo-bar",
            },
        )

    assert resp.status_code == 200
    assert len(caplog.records) == 1
    log = caplog.records[0]

    expected_log = {
        "client_allowed": True,
        "client_id": "test_client",
        "uid": "test_client",
        "agent": "testclient",
        "method": "GET",
        "path": f"/ctms/{email_id}",
        "code": 200,
        "lang": None,
        "rid": "foo-bar",
        "t": FuzzyAssert(lambda x: x > 0, name="uint"),
    }
    fmtr = JsonLogFormatter()
    assert fmtr.convert_record(log)["Fields"] == expected_log


def test_token_request_log(anon_client, client_id_and_secret, caplog):
    """A token request log has omitted headers."""
    client_id, client_secret = client_id_and_secret
    with caplog.at_level(logging.INFO):
        anon_client.cookies.set("csrftoken", "0WzT-base64-string")
        resp = anon_client.post(
            "/token",
            data={"grant_type": "client_credentials"},
            auth=HTTPBasicAuth(client_id, client_secret),
        )
    assert resp.status_code == 200
    assert len(caplog.records) == 1
    log = caplog.records[0]
    assert log.client_id == client_id
    assert log.token_creds_from == "header"


def test_log_omits_emails(client, email_factory, caplog):
    """The logger omits emails from query params."""
    email = email_factory(with_fxa=True)
    url = f"/ctms?primary_email={email.primary_email}&fxa_primary_email={email.fxa.primary_email}&email_id={email.email_id}"
    with caplog.at_level(logging.INFO):
        resp = client.get(url)
    assert resp.status_code == 200
    assert len(caplog.records) == 1
    log = caplog.records[0]
    assert email.primary_email not in log.message
    assert email.fxa.primary_email not in log.message
    assert str(email.email_id) not in log.message


def test_log_crash(client, caplog):
    """Exceptions are logged."""
    path = "/__crash__"
    with pytest.raises(RuntimeError), caplog.at_level(logging.INFO):
        client.get(path)
    assert len(caplog.records) == 1
    log = caplog.records[0]
    assert hasattr(log, "rid") and log.rid is not None
