# -*- coding: utf-8 -*-
"""Tests for logging helpers"""
from unittest.mock import patch

import pytest
from requests.auth import HTTPBasicAuth
from structlog.testing import capture_logs

from ctms.log import configure_logging


def test_request_log(client, minimal_contact):
    """A request is logged."""
    email_id = str(minimal_contact.email.email_id)
    with capture_logs() as cap_logs:
        resp = client.get(
            f"/ctms/{email_id}",
            headers={
                "X-Request-Id": "foo-bar",
            },
        )
    assert resp.status_code == 200
    assert len(cap_logs) == 1
    log = cap_logs[0]
    assert "duration_s" in log
    expected_log = {
        "client_allowed": True,
        "client_host": "testclient",
        "client_id": "test_client",
        "duration_s": log["duration_s"],
        "event": f"testclient:50000 test_client 'GET /ctms/{email_id} HTTP/1.1' 200",
        "headers": {
            "host": "testserver",
            "user-agent": "testclient",
            "accept-encoding": "gzip, deflate",
            "accept": "*/*",
            "connection": "keep-alive",
            "x-request-id": "foo-bar",
        },
        "log_level": "info",
        "method": "GET",
        "path": f"/ctms/{email_id}",
        "path_params": {"email_id": email_id},
        "path_template": "/ctms/{email_id}",
        "status_code": 200,
        "rid": "foo-bar",
    }
    assert log == expected_log


def test_token_request_log(anon_client, client_id_and_secret):
    """A token request log has omitted headers."""
    client_id, client_secret = client_id_and_secret
    with capture_logs() as cap_logs:
        resp = anon_client.post(
            "/token",
            data={"grant_type": "client_credentials"},
            auth=HTTPBasicAuth(client_id, client_secret),
            cookies={"csrftoken": "0WzT-base64-string"},
        )
    assert resp.status_code == 200
    assert len(cap_logs) == 1
    log = cap_logs[0]
    assert log["client_id"] == client_id
    assert log["token_creds_from"] == "header"
    assert log["headers"]["authorization"] == "[OMITTED]"
    assert log["headers"]["content-length"] == "29"
    assert log["headers"]["cookie"] == "[OMITTED]"


def test_log_omits_emails(client, email_factory):
    """The logger omits emails from query params."""
    email = email_factory(fxa=True)
    url = (
        f"/ctms?primary_email={email.primary_email}&fxa_primary_email={email.fxa.primary_email}"
        f"&email_id={email.email_id}"
    )
    with capture_logs() as cap_logs:
        resp = client.get(url)
    assert resp.status_code == 200
    assert len(cap_logs) == 1
    log = cap_logs[0]
    assert log["query"] == {
        "email_id": str(email.email_id),
        "fxa_primary_email": "[OMITTED]",
        "primary_email": "[OMITTED]",
    }


def test_log_crash(client):
    """Exceptions are logged."""
    path = "/__crash__"
    with pytest.raises(RuntimeError), capture_logs() as cap_logs:
        client.get(path)
    assert len(cap_logs) == 1
    log = cap_logs[0]
    assert log["log_level"] == "error"
    assert "rid" in log
    assert log["event"] == "testclient:50000 test_client 'GET /__crash__ HTTP/1.1' 500"


@pytest.mark.parametrize(
    "use_mozlog,logging_level",
    (
        (True, "INFO"),
        (False, "WARNING"),
    ),
)
def test_configure_logging(use_mozlog, logging_level):
    with patch("ctms.log.logging.config.dictConfig") as mock_dc:
        configure_logging(use_mozlog, logging_level)
    mock_dc.assert_called_once()
    args = mock_dc.mock_calls[0].args
    assert len(args) == 1
    if use_mozlog:
        handlers = ["mozlog"]
    else:
        handlers = ["humans"]
    assert args[0]["root"] == {"handlers": handlers, "level": logging_level}
    assert args[0]["loggers"]["ctms"]["level"] == logging_level
