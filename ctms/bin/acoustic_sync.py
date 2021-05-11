#!/usr/bin/env python3
"""Run continuously in the background, syncing acoustic with our db."""
from time import monotonic, sleep

from ctms import config
from ctms.database import get_db_engine
from ctms.sync import CTMSToAcousticSync


def main(db, settings):
    sync_service = CTMSToAcousticSync(
        client_id=settings.acoustic_client_id,
        client_secret=settings.acoustic_client_secret,
        refresh_token=settings.acoustic_refresh_token,
        acoustic_main_table_id=settings.acoustic_main_table_id,
        acoustic_newsletter_table_id=settings.acoustic_newsletter_table_id,
        server_number=settings.acoustic_server_number,
        retry_limit=settings.acoustic_retry_limit,
    )
    prev = monotonic()
    while True:
        sync_service.sync_records(db)
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
