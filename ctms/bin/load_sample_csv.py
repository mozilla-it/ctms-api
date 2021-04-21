#!/usr/bin/env python3
"""Load csv dumps of bigquery into the db."""

import argparse
import csv
import os
import sys
from itertools import chain
from typing import Any, Callable, Dict, Set

from pydantic.error_wrappers import ValidationError
from sqlalchemy.engine import Connection

from ctms import config
from ctms.csv_helpers import (
    NonCanonicalError,
    amo_modifier,
    email_modifier,
    fxa_modifier,
    newsletter_modifier,
    vpn_waitlist_modifier,
)
from ctms.database import get_db_engine
from ctms.ingest import Ingester, InputIOs


def csv_reader(
    directory,
    f,
    modifier: Callable[[int, Dict[str, Any], bool, Any, Any], Any],
    isdev: bool,
    canonical_mapping: Dict[str, str],
    skip_writes: Set[str],
):
    path = os.path.join(directory, f)
    with open(path, "r", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for i, line in enumerate(reader):
            newline = {}
            for key, value in line.items():
                if value != "":
                    newline[key] = value
            try:
                yield modifier(i, newline, isdev, canonical_mapping, skip_writes)
            except ValidationError as e:
                # TODO: Write this to a table so we know what didn't work
                print(
                    newline["email_id"],
                    str(e),
                    file=sys.stderr,
                )
            except NonCanonicalError as e:
                print(
                    newline["email_id"],
                    "is non-canonical, skipping.",
                    file=sys.stderr,
                )


def main(db: Connection, cfg: config.Settings, test_args=None) -> int:
    parser = argparse.ArgumentParser(
        description="""
        Load csv dumps of bigquery into the db. This requires...
        """
    )
    parser.add_argument(
        "-d", "--dir", help="Directory containing the csv files.", required=True
    )
    parser.add_argument(
        "-b",
        "--batch-size",
        help="Maximum size of insert batch.",
        default=1000,
        type=int,
    )
    parser.add_argument(
        "--dev",
        help="If true, apply dev transforms",
        action="store_true",
    )
    parser.add_argument(
        "--duplicates",
        help="A spefically formatted file containing duplicate emails",
        required=True,
    )

    args = parser.parse_args(args=test_args)
    directory = args.dir
    isdev = args.dev
    inputs = InputIOs()
    total = 0

    # Track email_ids that we have determined should not be inserted for
    # one reason or another
    skip_writes: Set[str] = set()
    canonical_mapping: Dict[str, str] = {}

    with open(args.duplicates, "r") as dups:
        for line in dups:
            ids = line.strip("\n").split(" ")
            for _id in ids[1:]:
                canonical_mapping[_id] = ids[0]

    emails = []
    amos = []
    fxas = []
    newsletters = []
    vpn_waitlists = []
    for f in os.listdir(directory):
        if "contact_to_email" in f:
            total += 1
            emails.append(
                csv_reader(
                    directory, f, email_modifier, isdev, canonical_mapping, skip_writes
                )
            )
        elif "contact_to_amo" in f:
            total += 1
            amos.append(
                csv_reader(
                    directory, f, amo_modifier, isdev, canonical_mapping, skip_writes
                )
            )
        elif "contact_to_fxa" in f:
            total += 1
            fxas.append(
                csv_reader(
                    directory, f, fxa_modifier, isdev, canonical_mapping, skip_writes
                )
            )
        elif "contact_to_newsletter" in f:
            total += 1
            newsletters.append(
                csv_reader(
                    directory,
                    f,
                    newsletter_modifier,
                    isdev,
                    canonical_mapping,
                    skip_writes,
                )
            )
        elif "contact_to_vpn_waitlist" in f:
            total += 1
            vpn_waitlists.append(
                csv_reader(
                    directory,
                    f,
                    vpn_waitlist_modifier,
                    isdev,
                    canonical_mapping,
                    skip_writes,
                )
            )

    inputs.amo = chain(*amos)
    inputs.emails = chain(*emails)
    inputs.fxa = chain(*fxas)
    inputs.newsletters = chain(*newsletters)
    inputs.vpn_waitlist = chain(*vpn_waitlists)
    try:
        inputs.finalize()
    except BaseException as e:  # pylint:disable = W0703
        print(e)
        return 1

    ingester = Ingester(inputs, db, args.batch_size, total_inputs=total)
    ingester.run()

    return 0


if __name__ == "__main__":
    # Get the database
    config_settings = config.Settings()
    engine, _ = get_db_engine(config_settings)

    with engine.connect() as connection:
        ret = main(connection, config_settings)  # pylint:disable = C0103

    sys.exit(ret)
