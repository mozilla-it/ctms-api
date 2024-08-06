# -*- coding: utf-8 -*-
"""Tests for logging helpers"""

import logging
from unittest.mock import patch

import pytest
from requests.auth import HTTPBasicAuth
from dockerflow.logging import JsonLogFormatter


def test_request_log(client, email_factory, caplog):
    """A request is logged."""
    email = email_factory()
    email_id = str(email.email_id)

    with caplog.at_level(logging.INFO, logger="ctms.web"):
        resp = client.get(
            f"/ctms/{email_id}",
            headers={
                "X-Request-Id": "foo-bar",
            },
        )

    assert resp.status_code == 200
    assert len(caplog.records) == 1
    log = caplog.records[0]
    assert hasattr(log, "duration_s")
    expected_log = {
        "client_allowed": True,
        "client_host": "testclient",
        "client_id": "test_client",
        "duration_s": log.duration_s,
        "msg": f"testclient:50000 test_client 'GET /ctms/{email_id} HTTP/1.1' 200",
        "headers": {
            "host": "testserver",
            "user-agent": "testclient",
            "accept-encoding": "gzip, deflate",
            "accept": "*/*",
            "connection": "keep-alive",
            "x-request-id": "foo-bar",
        },
        "method": "GET",
        "path": f"/ctms/{email_id}",
        "path_params": {"email_id": email_id},
        "path_template": "/ctms/{email_id}",
        "status_code": 200,
        "rid": "foo-bar",
    }
    fmtr = JsonLogFormatter()
    assert fmtr.convert_record(log)["Fields"] == expected_log


def test_token_request_log(anon_client, client_id_and_secret, caplog):
    """A token request log has omitted headers."""
    client_id, client_secret = client_id_and_secret
    with caplog.at_level(logging.INFO, logger="ctms.web"):
        resp = anon_client.post(
            "/token",
            data={"grant_type": "client_credentials"},
            auth=HTTPBasicAuth(client_id, client_secret),
            cookies={"csrftoken": "0WzT-base64-string"},
        )
    assert resp.status_code == 200
    assert len(caplog.records) == 1
    log = caplog.records[0]
    assert log.client_id == client_id
    assert log.token_creds_from == "header"
    assert log.headers["authorization"] == "[OMITTED]"
    assert log.headers["content-length"] == "29"
    assert log.headers["cookie"] == "[OMITTED]"


def test_log_omits_emails(client, email_factory, caplog):
    """The logger omits emails from query params."""
    email = email_factory(with_fxa=True)
    url = (
        f"/ctms?primary_email={email.primary_email}&fxa_primary_email={email.fxa.primary_email}"
        f"&email_id={email.email_id}"
    )
    with caplog.at_level(logging.INFO, logger="ctms.web"):
        resp = client.get(url)
    assert resp.status_code == 200
    assert len(caplog.records) == 1
    log = caplog.records[0]
    assert log.query == {
        "email_id": str(email.email_id),
        "fxa_primary_email": "[OMITTED]",
        "primary_email": "[OMITTED]",
    }


def test_log_crash(client, caplog):
    """Exceptions are logged."""
    path = "/__crash__"
    with pytest.raises(RuntimeError), caplog.at_level(logging.ERROR):
        client.get(path)
    assert len(caplog.records) == 1
    log = caplog.records[0]
    assert hasattr(log, "rid") and log.rid is not None
    assert log.msg == "testclient:50000 test_client 'GET /__crash__ HTTP/1.1' 500"
