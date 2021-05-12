"""Unit tests for dockerflow health monitoring endpoints"""
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import TimeoutError as SQATimeoutError

from ctms.app import app, get_db


@pytest.fixture
def mock_db():
    """Mock the database session."""
    mocked_db = Mock()

    def mock_get_db():
        yield mocked_db

    app.dependency_overrides[get_db] = mock_get_db
    yield mocked_db
    del app.dependency_overrides[get_db]


def test_read_heartbeat(anon_client, dbsession):
    """The platform calls /__heartbeat__ to check backing services."""
    resp = anon_client.get("/__heartbeat__")
    assert resp.status_code == 200
    data = resp.json()
    expected = {"database": {"up": True, "time_ms": data["database"]["time_ms"]}}
    assert data == expected


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
    resp = anon_client.get("/__lbheartbeat__")
    assert resp.status_code == 200
    assert resp.json() == {"status": "OK"}


@pytest.mark.parametrize("path", ("/__lbheartbeat__", "/__heartbeat__"))
def test_head_monitoring_endpoints(anon_client, dbsession, path):
    """Monitoring endpoints can be called without credentials"""
    resp = anon_client.head(path)
    assert resp.status_code == 200
