#!/usr/bin/env python3
"""Check that the healthcheck file updated by acoustic_sync.py was updated recently."""
import sys

import structlog

from ctms import config
from ctms.log import configure_logging
from ctms.sync import check_healthcheck


def main(settings):
    """
    Check the timestamp in the healthcheck file.

    This is written by ctms/bin/acoustic_sync.py
    Return is the exit code, 0 for success, 1 for failure
    """
    logger = structlog.get_logger("ctms.bin.acoustic_sync")
    healthcheck_path = settings.background_healthcheck_path
    healthcheck_age_s = settings.background_healthcheck_age_s

    try:
        age = check_healthcheck(healthcheck_path, healthcheck_age_s)
    except Exception:  # pylint: disable=broad-except
        logger.exception("Healthcheck failed")
        return 1
    logger.debug("Healthcheck passed", age=age)
    return 0


if __name__ == "__main__":
    config_settings = config.BackgroundSettings()
    configure_logging(logging_level=config_settings.logging_level.name)
    sys.exit(main(config_settings))
