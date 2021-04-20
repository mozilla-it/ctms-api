# -*- coding: utf-8 -*-
"""Tests for logging helpers"""
from unittest.mock import Mock

import pytest

from ctms.app import app, create_or_update_ctms_contact, login, root
from ctms.logging import UvicornJsonLogFormatter


@pytest.fixture
def formatter():
    return UvicornJsonLogFormatter(logger_name="ctms", log_dropped_fields=True)


def test_uvicorn_mozlog_drop_color_message(formatter):
    """UvicornJsonLogFormatter drops color_message, sent by some error logs."""
    fields_in = {
        "color_message": "Finished server process [\u001b[36m%d\u001b[0m]",
        "msg": "Finished server process [30]",
    }
    out = formatter.convert_fields(fields_in)
    assert out == {
        "dropped_fields": ["color_message"],
        "msg": "Finished server process [30]",
    }


def test_uvicorn_mozlog_silent_drop_fields():
    """The field dropped_fields can be omitted."""
    fmt = UvicornJsonLogFormatter(logger_name="ctms", log_dropped_fields=False)
    fields_in = {
        "color_message": "Finished server process [\u001b[36m%d\u001b[0m]",
        "msg": "Finished server process [30]",
    }
    out = fmt.convert_fields(fields_in)
    assert out == {"msg": "Finished server process [30]"}


def test_uvicorn_mozlog_root_path_call(formatter):
    """
    UvicornJsonLogFormatter converts the 307 redirect from calling /.

    This is similar to a call in the local development environment.
    """
    fields_in = {
        "status_code": 307,
        "scope": {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.1"},
            "http_version": "1.1",
            "server": ["172.19.0.3", 8000],
            "client": ["172.19.0.1", 56988],
            "scheme": "http",
            "method": "GET",
            "root_path": "",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": [
                [b"host", b"localhost:8000"],
                [b"accept", b"text/html,application/xhtml+xml"],
                [b"upgrade-insecure-requests", b"1"],
                [b"cookie", b"csrftoken=0WzTs-more-base64"],
                [b"user-agent", b"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6)"],
                [b"accept-language", b"en-us"],
                [b"accept-encoding", b"gzip, deflate"],
                [b"connection", b"keep-alive"],
            ],
            "fastapi_astack": Mock(),
            "app": app,
            "router": Mock(),
            "endpoint": root,
            "path_params": {},
            "state": {
                "log_context": {
                    "duration_s": 0.017,
                }
            },
        },
        "msg": '172.19.0.1:56988 - "GET / HTTP/1.1" 307',
    }
    out = formatter.convert_fields(fields_in)
    assert out == {
        "client_ip": "172.19.0.1",
        "client_port": 56988,
        "dropped_fields": [
            "scope.app",
            "scope.asgi",
            "scope.fastapi_astack",
            "scope.raw_path",
            "scope.root_path",
            "scope.router",
        ],
        "duration_s": 0.017,
        "endpoint": "root",
        "headers": {
            "accept": "text/html,application/xhtml+xml",
            "accept-encoding": "gzip, deflate",
            "accept-language": "en-us",
            "connection": "keep-alive",
            "cookie": "[OMITTED]",
            "host": "localhost:8000",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6)",
        },
        "http_version": "1.1",
        "method": "GET",
        "msg": '172.19.0.1:56988 - "GET / HTTP/1.1" 307',
        "path": "/",
        "path_params": {},
        "query": {},
        "scheme": "http",
        "server_ip": "172.19.0.3",
        "server_port": 8000,
        "status_code": 307,
        "type": "http",
    }


def test_uvicorn_mozlog_token_request(formatter):
    """
    UvicornJsonLogFormatter converts the 200 from a successful token request.

    This is similar to a call in the local development environment,
    but omits most fields from previous tests.
    """
    fields_in = {
        "status_code": 200,
        "scope": {
            "method": "POST",
            "headers": [
                [b"authorization", b"Basic base64-string"],
                [b"x-requested-with", b"XMLHttpRequest"],
                [b"content-type", b"application/x-www-form-urlencoded"],
                [b"content-length", b"29"],
                [b"referer", b"http://localhost:8000/docs"],
                [b"origin", b"http://localhost:8000"],
                [b"cookie", b"csrftoken=0WzT-base64-string"],
            ],
            "path": "/token",
            "endpoint": login,
        },
        "msg": '172.19.0.1:57002 - "POST /token HTTP/1.1" 200',
    }
    out = formatter.convert_fields(fields_in)
    assert out == {
        "endpoint": "login",
        "headers": {
            "authorization": "[OMITTED]",
            "content-length": "29",
            "content-type": "application/x-www-form-urlencoded",
            "cookie": "[OMITTED]",
            "origin": "http://localhost:8000",
            "referer": "http://localhost:8000/docs",
            "x-requested-with": "XMLHttpRequest",
        },
        "method": "POST",
        "msg": '172.19.0.1:57002 - "POST /token HTTP/1.1" 200',
        "path": "/token",
        "status_code": 200,
    }


