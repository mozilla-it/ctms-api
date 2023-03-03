"""Tests for ctms/bin/acoustic_sync.py"""

from unittest import mock

import pytest
from prometheus_client import CollectorRegistry
from structlog.testing import capture_logs

from ctms.background_metrics import BackgroundMetricService
from ctms.bin.acoustic_sync import sync
from ctms.config import Settings


class HaltLoop(Exception):
    """Break out of the infinite loop in main."""


@pytest.fixture
def test_env():
    """Setup environment for sync() tests."""
    settings = Settings(
        prometheus_pushgateway_url="https://prom.example.com/push",
        acoustic_client_id="CLIENT_ID",
        acoustic_client_secret="CLIENT_SECRET",  # pragma: allowlist secret
        acoustic_refresh_token="REFRESH_TOKEN",
        acoustic_main_table_id=1234,
        acoustic_newsletter_table_id=12345,
        acoustic_product_subscriptions_id=123456,
        acoustic_retry_limit=6,
        acoustic_batch_limit=20,
        acoustic_server_number=6,
        acoustic_loop_min_secs=5,
        acoustic_max_backlog=None,
        acoustic_max_retry_backlog=None,
        acoustic_sync_feature_flag=True,
        acoustic_integration_feature_flag=True,
    )
    patcher_sleep = mock.patch(
        "ctms.bin.acoustic_sync.sleep", side_effect=[None, HaltLoop]
    )

    metrics_registry = CollectorRegistry()
    metric_service = BackgroundMetricService(
        registry=metrics_registry, pushgateway_url=settings.prometheus_pushgateway_url
    )

    patcher_push = mock.patch("ctms.background_metrics.push_to_gateway")
    mock_sleep = patcher_sleep.start()
    mock_push = patcher_push.start()

    try:
        yield {
            "settings": settings,
            "mock_sleep": mock_sleep,
            "metric_service": metric_service,
            "mock_push": mock_push,
        }
    finally:
        patcher_sleep.stop()
        patcher_push.stop()


@pytest.fixture
def mock_service():
    """Mock the sync_service CTMSToAcousticSync instance"""
    service = mock.Mock(spec_set=("sync_records",))
    service.sync_records.return_value = {
        "batch_limit": 20,
        "count_total": 0,
        "end_time": "now",
        "retry_backlog": 0,
        "retry_limit": 6,
        "sync_backlog": 0,
    }
    with mock.patch("ctms.bin.acoustic_sync.CTMSToAcousticSync", return_value=service):
        yield service


def test_main_no_contacts(dbsession, test_env):
    """sync() sleeps when no records are processed."""
    with capture_logs() as caplog, pytest.raises(HaltLoop):
        sync(dbsession, test_env["settings"], test_env["metric_service"])
    assert test_env["mock_sleep"].call_count == 2
    test_env["mock_push"].assert_called_with(
        "https://prom.example.com/push", job="prometheus-pushgateway", registry=mock.ANY
    )
    assert test_env["mock_push"].call_count == 2
    assert len(caplog) == 2
    loop_duration_s = caplog[1]["loop_duration_s"]
    loop_sleep_s = caplog[1]["loop_sleep_s"]
    assert caplog[0] == {
        "event": "sync_service cycle complete",
        "log_level": "info",
        "batch_limit": 20,
        "count_total": 0,
        "end_time": "now",
        "loop_duration_s": caplog[0]["loop_duration_s"],
        "loop_sleep_s": caplog[0]["loop_sleep_s"],
        "retry_backlog": 0,
        "retry_limit": 6,
        "sync_backlog": 0,
        "trivial": True,
    }
    assert loop_duration_s + loop_sleep_s == pytest.approx(5.0, 0.001)
    assert caplog[0]["event"] == "sync_service cycle complete"


def test_main_some_contacts(dbsession, test_env, mock_service):
    """sync() sleeps when all backlogged records are processed."""
    mock_service.sync_records.return_value.update({"count_total": 2, "sync_backlog": 2})
    with capture_logs() as caplog, pytest.raises(HaltLoop):
        sync(dbsession, test_env["settings"], test_env["metric_service"])
    assert test_env["mock_sleep"].call_count == 2
    test_env["mock_push"].assert_called_with(
        "https://prom.example.com/push", job="prometheus-pushgateway", registry=mock.ANY
    )
    assert test_env["mock_push"].call_count == 2
    assert len(caplog) == 2
    loop_duration_s = caplog[0]["loop_duration_s"]
    loop_sleep_s = caplog[0]["loop_sleep_s"]
    assert caplog[0] == {
        "event": "sync_service cycle complete",
        "log_level": "info",
        "batch_limit": 20,
        "count_total": 2,
        "end_time": "now",
        "loop_duration_s": caplog[0]["loop_duration_s"],
        "loop_sleep_s": caplog[0]["loop_sleep_s"],
        "retry_backlog": 0,
        "retry_limit": 6,
        "sync_backlog": 2,
    }
    assert loop_duration_s + loop_sleep_s == pytest.approx(5.0, 0.001)
    assert caplog[0]["event"] == "sync_service cycle complete"


def test_main_not_enough_contacts(dbsession, test_env, mock_service):
    """sync() does not sleep when a backlog remains."""
    context = mock_service.sync_records.return_value.copy()
    context.update({"count_total": 20, "sync_backlog": 40})
    mock_service.sync_records.side_effect = [context, context, HaltLoop]

    with capture_logs() as caplog, pytest.raises(HaltLoop):
        sync(dbsession, test_env["settings"], test_env["metric_service"])
    test_env["mock_sleep"].assert_not_called()
    test_env["mock_push"].assert_called_with(
        "https://prom.example.com/push", job="prometheus-pushgateway", registry=mock.ANY
    )
    assert test_env["mock_push"].call_count == 2
    assert len(caplog) == 2
    loop_sleep_s = caplog[0]["loop_sleep_s"]
    assert caplog[0] == {
        "event": "sync_service cycle complete",
        "log_level": "info",
        "batch_limit": 20,
        "count_total": 20,
        "end_time": "now",
        "loop_duration_s": caplog[0]["loop_duration_s"],
        "loop_sleep_s": loop_sleep_s,
        "retry_backlog": 0,
        "retry_limit": 6,
        "sync_backlog": 40,
    }
    assert loop_sleep_s == 0.0
    assert caplog[0]["event"] == "sync_service cycle complete"


def test_main_force_resync(
    dbsession,
    test_env,
    sample_contacts,
    main_acoustic_fields,
    acoustic_newsletters_mapping,
):
    """sync() with a list of primary emails to resync."""
    _, some_contact = sample_contacts["minimal"]
    to_resync = [
        some_contact.email.primary_email,
    ]
    with capture_logs() as caplog, pytest.raises(HaltLoop):
        with mock.patch(
            "ctms.bin.acoustic_sync.CTMSToAcousticSync.sync_contact_with_acoustic"
        ) as mocked_sync:
            sync(
                dbsession,
                test_env["settings"],
                test_env["metric_service"],
                to_resync=to_resync,
            )

    assert caplog[0]["event"] == "Force resync of 1 contacts"

    mocked_sync.assert_called_with(
        some_contact, main_acoustic_fields, acoustic_newsletters_mapping
    )
