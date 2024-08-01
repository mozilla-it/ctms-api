import json
from pathlib import Path
from unittest import mock

import pytest
from sqlalchemy.exc import TimeoutError as SQATimeoutError
from structlog.testing import capture_logs

from ctms.app import app


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
    before = getattr(app.state, "APP_DIR", None)
    here = Path(__file__)
    root_dir = here.parents[3]
    app.state.APP_DIR = root_dir
    version_path = Path(root_dir / "version.json")
    with open(version_path, "r", encoding="utf8") as vp_file:
        version_contents = vp_file.read()
    expected = json.loads(version_contents)

    resp = anon_client.get("/__version__")

    assert resp.status_code == 200
    assert resp.json() == expected
    if before is not None:
        app.state.APP_DIR = before


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
    assert data == {
        "checks": {"database": "ok"},
        "details": {},
        "status": "ok",
    }
    assert len(cap_logs) == 1


@mock.patch("ctms.routers.platform.SessionLocal")
def test_read_heartbeat_db_fails(mock_db, anon_client):
    """/__heartbeat__ returns 503 when the database is unavailable."""
    mocked_session = mock.MagicMock()
    mocked_session.__enter__.return_value = mocked_session
    mocked_session.execute.side_effect = SQATimeoutError()
    mock_db.return_value = mocked_session

    resp = anon_client.get("/__heartbeat__")
    assert resp.status_code == 500
    data = resp.json()
    assert data == {
        "checks": {"database": "error"},
        "details": {
            "database": {
                "level": 40,
                "messages": {
                    "db.0001": "Database not reachable",
                },
                "status": "error",
            },
        },
        "status": "error",
    }


def test_read_health(anon_client):
    """The platform calls /__lbheartbeat__ to see when the app is running."""
    resp = anon_client.get("/__lbheartbeat__")
    assert resp.status_code == 200


def test_get_metrics(anon_client, setup_metrics):
    """An anonoymous user can request metrics."""
    with capture_logs() as cap_logs:
        resp = anon_client.get("/metrics")
    assert resp.status_code == 200
    assert len(cap_logs) == 1
