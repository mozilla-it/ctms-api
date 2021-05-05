#!/usr/bin/env python3
"""Run continuously in the background, syncing acoustic with our db."""
from datetime import datetime, timezone
from time import monotonic, sleep
from typing import List

from ctms import config
from ctms.crud import (
    delete_acoustic_record,
    get_acoustic_record_as_contact,
    get_all_acoustic_records_before,
    retry_acoustic_record,
)
from ctms.database import get_db_engine
from ctms.models import PendingAcousticRecord
from ctms.schemas import ContactSchema


def sync_contact_with_acoustic(contact: ContactSchema):
    print("sync here")
    is_success = True
    # TODO:
    #  Need to define what a successful response from Acoustic would be, and make the request.
    #   Upon success, the record is discarded;
    #   Upon failure, the record is up for retry
    return is_success


def sync_pending_record(db, pending_record: PendingAcousticRecord):
    contact: ContactSchema = get_acoustic_record_as_contact(pending_record)
    is_success = sync_contact_with_acoustic(contact)

    if is_success:
        delete_acoustic_record(db, pending_record)
    else:
        retry_acoustic_record(db, pending_record)


def sync_records(db):
    all_acoustic_records_before_now: List[
        PendingAcousticRecord
    ] = get_all_acoustic_records_before(db, end_time=datetime.now(timezone.utc))
    for acoustic_record in all_acoustic_records_before_now:
        sync_pending_record(db, acoustic_record)


def main(db, settings):
    prev = monotonic()
    while True:
        sync_records(db)
        to_sleep = settings.acoustic_loop_min_secs - (monotonic() - prev)
        if to_sleep > 0:
            sleep(to_sleep)
        prev = monotonic()


if __name__ == "__main__":
    # Get the database
    config_settings = config.Settings()
    engine, session_factory = get_db_engine(config_settings)
    session = session_factory()

    try:
        main(session, config_settings)
    finally:
        session.close()
