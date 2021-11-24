#!/usr/bin/env python3
"""Run continuously in the background, syncing acoustic with our db."""
from time import monotonic, sleep

import structlog
from prometheus_client import CollectorRegistry

from ctms import config
from ctms.background_metrics import BackgroundMetricService
from ctms.database import get_db_engine
from ctms.exception_capture import init_sentry
from ctms.log import configure_logging
from ctms.sync import CTMSToAcousticSync


def main(db, settings):
    logger = structlog.get_logger(__name__)
    logger.info(
        "Setting up sync_service.",
        sync_feature_flag=settings.acoustic_sync_feature_flag,
    )
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
    while settings.acoustic_sync_feature_flag:
        context = sync_service.sync_records(db)
        metric_service.push_to_gateway()
        duration_s = monotonic() - prev
        to_sleep = settings.acoustic_loop_min_secs - duration_s
        logger.info(
            "sync_service cycle complete",
            loop_duration_s=round(duration_s, 3),
            loop_sleep_s=round(to_sleep, 3),
            **context
        )
        if to_sleep > 0:
            sleep(to_sleep)
        prev = monotonic()


if __name__ == "__main__":
    init_sentry()
    config_settings = config.BackgroundSettings()
    configure_logging(logging_level=config_settings.logging_level.name)
    engine, session_factory = get_db_engine(config_settings)
    session = session_factory()

    try:
        main(session, config_settings)
    finally:
        session.close()
