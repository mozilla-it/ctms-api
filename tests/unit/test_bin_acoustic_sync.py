"""Tests for ctms/bin/acoustic_sync.py"""

from unittest import mock

import pytest
from structlog.testing import capture_logs

from ctms.bin.acoustic_sync import main
from ctms.config import Settings


class HaltLoop(Exception):
    """Break out of the infinite loop in main."""


@pytest.fixture
def test_env():
    """Setup environment for main() tests."""
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
    patcher_push = mock.patch("ctms.background_metrics.push_to_gateway")
    mock_sleep = patcher_sleep.start()
    mock_push = patcher_push.start()
    try:
        yield {
            "settings": settings,
            "mock_sleep": mock_sleep,
            "mock_push": mock_push,
        }
    finally:
        patcher_sleep.stop()
        patcher_push.stop()


def test_main_no_contacts(dbsession, test_env):
    """main() runs when enabled until an Exception is raised."""
    with capture_logs() as caplog, pytest.raises(HaltLoop):
        main(dbsession, test_env["settings"])
    assert test_env["mock_sleep"].call_count == 2
    test_env["mock_push"].assert_called_with(
        "https://prom.example.com/push", job="prometheus-pushgateway", registry=mock.ANY
    )
    assert test_env["mock_push"].call_count == 2
    assert len(caplog) == 3
    assert caplog[0] == {
        "event": "Setting up sync_service.",
        "log_level": "info",
        "sync_feature_flag": True,
    }
    loop_duration_s = caplog[1]["loop_duration_s"]
    loop_sleep_s = caplog[1]["loop_sleep_s"]
    assert caplog[1] == {
        "event": "sync_service cycle complete",
        "log_level": "info",
        "batch_limit": 20,
        "count_total": 0,
        "end_time": "now",
        "loop_duration_s": caplog[1]["loop_duration_s"],
        "loop_sleep_s": caplog[1]["loop_sleep_s"],
        "retry_backlog": 0,
        "retry_limit": 6,
        "sync_backlog": 0,
    }
    assert loop_duration_s + loop_sleep_s == pytest.approx(5.0, 0.001)
    assert caplog[1]["event"] == "sync_service cycle complete"
