from datetime import datetime, timedelta, timezone
from unittest import mock
from unittest.mock import MagicMock

import pytest

from ctms.crud import schedule_acoustic_record
from ctms.sync import CTMSToAcousticSync
from tests.unit.test_crud import StatementWatcher

CTMS_ACOUSTIC_CLIENT_ID = "CLIENT"
CTMS_ACOUSTIC_CLIENT_SECRET = "SECRET"
CTMS_ACOUSTIC_REFRESH_TOKEN = "REFRESH"
CTMS_ACOUSTIC_MAIN_TABLE_ID = "1"
CTMS_ACOUSTIC_NEWSLETTER_TABLE_ID = "9"


@pytest.fixture()
def no_acoustic():
    patcher = mock.patch("ctms.acoustic_service.Acoustic")
    patcher.start()
    yield patcher
    patcher.stop()


@pytest.fixture
def ctms_to_acoustic_sync(no_acoustic):
    return CTMSToAcousticSync(
        client_id=CTMS_ACOUSTIC_CLIENT_ID,
        client_secret=CTMS_ACOUSTIC_CLIENT_SECRET,
        refresh_token=CTMS_ACOUSTIC_REFRESH_TOKEN,
        acoustic_main_table_id=CTMS_ACOUSTIC_MAIN_TABLE_ID,
        acoustic_newsletter_table_id=CTMS_ACOUSTIC_NEWSLETTER_TABLE_ID,
        server_number=6,
    )


def _setup_pending_record(dbsession, email_id):
    schedule_acoustic_record(dbsession, email_id=email_id)
    dbsession.flush()


def test_ctms_to_acoustic_sync_creation(ctms_to_acoustic_sync):
    assert ctms_to_acoustic_sync is not None


def test_sync_to_acoustic(
    ctms_to_acoustic_sync,
    maximal_contact,
):
    ctms_to_acoustic_sync.ctms_to_acoustic = MagicMock()
    result = ctms_to_acoustic_sync.sync_contact_with_acoustic(maximal_contact)
    assert result
    ctms_to_acoustic_sync.ctms_to_acoustic.attempt_to_upload_ctms_contact.assert_called_with(
        maximal_contact
    )


def test_sync_acoustic_record_retry_path(
    dbsession,
    ctms_to_acoustic_sync,
    maximal_contact,
):
    ctms_to_acoustic_sync.ctms_to_acoustic = MagicMock(
        **{"attempt_to_upload_ctms_contact.return_value": False}
    )
    _setup_pending_record(dbsession, email_id=maximal_contact.email.email_id)
    with StatementWatcher(dbsession.connection()) as watcher:
        ctms_to_acoustic_sync.sync_records(
            dbsession, end_time=datetime.now(timezone.utc) + timedelta(hours=12)
        )
        dbsession.flush()
    assert watcher.count == 4  # Get All Records, Get Contact(x2), Increment Retry
    ctms_to_acoustic_sync.ctms_to_acoustic.attempt_to_upload_ctms_contact.assert_called_with(
        maximal_contact
    )


def test_sync_acoustic_record_delete_path(
    dbsession,
    ctms_to_acoustic_sync,
    maximal_contact,
):
    ctms_to_acoustic_sync.ctms_to_acoustic = MagicMock(
        **{"attempt_to_upload_ctms_contact.return_value": True}
    )
    _setup_pending_record(dbsession, email_id=maximal_contact.email.email_id)

    with StatementWatcher(dbsession.connection()) as watcher:
        ctms_to_acoustic_sync.sync_records(
            dbsession, end_time=datetime.now(timezone.utc) + timedelta(hours=12)
        )
        dbsession.flush()
    assert watcher.count == 4  # Get All Records, Get Contact(x2), Delete Record
    ctms_to_acoustic_sync.ctms_to_acoustic.attempt_to_upload_ctms_contact.assert_called_with(
        maximal_contact
    )
