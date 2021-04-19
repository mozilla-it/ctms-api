#!/usr/bin/env python3
"""Load csv dumps of bigquery into the db. This is only for development testing data, it mutates stuff in a way we don't want to for real data"""

import argparse
import csv
import os
import re
from datetime import datetime, timezone
from itertools import chain
from typing import Any, Callable, Dict
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


def csv_reader(directory, f, modifier: Callable[[int, Dict[str, Any]], BaseModel]):
    path = os.path.join(directory, f)
    with open(path, "r", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for i, line in enumerate(reader):
            newline = {}
            for key, value in line.items():
                if value != "":
                    newline[key] = value
            try:
                yield modifier(i, newline)
            except ValidationError as e:
                # TODO: Write this to a table so we know what didn't work
                print(
                    newline["email_id"],
                    str(e),
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


def _email_modifier(i: int, line: dict) -> EmailTableSchema:
    _ensure_timestamps(line)
    line["primary_email"] = f"{line['primary_email']}@example.com"
    return EmailTableSchema(**line)


def _amo_modifier(i: int, line: dict) -> AddOnsTableSchema:
    _ensure_timestamps(line)
    newline = {}
    for key, val in line.items():
        key = re.sub("^amo_", "", key)
        newline[key] = val
    return AddOnsTableSchema(**newline)


def _fxa_modifier(i: int, line: dict) -> FirefoxAccountsTableSchema:
    _ensure_timestamps(line)
    if line.get("fxa_primary_email"):
        line["fxa_primary_email"] = f"{line['fxa_primary_email']}@example.com"
    line.setdefault("fxa_id", str(uuid4()))
    newline = {}
    for key, val in line.items():
        if key != "fxa_id":
            key = re.sub("^fxa_", "", key)
        newline[key] = val
    return FirefoxAccountsTableSchema(**newline)


def _newsletter_modifier(i: int, line: dict) -> NewsletterTableSchema:
    _ensure_timestamps(line)
    newline = {}
    for key, val in line.items():
        key = re.sub("^newsletter_", "", key)
        newline[key] = val
    return NewsletterTableSchema(**newline)


def _vpn_waitlist_modifier(i: int, line: dict) -> VpnWaitlistTableSchema:
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

    args = parser.parse_args(args=test_args)
    directory = args.dir
    inputs = InputIOs()
    total = 0

    emails = []
    amos = []
    fxas = []
    newsletters = []
    vpn_waitlists = []
    for f in os.listdir(directory):
        if "contact_to_email" in f:
            total += 1
            emails.append(csv_reader(directory, f, _email_modifier))
        elif "contact_to_amo" in f:
            total += 1
            amos.append(csv_reader(directory, f, _amo_modifier))
        elif "contact_to_fxa" in f:
            total += 1
            fxas.append(csv_reader(directory, f, _fxa_modifier))
        elif "contact_to_newsletter" in f:
            total += 1
            newsletters.append(csv_reader(directory, f, _newsletter_modifier))
        elif "contact_to_vpn_waitlist" in f:
            total += 1
            vpn_waitlists.append(csv_reader(directory, f, _vpn_waitlist_modifier))

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
    import sys

    # Get the database
    config_settings = config.Settings()
    engine, _ = get_db_engine(config_settings)

    with engine.connect() as connection:
        ret = main(connection, config_settings)  # pylint:disable = C0103

    sys.exit(ret)
