"""Capture exceptions with Sentry"""

import sentry_sdk
from pydantic import ValidationError
from sentry_sdk.integrations.logging import ignore_logger

from ctms import config


def init_sentry():
    """
    Initialize Sentry integrations for capturing exceptions.

    Because FastAPI uses threads to integrate async and sync code, this needs
    to be called at module import.

    sentry_sdk.init needs a data source name (DSN) URL, which it reads from the
    environment variable SENTRY_DSN.
    """
    try:
        settings = config.Settings()
        sentry_debug = settings.sentry_debug
    except ValidationError:
        sentry_debug = False

    version_info = config.get_version()
    # pylint: disable=abstract-class-instantiated
    sentry_sdk.init(
        release=version_info["version"],
        debug=sentry_debug,
        send_default_pii=False,
    )
    ignore_logger("uvicorn.error")
    ignore_logger("ctms.web")
