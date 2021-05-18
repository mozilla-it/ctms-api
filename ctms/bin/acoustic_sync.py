#!/usr/bin/env python3
"""Run continuously in the background, syncing acoustic with our db."""
import argparse
import logging
from time import monotonic, sleep

from ctms import config
from ctms.database import get_db_engine
from ctms.sync import CTMSToAcousticSync

LOGGER = None


def _setup_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-log",
        "--log",
        default="debug",
        help=("provide logging level to job (default: debug)"),
    )

    options = parser.parse_args()
    levels = {
        "critical": logging.CRITICAL,
        "error": logging.ERROR,
        "warn": logging.WARNING,
        "warning": logging.WARNING,
        "info": logging.INFO,
        "debug": logging.DEBUG,
    }
    level = levels.get(options.log.lower())
    if level is None:
        raise ValueError(
            f"log level given: {options.log}"
            f" -- must be one of: {' | '.join(levels.keys())}"
        )
    logging.basicConfig(level=level)
    return logging.getLogger(__name__)


def main(db, settings):
    LOGGER.debug("Setting up sync_service.")
    sync_service = CTMSToAcousticSync(
        client_id=settings.acoustic_client_id,
        client_secret=settings.acoustic_client_secret,
        refresh_token=settings.acoustic_refresh_token,
        acoustic_main_table_id=settings.acoustic_main_table_id,
        acoustic_newsletter_table_id=settings.acoustic_newsletter_table_id,
        server_number=settings.acoustic_server_number,
        retry_limit=settings.acoustic_retry_limit,
        is_acoustic_enabled=settings.acoustic_integration_feature_flag,
    )
    prev = monotonic()
    LOGGER.debug("Sync Feature Flag is: %s", settings.acoustic_sync_feature_flag)
    while settings.acoustic_sync_feature_flag:
        sync_service.sync_records(db)
        to_sleep = settings.acoustic_loop_min_secs - (monotonic() - prev)
        if to_sleep > 0:
            sleep(to_sleep)
        prev = monotonic()


if __name__ == "__main__":
    LOGGER = _setup_args()
    LOGGER.debug("Begin Acoustic Sync Script.")
    config_settings = config.BackgroundSettings()
    engine, session_factory = get_db_engine(config_settings)
    session = session_factory()

    try:
        main(session, config_settings)
    finally:
        session.close()
