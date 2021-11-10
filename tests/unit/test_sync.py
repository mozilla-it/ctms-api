from datetime import datetime, timedelta, timezone
from unittest import mock
from unittest.mock import MagicMock

import pytest

from ctms.crud import schedule_acoustic_record
from ctms.sync import CTMSToAcousticSync
from tests.unit.test_crud import StatementWatcher


@pytest.fixture
def ctms_to_acoustic_sync():
    with mock.patch("ctms.acoustic_service.Acoustic"):
        yield CTMSToAcousticSync(
            client_id="CLIENT",
            client_secret="SECRET",
            refresh_token="REFRESH",
            acoustic_main_table_id="1",
            acoustic_newsletter_table_id="9",
            acoustic_product_table_id="10",
            server_number=6,
        )


@pytest.fixture
def ctms_to_acoustic_sync_with_metrics(background_metric_service):
    with mock.patch("ctms.acoustic_service.Acoustic"):
        yield CTMSToAcousticSync(
            client_id="CLIENT",
            client_secret="SECRET",
            refresh_token="REFRESH",
            acoustic_main_table_id="1",
            acoustic_newsletter_table_id="9",
            acoustic_product_table_id="10",
            server_number=6,
            metric_service=background_metric_service,
        )


@pytest.fixture(params=["with_metrics", "no_metrics"])
def sync_obj(request, ctms_to_acoustic_sync, ctms_to_acoustic_sync_with_metrics):
    """Test sync with and without metrics."""
    if request.param == "with_metrics":
        return ctms_to_acoustic_sync_with_metrics
    assert request.param == "no_metrics"
    return ctms_to_acoustic_sync


def _setup_pending_record(dbsession, email_id):
    schedule_acoustic_record(dbsession, email_id=email_id)
    dbsession.flush()


def test_ctms_to_acoustic_sync_creation(sync_obj):
    assert sync_obj is not None


def test_sync_to_acoustic(sync_obj, maximal_contact):
    sync_obj.ctms_to_acoustic = MagicMock()
    result = sync_obj.sync_contact_with_acoustic(maximal_contact)
    assert result
    sync_obj.ctms_to_acoustic.attempt_to_upload_ctms_contact.assert_called_with(
        maximal_contact
    )


def test_sync_acoustic_record_retry_path(dbsession, sync_obj, maximal_contact):
    sync_obj.ctms_to_acoustic = MagicMock(
        **{"attempt_to_upload_ctms_contact.return_value": False}
    )
    _setup_pending_record(dbsession, email_id=maximal_contact.email.email_id)
    no_metrics = sync_obj.metric_service is None
    with StatementWatcher(dbsession.connection()) as watcher:
        sync_obj.sync_records(
            dbsession, end_time=datetime.now(timezone.utc) + timedelta(hours=12)
        )
        dbsession.flush()
    sync_obj.ctms_to_acoustic.attempt_to_upload_ctms_contact.assert_called_with(
        maximal_contact
    )
    if no_metrics:
        assert watcher.count == 4  # Get All Records, Get Contact(x2), Increment Retry
        return

    # Metrics adds two DB queries (total records and retries)
    assert watcher.count == 6

    registry = sync_obj.metric_service.registry
    labels = {
        "app_kubernetes_io_component": "background",
        "app_kubernetes_io_instance": "ctms",
        "app_kubernetes_io_name": "ctms",
    }
    prefix = "ctms_background_acoustic_sync"
    assert registry.get_sample_value(f"{prefix}_total", labels) is None
    assert registry.get_sample_value(f"{prefix}_retries", labels) == 0
    assert registry.get_sample_value(f"{prefix}_backlog", labels) == 1


def test_sync_acoustic_record_delete_path(
    dbsession,
    sync_obj,
    maximal_contact,
):
    no_metrics = sync_obj.metric_service is None
    sync_obj.ctms_to_acoustic = MagicMock(
        **{"attempt_to_upload_ctms_contact.return_value": True}
    )
    _setup_pending_record(dbsession, email_id=maximal_contact.email.email_id)

    with StatementWatcher(dbsession.connection()) as watcher:
        sync_obj.sync_records(
            dbsession, end_time=datetime.now(timezone.utc) + timedelta(hours=12)
        )
        dbsession.flush()
    sync_obj.ctms_to_acoustic.attempt_to_upload_ctms_contact.assert_called_with(
        maximal_contact
    )
    if no_metrics:
        assert watcher.count == 4  # Get All Records, Get Contact(x2), Increment Retry
        return

    # Metrics adds two DB queries (total records and retries)
    assert watcher.count == 6

    registry = sync_obj.metric_service.registry
    labels = {
        "app_kubernetes_io_component": "background",
        "app_kubernetes_io_instance": "ctms",
        "app_kubernetes_io_name": "ctms",
    }
    prefix = "ctms_background_acoustic_sync"
    assert registry.get_sample_value(f"{prefix}_total", labels) == 1
    assert registry.get_sample_value(f"{prefix}_retries", labels) == 0
    assert registry.get_sample_value(f"{prefix}_backlog", labels) == 1
