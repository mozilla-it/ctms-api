#!/usr/bin/env python3
"""Load Stripe data from JSON."""

import argparse
import json
import logging
from typing import List, Tuple

from sqlalchemy.orm import Session

from ctms.database import SessionLocal
from ctms.ingest_stripe import (
    StripeIngestActions,
    StripeIngestUnknownObjectError,
    ingest_stripe_object,
)
from ctms.models import StripeBase

logger = logging.getLogger(__name__)


def main(db_session: Session, filenames: List[str]) -> None:
    """Load a Stripe object or list of objects from disk."""

    for filename in filenames:
        logger.info("Reading data from %s...", filename)
        with open(filename, "r", encoding="utf8") as data_file:
            data = json.load(data_file)

        if isinstance(data, dict):
            ingest_object(db_session, data)
        elif isinstance(data, list):
            for obj in data:
                if obj:
                    ingest_object(db_session, obj)


def ingest_object(db_session, obj):
    """Ingest a Stripe object."""

    try:
        ingestion_data: Tuple[StripeBase, StripeIngestActions] = ingest_stripe_object(
            db_session, obj
        )
        logger.info("Object and Actions: %s %s", ingestion_data[0], ingestion_data[1])
    except StripeIngestUnknownObjectError:
        logger.info("Skipping %s %s", obj["object"], obj["id"])
    else:
        logger.info("Ingested %s %s", obj["object"], obj["id"])
        db_session.commit()


def get_parser():
    the_parser = argparse.ArgumentParser(description="Load Stripe data from JSON")
    the_parser.add_argument(
        "filenames", metavar="data.json", nargs="+", help="Stripe data to load"
    )
    return the_parser


if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    with SessionLocal() as session:
        main(session, args.filenames)
