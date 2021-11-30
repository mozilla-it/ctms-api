"""pytest tests for basic app functionality"""

import json
import os.path

import pytest
from structlog.testing import capture_logs


def test_read_root(anon_client):
    """The site root redirects to the Swagger docs"""
    with capture_logs() as caplogs:
        resp = anon_client.get("/")
    assert resp.status_code == 200
    assert len(resp.history) == 1
    prev_resp = resp.history[0]
    assert prev_resp.status_code == 307  # Temporary Redirect
    assert prev_resp.headers["location"] == "./docs"
    assert len(caplogs) == 2
    assert caplogs[0]["trivial"] is True
    assert "trivial" not in caplogs[1]


def test_read_version(anon_client):
    """__version__ returns the contents of version.json."""
    here = os.path.dirname(__file__)
    root_dir = os.path.dirname(os.path.dirname(here))
    version_path = os.path.join(root_dir, "version.json")
    with open(version_path, "r", encoding="utf8") as vp_file:
        version_contents = vp_file.read()
    expected = json.loads(version_contents)
    resp = anon_client.get("/__version__")
    assert resp.status_code == 200
    assert resp.json() == expected


def test_crash_authorized(client):
    """The endpoint /__crash__ can be used to test Sentry integration."""
    with pytest.raises(RuntimeError):
        client.get("/__crash__")


def test_crash_unauthorized(anon_client):
    """The endpoint /__crash__ can not be used without credentials."""
    resp = anon_client.get("/__crash__")
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Not authenticated"}
