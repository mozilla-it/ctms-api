"""Unit tests for dockerflow health monitoring endpoints"""
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.exc import TimeoutError as SQATimeoutError
from structlog.testing import capture_logs

from ctms.app import app, get_db, get_settings
from ctms.config import Settings


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


def test_read_heartbeat(anon_client, dbsession, test_settings):
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
    expected = {"database": {"up": False, "time_ms": data["database"]["time_ms"]}}
    assert data == expected


def test_read_heartbeat_acoustic_fails(anon_client, dbsession, test_settings):
    """/__heartbeat__ returns 200 when measuring the acoustic backlog fails."""
    with patch(
        "ctms.monitor.get_all_acoustic_records_count", side_effect=SQATimeoutError()
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
    anon_client, dbsession, test_settings, backlog, retry_backlog
):
    """/__heartbeat__ returns 503 when measuring the acoustic backlog fails."""
    test_settings["acoustic_max_backlog"] = 50
    test_settings["acoustic_max_retry_backlog"] = 50
    backlog = 1
    retry_backlog = 1
    with patch(
        "ctms.monitor.get_all_acoustic_records_count", return_value=backlog
    ), patch("ctms.monitor.get_all_acoustic_retries_count", return_value=retry_backlog):
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
        "ctms.monitor.get_all_acoustic_records_count", return_value=0
    ), patch("ctms.monitor.get_all_acoustic_retries_count", return_value=0):
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
def test_head_monitoring_endpoints(anon_client, dbsession, path):
    """Monitoring endpoints can be called without credentials"""
    with capture_logs() as cap_logs:
        resp = anon_client.head(path)
    assert resp.status_code == 200
    assert len(cap_logs) == 1
    assert "trivial" not in cap_logs[0]