def test_uvicorn_mozlog_put_api_call(formatter):
    """
    UvicornJsonLogFormatter converts the 303 from a successful PUT request.

    This is similar to a call in the local development environment,
    but omits most fields from previous tests.
    """
    fields_in = {
        "status_code": 303,
        "scope": {
            "method": "PUT",
            "path": "/ctms/e1d35779-9f14-4553-b2aa-85f9629f68bb",
            "headers": [
                [b"authorization", b"Bearer eyJh-base64-string"],
                [b"content-length", b"1300"],
                [b"cookie", b"csrftoken=a-base64-string"],
            ],
            "endpoint": create_or_update_ctms_contact,
            "path_params": {"email_id": "e1d35779-9f14-4553-b2aa-85f9629f68bb"},
            "state": {
                "log_context": {
                    "duration_s": 0.116,
                    "client_id": "id_test",
                    "client_allowed": True,
                }
            },
        },
        "msg": '172.19.0.1:57014 - "PUT /ctms/e1d35779-9f14-4553-b2aa-85f9629f68bb HTTP/1.1" 303',
    }
    out = formatter.convert_fields(fields_in)
    assert out == {
        "client_allowed": True,
        "client_id": "id_test",
        "duration_s": 0.116,
        "endpoint": "create_or_update_ctms_contact",
        "headers": {
            "authorization": "[OMITTED]",
            "content-length": "1300",
            "cookie": "[OMITTED]",
        },
        "method": "PUT",
        "msg": (
            "172.19.0.1:57014 - "
            '"PUT /ctms/e1d35779-9f14-4553-b2aa-85f9629f68bb HTTP/1.1"'
            " 303"
        ),
        "path": "/ctms/e1d35779-9f14-4553-b2aa-85f9629f68bb",
        "path_params": {"email_id": "e1d35779-9f14-4553-b2aa-85f9629f68bb"},
        "status_code": 303,
    }


def test_uvicorn_mozlog_non_ascii_header_value(formatter):
    """
    A non-ascii header value is added to the log as bytes

    curl refuses to send these, so this is theoretical.
    """
    fields_in = {
        "scope": {
            "headers": [
                [b"x-star", "✰".encode("utf8")],
            ],
        },
    }
    out = formatter.convert_fields(fields_in)
    assert out == {
        "bytes_fields": ["headers.x-star"],
        "headers": {"x-star": b"\xe2\x9c\xb0"},
    }


def test_uvicorn_mozlog_non_ascii_header_name(formatter):
    """
    A non-ascii header is added to the log as bytes

    Currently, uvicorn rejects requests with invalid headers,
    so this code path is even more theoretical.
    """
    fields_in = {
        "scope": {
            "headers": [
                ["x-✰".encode("utf8"), b"star"],
            ],
        },
    }
    out = formatter.convert_fields(fields_in)
    assert out == {
        "bytes_fields": ["headers"],
        "headers": {b"x-\xe2\x9c\xb0": "star"},
    }


def test_uvicorn_mozlog_non_ascii_path(formatter):
    """
    A non-ascii path is added to the log as bytes

    Currently, uvicorn rejects requests with unicode paths,
    so this code path is even more theoretical.
    """
    fields_in = {
        "scope": {
            "path": "/✰".encode("utf8"),
        }
    }
    out = formatter.convert_fields(fields_in)
    assert out == {
        "bytes_fields": ["path"],
        "path": b"/\xe2\x9c\xb0",
    }


def test_uvicorn_mozlog_duplicate_headers(formatter):
    """A repeated header is reported as a list."""
    fields_in = {
        "scope": {
            "headers": [
                [b"x-decision", b"yes"],
                [b"x-decision", b"no"],
                [b"x-decision", b"maybe"],
                [b"x-decision", b"I don't know"],
                [b"x-decision", b"Can you repeat the question?"],
            ]
        }
    }
    out = formatter.convert_fields(fields_in)
    assert out == {
        "headers": {
            "x-decision": [
                "yes",
                "no",
                "maybe",
                "I don't know",
                "Can you repeat the question?",
            ]
        },
        "headers_have_duplicates": True,
    }


def test_uvicorn_mozlog_string_header(formatter):
    """If a header is already a string, it is kept a string."""
    fields_in = {"scope": {"headers": [["x-unicode", "✓"]]}}
    out = formatter.convert_fields(fields_in)
    assert out == {
        "headers": {"x-unicode": "✓"},
    }


def test_uvicorn_mozlog_string_object(formatter):
    """
    If a header is an object, is is kept as an object.

    This would be an assertion, but we're in logging, so don't raise.
    """
    fields_in = {"scope": {"headers": [["x-set", {}]]}}
    out = formatter.convert_fields(fields_in)
    assert out == {
        "bytes_fields": ["headers.x-set"],
        "headers": {"x-set": {}},
    }


@pytest.mark.parametrize(
    "querystring,query",
    (
        (b"primary_email=test@example.com", {"primary_email": "[OMITTED]"}),
        (b"fxa_primary_email=test@example.com", {"fxa_primary_email": "[OMITTED]"}),
        (b"email_id=a-uuid", {"email_id": "a-uuid"}),
        (
            b"start=2020-04-19T21:03&end=&limit=10",
            {"start": "2020-04-19T21:03", "end": "", "limit": "10"},
        ),
        (b"a=1&a=2", {"a": ["1", "2"]}),
    ),
)
def test_uvicorn_mozlog_querystring(formatter, querystring, query):
    """The querystring is parsed, and emails are omitted."""
    fields_in = {"scope": {"query_string": querystring}}
    out = formatter.convert_fields(fields_in)
    assert out == {"query": query}


def test_uvicorn_mozlog_invalid_querystring(formatter):
    """An invalid querystring is not parsed."""
    fields_in = {"scope": {"query_string": b"invalid&&="}}
    out = formatter.convert_fields(fields_in)
    assert out == {"query_string": "invalid&&="}


def test_uvicorn_mozlog_nonascii_querystring(formatter):
    """An non-ASCII querystring is not parsed."""
    fields_in = {"scope": {"query_string": "star=✰".encode("utf8")}}
    out = formatter.convert_fields(fields_in)
    assert out == {
        "bytes_fields": ["query_string"],
        "query_string": b"star=\xe2\x9c\xb0",
    }
