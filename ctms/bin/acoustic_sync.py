#!/usr/bin/env python3
"""Run continuously in the background, syncing acoustic with our db."""
import logging
from time import monotonic, sleep

from prometheus_client import CollectorRegistry

from ctms import config
from ctms.background_metrics import BackgroundMetricService
from ctms.database import get_db_engine
from ctms.exception_capture import init_sentry
from ctms.log import configure_logging
from ctms.sync import CTMSToAcousticSync

LOGGER = None


def _setup_logging(settings):
    configure_logging(logging_level=settings.logging_level.name)
    return logging.getLogger(__name__)


def main(db, settings):
    LOGGER.debug("Setting up sync_service.")
    metrics_registry = CollectorRegistry()
    metric_service = BackgroundMetricService(
        registry=metrics_registry, pushgateway_url=settings.prometheus_pushgateway_url
    )

    sync_service = CTMSToAcousticSync(
        client_id=settings.acoustic_client_id,
        client_secret=settings.acoustic_client_secret,
        refresh_token=settings.acoustic_refresh_token,
        acoustic_main_table_id=settings.acoustic_main_table_id,
        acoustic_newsletter_table_id=settings.acoustic_newsletter_table_id,
        acoustic_product_table_id=settings.acoustic_product_subscriptions_id,
        server_number=settings.acoustic_server_number,
        retry_limit=settings.acoustic_retry_limit,
        batch_limit=settings.acoustic_batch_limit,
        is_acoustic_enabled=settings.acoustic_integration_feature_flag,
        metric_service=metric_service,
    )
    prev = monotonic()
    LOGGER.debug("Sync Feature Flag is: %s", settings.acoustic_sync_feature_flag)
    while settings.acoustic_sync_feature_flag:
        sync_service.sync_records(db)
        metric_service.push_to_gateway()
        to_sleep = settings.acoustic_loop_min_secs - (monotonic() - prev)
        if to_sleep > 0:
            sleep(to_sleep)
        prev = monotonic()


if __name__ == "__main__":
    init_sentry()
    config_settings = config.BackgroundSettings()
    LOGGER = _setup_logging(config_settings)
    engine, session_factory = get_db_engine(config_settings)
    session = session_factory()

    try:
        LOGGER.debug("Begin Acoustic Sync Script.")
        main(session, config_settings)
    finally:
        session.close()
