#!/usr/bin/env python3
"""Run continuously in the background, syncing acoustic with our db."""
from time import monotonic, sleep

import click
import structlog
from prometheus_client import CollectorRegistry
from sqlalchemy.orm import Session

from ctms import config
from ctms.background_metrics import BackgroundMetricService
from ctms.database import engine_factory
from ctms.exception_capture import init_sentry
from ctms.log import configure_logging
from ctms.sync import CTMSToAcousticSync, update_healthcheck

logger = structlog.get_logger("ctms.bin.acoustic_sync")


@click.command()
def main():
    """CTMS command to sync contacts with Acoustic."""
    init_sentry()
    settings = config.BackgroundSettings()
    configure_logging(logging_level=settings.logging_level.name)
    engine = engine_factory(settings)

    logger.info(
        "Setting up sync_service.",
        sync_feature_flag=settings.acoustic_sync_feature_flag,
    )
    metrics_registry = CollectorRegistry()
    metric_service = BackgroundMetricService(
        registry=metrics_registry, pushgateway_url=settings.prometheus_pushgateway_url
    )

    with Session(engine) as session:
        sync(session, settings, metric_service)


def sync(db, settings, metric_service):
    healthcheck_path = settings.background_healthcheck_path
    update_healthcheck(healthcheck_path)

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
        acoustic_timeout=settings.acoustic_timeout_s,
    )
    prev = monotonic()
    while settings.acoustic_sync_feature_flag:
        context = sync_service.sync_records(db)
        metric_service.inc_acoustic_sync_loop()
        metric_service.push_to_gateway()
        update_healthcheck(healthcheck_path)

        duration_s = monotonic() - prev

        if context["count_total"] == context["batch_limit"]:
            to_sleep = 0

        else:
            to_sleep = settings.acoustic_loop_min_secs - duration_s

        if context["count_total"] == 0:
            context["trivial"] = True

        logger.info(
            "sync_service cycle complete",
            loop_duration_s=round(duration_s, 3),
            loop_sleep_s=round(to_sleep, 3),
            **context
        )

        metric_service.set_sync_loop_duration_seconds(round(duration_s, 3))

        if to_sleep > 0:
            sleep(to_sleep)

        prev = monotonic()


if __name__ == "__main__":
    main()
