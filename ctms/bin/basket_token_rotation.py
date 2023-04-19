#!/usr/bin/env python3
"""Run in the background; recreate existing basket tokens."""
from uuid import uuid4

import structlog
from app import get_metrics
from crud import (
    get_all_contacts_with_basket_tokens,
    schedule_acoustic_record,
    update_contact,
)
from metrics import init_metrics
from prometheus_client import CollectorRegistry
from sqlalchemy.orm import Session

from ctms import config
from ctms.background_metrics import BackgroundMetricService
from ctms.database import engine_factory
from ctms.exception_capture import init_sentry
from ctms.log import configure_logging
from ctms.sync import CTMSToAcousticSync, update_healthcheck


def main(db, settings):
    logger = structlog.get_logger("ctms.bin.basket_token_rotation")
    logger.info("Setting up basket_rotation process.")
    metrics_registry = CollectorRegistry()
    metric_service = BackgroundMetricService(
        registry=metrics_registry,
        pushgateway_url=settings.prometheus_pushgateway_url,
        metric_prefix="ctms_basket_token_rotation_",
    )
    healthcheck_path = settings.background_healthcheck_path
    update_healthcheck(healthcheck_path)

    email_records_pending_update = get_all_contacts_with_basket_tokens(dbsession=db)
    if not email_records_pending_update:
        raise ValueError("No emails with basket_tokens.")

    count_of_records = len(email_records_pending_update)
    logger.info(
        "Beginning acoustic token rotation",
        context={"email_records_pending_update": count_of_records},
    )
    metric_service.gauge_token_rotation(count_of_records)
    metric_service.push_to_gateway()

    failed_records = []
    # For each email record:
    for email in email_records_pending_update:
        try:
            # generate a uuid
            new_token = uuid4()

            # update the contact
            update_contact(
                db=db,
                email=email,
                update_data={"email": {"basket_token": new_token}},
                metrics=None,
            )
            logger.info("email record token rotated in CTMS.")

            schedule_acoustic_record(db=db, email_id=email.id, metrics=None)
            logger.info("email record scheduled to update in Acoustic.")

            db.commit()

            # Reduce and submit gauge count to metric service
            count_of_records = count_of_records - 1
            metric_service.gauge_token_rotation(count_of_records)
            metric_service.push_to_gateway()
        except Exception as e:  # pylint: disable=broad-except
            logger.err("Email ID unable to be rotated.", context={"email_id": email.id})
            failed_records.append(email.id)

        if failed_records:
            logger.err(
                "Full list of unprocessable email_ids.",
                context={"failed_records": failed_records},
            )


if __name__ == "__main__":
    init_sentry()
    config_settings = config.BackgroundSettings()
    configure_logging(logging_level=config_settings.logging_level.name)
    metrics = init_metrics(METRICS_REGISTRY)
    init_metrics_labels(SessionLocal(), app, METRICS)
    engine = engine_factory(config_settings)
    with Session(engine) as session:
        main(session, config_settings)
