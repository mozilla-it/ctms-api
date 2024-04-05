import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import TimeoutError as SQATimeoutError
from structlog.testing import capture_logs

from ctms.app import app
from ctms.dependencies import get_db


@pytest.fixture
def mock_db():
    """Mock the database session."""
    mocked_db = Mock()

    def mock_get_db():
        yield mocked_db

    app.dependency_overrides[get_db] = mock_get_db
    yield mocked_db
    del app.dependency_overrides[get_db]


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


def test_read_version(anon_client):
    """__version__ returns the contents of version.json."""
    here = Path(__file__)
    root_dir = here.parents[3]
    version_path = Path(root_dir / "version.json")
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


def test_read_heartbeat(anon_client):
    """The platform calls /__heartbeat__ to check backing services."""
    with capture_logs() as cap_logs:
        resp = anon_client.get("/__heartbeat__")
    assert resp.status_code == 200
    data = resp.json()
    expected = {"database": {"up": True, "time_ms": data["database"]["time_ms"]}}
    assert data == expected
    assert len(cap_logs) == 1


def test_read_heartbeat_no_db_fails(anon_client, mock_db):
    """/__heartbeat__ returns 503 when the database is unavailable."""
    mock_db.execute.side_effect = SQATimeoutError()
    resp = anon_client.get("/__heartbeat__")
    assert resp.status_code == 503
    data = resp.json()
    expected = {"database": {"up": False, "time_ms": data["database"]["time_ms"]}}
    assert data == expected


def test_read_health(anon_client):
    """The platform calls /__lbheartbeat__ to see when the app is running."""
    with capture_logs() as cap_logs:
        resp = anon_client.get("/__lbheartbeat__")
    assert resp.status_code == 200
    assert resp.json() == {"status": "OK"}
    assert len(cap_logs) == 1


@pytest.mark.parametrize("path", ("/__lbheartbeat__", "/__heartbeat__"))
def test_head_monitoring_endpoints(anon_client, path):
    """Monitoring endpoints can be called without credentials"""
    with capture_logs() as cap_logs:
        resp = anon_client.head(path)
    assert resp.status_code == 200
    assert len(cap_logs) == 1
