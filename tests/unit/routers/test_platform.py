import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.exc import TimeoutError as SQATimeoutError
from structlog.testing import capture_logs

from ctms.app import app
from ctms.config import Settings
from ctms.dependencies import get_db, get_settings


@pytest.fixture
def mock_db():
    """Mock the database session."""
    mocked_db = Mock()

    def mock_get_db():
        yield mocked_db

    app.dependency_overrides[get_db] = mock_get_db
    yield mocked_db
    del app.dependency_overrides[get_db]


@pytest.fixture
def test_settings():
    """Set settings for heartbeat tests."""

    settings = {
        "acoustic_retry_limit": 5,
        "acoustic_batch_limit": 25,
        "acoustic_loop_min_secs": 10,
    }

    app.dependency_overrides[get_settings] = lambda: Settings(**settings)
    yield settings
    del app.dependency_overrides[get_settings]


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


def test_exposed_configuration(anon_client):
    resp = anon_client.get("/acoustic_configuration")
    exposed = resp.json()

    assert "fxa_lang" in exposed["sync_fields"]["main"]
    assert exposed["newsletter_mappings"]["mozilla-rally"] == "sub_rally"


def test_read_heartbeat(anon_client, test_settings):
    """The platform calls /__heartbeat__ to check backing services."""
    with capture_logs() as cap_logs:
        resp = anon_client.get("/__heartbeat__")
    assert resp.status_code == 200
    data = resp.json()
    expected = {
        "database": {
            "up": True,
            "time_ms": data["database"]["time_ms"],
            "acoustic": {
                "success": True,
                "backlog": 0,
                "max_backlog": None,
                "retry_backlog": 0,
                "max_retry_backlog": None,
                "retry_limit": 5,
                "batch_limit": 25,
                "loop_min_sec": 10,
                "time_ms": data["database"]["acoustic"]["time_ms"],
            },
        }
    }
    assert data == expected
    assert len(cap_logs) == 1
    assert "trivial" not in cap_logs[0]


def test_read_heartbeat_no_db_fails(anon_client, mock_db):
    """/__heartbeat__ returns 503 when the database is unavailable."""
    mock_db.execute.side_effect = SQATimeoutError()
    resp = anon_client.get("/__heartbeat__")
    assert resp.status_code == 503
    data = resp.json()
    expected = {
        "database": {
            "up": False,
            "time_ms": data["database"]["time_ms"],
            "acoustic": {},
        }
    }
    assert data == expected


def test_read_heartbeat_acoustic_fails(anon_client, test_settings):
    """/__heartbeat__ returns 200 when measuring the acoustic backlog fails."""
    with patch(
        "ctms.routers.platform.get_all_acoustic_records_count",
        side_effect=SQATimeoutError(),
    ):
        resp = anon_client.get("/__heartbeat__")
    assert resp.status_code == 200
    data = resp.json()
    expected = {
        "database": {
            "up": True,
            "time_ms": data["database"]["time_ms"],
            "acoustic": {
                "success": False,
                "backlog": None,
                "max_backlog": None,
                "retry_backlog": None,
                "max_retry_backlog": None,
                "retry_limit": 5,
                "batch_limit": 25,
                "loop_min_sec": 10,
                "time_ms": data["database"]["acoustic"]["time_ms"],
            },
        }
    }
    assert data == expected


@pytest.mark.parametrize("backlog, retry_backlog", ((51, 1), (1, 51)))
def test_read_heartbeat_backlog_over_limit(
    anon_client, test_settings, backlog, retry_backlog
):
    """/__heartbeat__ returns 503 when measuring the acoustic backlog fails."""
    test_settings["acoustic_max_backlog"] = 50
    test_settings["acoustic_max_retry_backlog"] = 50
    backlog = 1
    retry_backlog = 1
    with patch(
        "ctms.routers.platform.get_all_acoustic_records_count", return_value=backlog
    ), patch(
        "ctms.routers.platform.get_all_acoustic_retries_count",
        return_value=retry_backlog,
    ):
        resp = anon_client.get("/__heartbeat__")
    assert resp.status_code == 503
    data = resp.json()
    assert data["database"]["acoustic"]["backlog"] == backlog
    assert data["database"]["acoustic"]["max_backlog"] == 50
    assert data["database"]["acoustic"]["retry_backlog"] == retry_backlog
    assert data["database"]["acoustic"]["max_retry_backlog"] == 50


@pytest.mark.parametrize("method", ("GET", "HEAD"))
@pytest.mark.parametrize("agent", ("newrelic", "amazon"))
@pytest.mark.parametrize("success", (True, False))
def test_read_heartbeat_by_bot(anon_client, mock_db, success, agent, method):
    """When a known bot calls heartbeat, mark trivial on success."""
    if agent == "newrelic":
        headers = {
            "x-abuse-info": "Request sent by a New Relic Synthetics Monitor (...",
            "x-newrelic-synthetics": "YmluYXJ5IGRhdGE=",
        }
    else:
        assert agent == "amazon"
        headers = {"user-agent": "Amazon-Route53-Health-Check-Service (ref ..."}

    if not success:
        mock_db.execute.side_effect = SQATimeoutError()

    with capture_logs() as cap_logs, patch(
        "ctms.routers.platform.get_all_acoustic_records_count", return_value=0
    ), patch("ctms.routers.platform.get_all_acoustic_retries_count", return_value=0):
        resp = anon_client.request(method, "/__heartbeat__", headers=headers)
    assert len(cap_logs) == 1

    if success:
        assert resp.status_code == 200
        assert cap_logs[0]["trivial"] is True
    else:
        assert resp.status_code == 503
        assert "trivial" not in cap_logs[0]


def test_read_health(anon_client):
    """The platform calls /__lbheartbeat__ to see when the app is running."""
    with capture_logs() as cap_logs:
        resp = anon_client.get("/__lbheartbeat__")
    assert resp.status_code == 200
    assert resp.json() == {"status": "OK"}
    assert len(cap_logs) == 1
    assert "trivial" not in cap_logs[0]


@pytest.mark.parametrize("method", ("GET", "HEAD"))
def test_read_health_by_bot(anon_client, method):
    """When a known bot calls lbheartbeat, mark the request as trivial."""
    headers = {"user-agent": "kube-probe/1.18+"}
    with capture_logs() as cap_logs:
        resp = anon_client.request(method, "/__lbheartbeat__", headers=headers)
    assert resp.status_code == 200
    assert len(cap_logs) == 1
    assert cap_logs[0]["trivial"] is True


@pytest.mark.parametrize("path", ("/__lbheartbeat__", "/__heartbeat__"))
def test_head_monitoring_endpoints(anon_client, path):
    """Monitoring endpoints can be called without credentials"""
    with capture_logs() as cap_logs:
        resp = anon_client.head(path)
    assert resp.status_code == 200
    assert len(cap_logs) == 1
    assert "trivial" not in cap_logs[0]
