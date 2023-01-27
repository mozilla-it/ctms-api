#!/usr/bin/env python3
"""Manage Acoustic fields: add, list, and remove from the db."""

import argparse
import os
import sys

from ctms.crud import (
    create_acoustic_field,
    delete_acoustic_field,
    get_all_acoustic_fields,
)
from ctms.database import SessionLocal


def main(dbsession, args=None) -> int:
    parser = argparse.ArgumentParser(
        description="Manage Acoustic fields",
    )
    subparsers = parser.add_subparsers(dest="action")
    parser_add = subparsers.add_parser(
        "add", usage="""python acoustic_fields.py add "fxaid" """
    )
    parser_add.add_argument("field")
    parser_add.add_argument(
        "--tablename", "-t", help="Acoustic table name", default="main"
    )

    parser_remove = subparsers.add_parser(
        "remove", usage="""python acoustic_fields.py remove "fxaid" """
    )
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
        row = create_acoustic_field(dbsession, args.tablename, args.field)
        print(f"Added '{row.tablename}.{row.field}'.")
    elif args.action == "remove":
        row = delete_acoustic_field(dbsession, args.tablename, args.field)
        if not row:
            print(f"Unknown field '{args.tablename}.{args.field}'. Give up.")
            return os.EX_DATAERR
        print(f"Removed '{row.tablename}.{row.field}'.")
    else:
        entries = get_all_acoustic_fields(dbsession)
        print("\n".join(sorted(f"- {e.tablename}.{e.field}" for e in entries)))

    return os.EX_OK


if __name__ == "__main__":
    with SessionLocal() as session:
        sys.exit(main(session))
