#!/usr/bin/env python3
"""Manage Acoustic newsletters mapping: add, list, and remove from the db."""

import argparse
import os
import sys

from ctms import config
from ctms.crud import (
    create_acoustic_newsletters_mapping,
    delete_acoustic_newsletters_mapping,
    get_all_acoustic_newsletters_mapping,
)
from ctms.database import get_db_engine


def main(dbsession, test_args=None) -> int:
    parser = argparse.ArgumentParser(
        description="Manage Acoustic Newsletter mapping",
    )
    subparsers = parser.add_subparsers(dest="action")
    parser_add = subparsers.add_parser(
        "add",
        usage="""python acoustic_newsletters_mapping.py add "test-pilot:sub_new_test_pilot" """,
    )
    parser_add.add_argument(
        "mapping", help="Add newsletter mapping specified as 'source:destination'"
    )

    parser_remove = subparsers.add_parser(
        "remove",
        usage="""python acoustic_newsletters_mapping.py remove "test-pilot" """,
    )
    parser_remove.add_argument(
        "source", help="Remove newsletter mapping with specified 'source'"
    )

    subparsers.add_parser("list")

    args = parser.parse_args(args=test_args)
    if args.action == "add":
        source, destination = args.mapping.split(":")
        # This will fail if mapping already exists.
        create_acoustic_newsletters_mapping(dbsession, source, destination)
        print(f"Added {source!r} → {destination!r}.")
    elif args.action == "remove":
        row = delete_acoustic_newsletters_mapping(dbsession, args.source)
        if not row:
            print(f"Unknown mapping '{args.source}'. Give up.")
            return os.EX_DATAERR
        print(f"Removed {row.source!r} → {row.destination!r}.")
    else:
        entries = get_all_acoustic_newsletters_mapping(dbsession)
        print("\n".join(sorted(f"- {e.source!r} → {e.destination!r}" for e in entries)))

    return os.EX_OK


if __name__ == "__main__":
    config_settings = config.Settings()
    engine, session_factory = get_db_engine(config_settings)
    session = session_factory()
    with engine.connect() as connection:
        return_code = main(session)  # pylint:disable = invalid-name

    sys.exit(return_code)
