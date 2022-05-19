#!/usr/bin/env python3
"""Parse Stripe data from JSON; add to Acoustic Queue."""

import argparse
import json
import logging
from typing import List

from sqlalchemy.orm import Session

from ctms import config
from ctms.database import get_db_engine
from ctms.ingest_stripe import (
    StripeIngestUnknownObjectError,
    add_stripe_object_to_acoustic_queue,
)

logger = logging.getLogger(__name__)


def main(db_session: Session, filenames: List[str]) -> None:
    """Load a Stripe object or list of objects from disk."""

    for filename in filenames:
        logger.info("Reading data from %s...", filename)
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
    except StripeIngestUnknownObjectError:
        logger.info("Skipping %s %s", obj["object"], obj["id"])
    else:
        logger.info("Queued %s %s", obj["object"], obj["id"])
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
    config_settings = config.Settings()
    engine, session_factory = get_db_engine(config_settings)
    session = session_factory()
    parser = get_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    main(session, args.filenames)
