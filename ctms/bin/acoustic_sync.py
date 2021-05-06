#!/usr/bin/env python3
"""Run continuously in the background, syncing acoustic with our db."""
from datetime import datetime, timezone
from time import monotonic, sleep
from typing import List

from ctms import config
from ctms.acoustic_service import CTMSToAcousticService
from ctms.crud import (
    delete_acoustic_record,
    get_acoustic_record_as_contact,
    get_all_acoustic_records_before,
    retry_acoustic_record,
)
from ctms.database import get_db_engine
from ctms.models import PendingAcousticRecord
from ctms.schemas import ContactSchema


def get_acoustic_service(settings):
    return CTMSToAcousticService(
        client_id=settings.acoustic_client_id,
        client_secret=settings.acoustic_client_secret,
        refresh_token=settings.acoustic_refresh_token,
        acoustic_main_table_id=settings.acoustic_main_table_id,
        acoustic_newsletter_table_id=settings.acoustic_newsletter_table_id,
        server_number=6,
    )


def sync_contact_with_acoustic(
    contact: ContactSchema, ctms_to_acoustic: CTMSToAcousticService
):
    try:
        is_success: bool = ctms_to_acoustic.attempt_to_upload_ctms_contact(contact)
        return is_success
    except Exception:  # pylint: disable=W0703
        # Failure
        return False


def sync_pending_record(
    db, ctms_to_acoustic: CTMSToAcousticService, pending_record: PendingAcousticRecord
):
    contact: ContactSchema = get_acoustic_record_as_contact(db, pending_record)
    is_success = sync_contact_with_acoustic(contact, ctms_to_acoustic)

    if is_success:
        delete_acoustic_record(db, pending_record)
    else:
        retry_acoustic_record(db, pending_record)


def sync_records(db, settings):
    all_acoustic_records_before_now: List[
        PendingAcousticRecord
    ] = get_all_acoustic_records_before(db, end_time=datetime.now(timezone.utc))
    ctms_to_acoustic_service = get_acoustic_service(settings)
    for acoustic_record in all_acoustic_records_before_now:
        db.commit()
        sync_pending_record(db, ctms_to_acoustic_service, acoustic_record)


def main(db, settings):
    prev = monotonic()
    while True:
        sync_records(db, settings)
        to_sleep = settings.acoustic_loop_min_secs - (monotonic() - prev)
        if to_sleep > 0:
            sleep(to_sleep)
        prev = monotonic()


if __name__ == "__main__":
    # Get the database
    config_settings = config.BackgroundSettings()
    engine, session_factory = get_db_engine(config_settings)
    session = session_factory()

    try:
        main(session, config_settings)
    finally:
        session.close()
