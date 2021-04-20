#!/usr/bin/env python3
"""Load csv dumps of bigquery into the db."""

import argparse
import csv
import os
import re
import sys
from datetime import datetime, timezone
from itertools import chain
from typing import Any, Callable, Dict, Set
from uuid import uuid4

from pydantic import BaseModel
from pydantic.error_wrappers import ValidationError
from sqlalchemy.engine import Connection

from ctms import config
from ctms.database import get_db_engine
from ctms.ingest import Ingester, InputIOs
from ctms.schemas import (
    AddOnsTableSchema,
    EmailTableSchema,
    FirefoxAccountsTableSchema,
    NewsletterTableSchema,
    VpnWaitlistTableSchema,
)

# Track email_ids that we have determined should not be inserted for
# one reason or another
skip_writes: Set[str] = set()
canonical_mapping: Dict[str, str] = {}


class NonCanonicalError(BaseException):
    pass


def csv_reader(
    directory,
    f,
    modifier: Callable[[int, Dict[str, Any], bool], BaseModel],
    isdev: bool,
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
                yield modifier(i, newline, isdev)
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


def _ensure_timestamps(line: dict):
    create_ts = line.get("create_timestamp")
    update_ts = line.get("update_timestamp")
    if create_ts and update_ts:
        return

    if create_ts and not update_ts:
        line["update_timestamp"] = create_ts
    elif not create_ts and update_ts:
        line["create_timestamp"] = update_ts
    else:
        line["create_timestamp"] = datetime.now(timezone.utc)
        line["update_timestamp"] = datetime.now(timezone.utc)


def _email_modifier(i: int, line: dict, isdev: bool) -> EmailTableSchema:
    if canonical_mapping.get(line["email_id"]):
        raise NonCanonicalError  # We don't insert non-canonical email records
    _ensure_timestamps(line)
    if isdev:
        line["primary_email"] = f"{line['primary_email']}@example.com"

    # Only for emails, we add to the skip_writes list since
    # rows in other tables don't make sense with missing email row
    try:
        return EmailTableSchema(**line)
    except ValidationError as e:
        skip_writes.add(line["email_id"])
        raise e


def _amo_modifier(i: int, line: dict, isdev: bool) -> AddOnsTableSchema:
    if canonical_mapping.get(line["email_id"]):
        raise NonCanonicalError  # We don't insert non-canonical email records
    _ensure_timestamps(line)
    newline = {}
    for key, val in line.items():
        key = re.sub("^amo_", "", key)
        newline[key] = val
    return AddOnsTableSchema(**newline)


def _fxa_modifier(i: int, line: dict, isdev: bool) -> FirefoxAccountsTableSchema:
    if canonical_mapping.get(line["email_id"]):
        raise NonCanonicalError  # We don't insert non-canonical email records
    _ensure_timestamps(line)
    if isdev:
        if line.get("fxa_primary_email"):
            line["fxa_primary_email"] = f"{line['fxa_primary_email']}@example.com"
        line.setdefault("fxa_id", str(uuid4()))
    newline = {}
    for key, val in line.items():
        if key != "fxa_id":
            key = re.sub("^fxa_", "", key)
        newline[key] = val
    return FirefoxAccountsTableSchema(**newline)


def _newsletter_modifier(i: int, line: dict, isdev: bool) -> NewsletterTableSchema:

    # For newsletters only, we actually replace the email_id
    # with the canonical id so that we don't lose subscriptions
    canonical_id = canonical_mapping.get(line["email_id"])
    if canonical_id:
        line["email_id"] = canonical_id

    _ensure_timestamps(line)
    newline = {}
    for key, val in line.items():
        key = re.sub("^newsletter_", "", key)
        newline[key] = val
    return NewsletterTableSchema(**newline)


def _vpn_waitlist_modifier(i: int, line: dict, isdev: bool) -> VpnWaitlistTableSchema:
    if canonical_mapping.get(line["email_id"]):
        raise NonCanonicalError  # We don't insert non-canonical email records
    _ensure_timestamps(line)
    newline = {}
    for key, val in line.items():
        key = re.sub("^vpn_waitlist_", "", key)
        newline[key] = val
    return VpnWaitlistTableSchema(**newline)


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
            emails.append(csv_reader(directory, f, _email_modifier, isdev))
        elif "contact_to_amo" in f:
            total += 1
            amos.append(csv_reader(directory, f, _amo_modifier, isdev))
        elif "contact_to_fxa" in f:
            total += 1
            fxas.append(csv_reader(directory, f, _fxa_modifier, isdev))
        elif "contact_to_newsletter" in f:
            total += 1
            newsletters.append(csv_reader(directory, f, _newsletter_modifier, isdev))
        elif "contact_to_vpn_waitlist" in f:
            total += 1
            vpn_waitlists.append(
                csv_reader(directory, f, _vpn_waitlist_modifier, isdev)
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
