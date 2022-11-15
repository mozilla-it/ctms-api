#!/usr/bin/env python3
"""Manage Acoustic newsletters mapping: add and remove from the db."""

import argparse
import os
import sys

from ctms import config
from ctms.database import get_db_engine
from ctms.models import AcousticNewsletterMapping


def main(dbsession, test_args=None) -> int:
    parser = argparse.ArgumentParser(
        description="""
        Manage Acoustic Newsletter mapping
        """
    )
    subparsers = parser.add_subparsers(dest="action")
    parser_add = subparsers.add_parser("add")
    parser_add.add_argument("mapping")

    parser_remove = subparsers.add_parser("remove")
    parser_remove.add_argument("mapping")

    subparsers.add_parser("list")

    args = parser.parse_args(args=test_args)
    if args.action == "add":
        source, destination = args.mapping.split(":")
        # This will fail if mapping already exists.
        dbsession.add(AcousticNewsletterMapping(source=source, destination=destination))
        dbsession.commit()
        print("Added.")
    elif args.action == "remove":
        row = (
            dbsession.query(AcousticNewsletterMapping)
            .filter(AcousticNewsletterMapping.source == args.mapping)
            .one_or_none()
        )
        if not row:
            print(f"Unknown mapping '{args.mapping}'. Give up.")
            return os.EX_NOTFOUND
        dbsession.delete(row)
        dbsession.commit()
        print("Removed.")
    else:
        entries = dbsession.query(AcousticNewsletterMapping).all()
        print("\n".join(sorted(f"- {e.source!r} → {e.destination!r}" for e in entries)))

    return os.EX_OK


if __name__ == "__main__":
    # Get the database
    config_settings = config.Settings()
    engine, session_factory = get_db_engine(config_settings)
    session = session_factory()
    with engine.connect() as connection:
        ret = main(session)  # pylint:disable = invalid-name

    sys.exit(ret)
