#!/usr/bin/env python3
"""Run continuously in the background, syncing acoustic with our db."""

from time import monotonic, sleep

from ctms import config
from ctms.database import get_db_engine


def main(db, settings):
    prev = monotonic()
    while True:
        print("sync here")
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
