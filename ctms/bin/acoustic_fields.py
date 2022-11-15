#!/usr/bin/env python3
"""Manage Acoustic fields: add and remove from the db."""

import argparse
import os
import sys

from ctms import config
from ctms.database import get_db_engine
from ctms.models import AcousticField


def main(dbsession, args=None) -> int:
    parser = argparse.ArgumentParser(
        description="""
        Manage Acoustic fields
        """
    )
    subparsers = parser.add_subparsers(dest="action")
    parser_add = subparsers.add_parser("add")
    parser_add.add_argument("field")
    parser_add.add_argument(
        "--tablename", "-t", help="Acoustic table name", default="main"
    )

    parser_remove = subparsers.add_parser("remove")
    parser_remove.add_argument("field")
    parser_remove.add_argument(
        "--tablename",
        "-t",
        help="Acoustic table name (default: 'main')",
        default="main",
    )

    parser_list = subparsers.add_parser("list")
    parser_list.add_argument(
        "--tablename",
        "-t",
        help="Acoustic table name (default: 'main')",
        default="main",
    )

    args = parser.parse_args(args=args)
    if args.action == "add":
        dbsession.merge(AcousticField(tablename=args.tablename, field=args.field))
        dbsession.commit()
        print("Added.")
    elif args.action == "remove":
        row = (
            dbsession.query(AcousticField)
            .filter(
                AcousticField.tablename == args.tablename,
                AcousticField.field == args.field,
            )
            .one_or_none()
        )
        if not row:
            print(f"Unknown field '{args.tablename}.{args.field}'. Give up.")
            return os.EX_NOTFOUND
        dbsession.delete(row)
        dbsession.commit()
        print("Removed.")
    else:
        entries = dbsession.query(AcousticField).all()
        print("\n".join(sorted(f"- {e.tablename}.{e.field}" for e in entries)))

    return os.EX_OK


if __name__ == "__main__":
    # Get the database
    config_settings = config.Settings()
    engine, session_factory = get_db_engine(config_settings)
    session = session_factory()
    with engine.connect() as connection:
        ret = main(session)  # pylint:disable = invalid-name

    sys.exit(ret)
