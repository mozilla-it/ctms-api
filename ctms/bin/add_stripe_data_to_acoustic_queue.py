#!/usr/bin/env python3
"""Parse Stripe data from JSON; add to Acoustic Queue."""

import argparse
import json
from typing import List

import structlog
from sqlalchemy.orm import Session

from ctms.config import Settings
from ctms.database import SessionLocal
from ctms.ingest_stripe import (
    StripeIngestUnknownObjectError,
    StripeToAcousticParseError,
    add_stripe_object_to_acoustic_queue,
)
from ctms.log import configure_logging

logger = structlog.get_logger(__name__)


def main(db_session: Session, filenames: List[str]) -> None:
    """Load a Stripe object or list of objects from disk."""

    for filename in filenames:
        logger.info("Reading data from file...", filename=filename)
        with open(filename, "r", encoding="utf8") as data_file:
            data = json.load(data_file)

        if isinstance(data, dict):
            parse_stripe_object(db_session, data)
        elif isinstance(data, list):
            for obj in data:
                if obj:
                    parse_stripe_object(db_session, obj)


def parse_stripe_object(db_session, obj):
    """Parse a Stripe object; add the object's email_id to acoustic queue."""

    try:
        add_stripe_object_to_acoustic_queue(db_session, obj)
    except (StripeIngestUnknownObjectError, StripeToAcousticParseError):
        logger.info("Skipping object", object=obj["object"], id=obj["id"])
    else:
        logger.info("Queued object", object=obj["object"], id=obj["id"])
        db_session.commit()


def get_parser():
    the_parser = argparse.ArgumentParser(
        description="Add Stripe data from JSON to Acoustic Queue"
    )
    the_parser.add_argument(
        "filenames", metavar="data.json", nargs="+", help="Stripe data to parse"
    )
    return the_parser


if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    config_settings = Settings()
    configure_logging(logging_level=config_settings.logging_level.name)
    with SessionLocal() as session:
        main(session, args.filenames)
