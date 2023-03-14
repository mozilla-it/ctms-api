from datetime import datetime, timedelta, timezone
from unittest import mock
from unittest.mock import MagicMock

import pytest
from structlog.testing import capture_logs

from ctms.acoustic_service import AcousticUploadError
from ctms.crud import schedule_acoustic_record
from ctms.sync import CTMSToAcousticSync, check_healthcheck, update_healthcheck


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


def test_sync_acoustic_record_retry_path(
    dbsession,
    sync_obj,
    maximal_contact,
    main_acoustic_fields,
    acoustic_newsletters_mapping,
):
    sync_obj.ctms_to_acoustic = MagicMock(
        **{"attempt_to_upload_ctms_contact.side_effect": AcousticUploadError("Boom!")}
    )
    _setup_pending_record(dbsession, email_id=maximal_contact.email.email_id)
    no_metrics = sync_obj.metric_service is None
    end_time = datetime.now(timezone.utc) + timedelta(hours=12)

    with capture_logs() as caplog:
        context = sync_obj.sync_records(dbsession, end_time=end_time)

    sync_obj.ctms_to_acoustic.attempt_to_upload_ctms_contact.assert_called_with(
        maximal_contact, main_acoustic_fields, acoustic_newsletters_mapping
    )
    expected_context = {
        "batch_limit": 20,
        "retry_limit": 5,
        "count_total": 1,
        "count_retry": 1,
        "end_time": end_time.isoformat(),
    }

    if no_metrics:
        assert context == expected_context
        return

    expected_context["retry_backlog"] = 0
    expected_context["sync_backlog"] = 1
    assert context == expected_context

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

    assert len(caplog) == 1
    assert (
        caplog[0]["event"] == "Could not upload contact: AcousticUploadError('Boom!')"
    )


def test_email_domain_is_logged_when_address_is_invalid(
    dbsession, sync_obj, maximal_contact
):
    sync_obj.ctms_to_acoustic = MagicMock(
        **{
            "attempt_to_upload_ctms_contact.side_effect": AcousticUploadError(
                "Email Address Is Invalid"
            )
        }
    )
    _setup_pending_record(dbsession, email_id=maximal_contact.email.email_id)
    end_time = datetime.now(timezone.utc) + timedelta(hours=12)

    with capture_logs() as caplog:
        sync_obj.sync_records(dbsession, end_time=end_time)

    assert len(caplog) == 1
    assert (
        caplog[0]["event"]
        == "Could not upload contact: AcousticUploadError('Email Address Is Invalid')"
    )
    assert caplog[0]["email_id"] == maximal_contact.email.email_id
    assert caplog[0]["primary_email_domain"] == "example.com"


def test_sync_acoustic_record_delete_path(
    dbsession,
    sync_obj,
    maximal_contact,
    settings,
    main_acoustic_fields,
    acoustic_newsletters_mapping,
):
    no_metrics = sync_obj.metric_service is None
    sync_obj.ctms_to_acoustic = MagicMock(
        **{"attempt_to_upload_ctms_contact.return_value": True}
    )
    _setup_pending_record(dbsession, email_id=maximal_contact.email.email_id)
    end_time = datetime.now(timezone.utc) + timedelta(hours=12)

    context = sync_obj.sync_records(dbsession, end_time=end_time)
    dbsession.flush()

    sync_obj.ctms_to_acoustic.attempt_to_upload_ctms_contact.assert_called_with(
        maximal_contact, main_acoustic_fields, acoustic_newsletters_mapping
    )
    expected_context = {
        "batch_limit": 20,
        "retry_limit": 5,
        "count_total": 1,
        "count_synced": 1,
        "end_time": end_time.isoformat(),
    }

    if no_metrics:
        assert context == expected_context
        return

    expected_context["retry_backlog"] = 0
    expected_context["sync_backlog"] = 1
    assert context == expected_context

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
    assert 0.0 <= registry.get_sample_value(f"{prefix}_age_s", labels) <= 0.2


def test_update_healthcheck_no_path():
    """update_healthcheck does nothing with a null path"""
    update_healthcheck(None)


def test_update_healthcheck_path(tmp_path):
    """update_healthcheck writes a timestamp with a path"""
    health_path = tmp_path / "healthcheck"
    update_healthcheck(health_path)
    age = check_healthcheck(health_path, 5)
    assert age < 1


def test_check_healthcheck_no_path():
    """check_healthcheck raises if path is null."""
    with pytest.raises(Exception) as exc_info:
        check_healthcheck(None, 2)
    assert str(exc_info.value) == "BACKGROUND_HEALTHCHECK_PATH not set"


def test_check_healthcheck_no_age(tmp_path):
    """check_healthcheck raises if the age is null."""
    health_path = tmp_path / "healthcheck"
    with pytest.raises(Exception) as exc_info:
        check_healthcheck(health_path, None)
    assert str(exc_info.value) == "BACKGROUND_HEALTHCHECK_AGE_S not set"


def test_check_healthcheck_no_file(tmp_path):
    """check_healthcheck raises if file doesn't exist."""
    health_path = tmp_path / "healthcheck"
    with pytest.raises(OSError) as exc_info:
        check_healthcheck(health_path, 60)
    assert (exc_info.value.filename) == str(health_path)


def test_check_healthcheck_old_age(tmp_path):
    """check_healthcheck raises if the age is too old."""
    health_path = tmp_path / "healthcheck"
    old_date = datetime.now(tz=timezone.utc) - timedelta(seconds=120)
    old_date_iso = old_date.isoformat()
    with open(health_path, "w", encoding="utf8") as health_file:
        health_file.write(old_date_iso)
    with pytest.raises(Exception) as exc_info:
        check_healthcheck(health_path, 60)
    assert str(exc_info.value).startswith("Age 120.")
    assert str(exc_info.value).endswith(f"s > 60s, written at {old_date_iso}")
