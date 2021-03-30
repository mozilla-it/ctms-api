#!/usr/bin/env python3
"""Load csv dumps of bigquery into the db. This is only for development testing data, it mutates stuff in a way we don't want to for real data"""

import argparse
import csv
import os
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy.orm import Session

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
            for key, value in line.items():
                if value == "":
                    # dictreader has strings for all values, but we
                    # want to override that behavior
                    line[key] = None  # type: ignore[assignment]
            yield modifier(i, line)


def _email_modifier(i: int, line: dict) -> EmailTableSchema:
    line["primary_email"] = f"{line['primary_email']}@whatever.com"
    now = datetime.now(timezone.utc)
    line["create_timestamp"] = line["create_timestamp"] or now
    line["update_timestamp"] = line["update_timestamp"] or now
    return EmailTableSchema(**line)


def _amo_modifier(i: int, line: dict) -> AddOnsTableSchema:
    newline = {}
    for key, val in line.items():
        key = re.sub("^amo_", "", key)
        newline[key] = val
    return AddOnsTableSchema(**newline)


def _fxa_modifier(i: int, line: dict) -> FirefoxAccountsTableSchema:
    if line["fxa_primary_email"]:
        line["fxa_primary_email"] = f"{line['fxa_primary_email']}@whatever.com"
    line["fxa_id"] = line["fxa_id"] or str(uuid4())
    line["created_date"] = line["create_timestamp"]
    del line["create_timestamp"]
    del line["update_timestamp"]
    newline = {}
    for key, val in line.items():
        if key != "fxa_id":
            key = re.sub("^fxa_", "", key)
        newline[key] = val
    return FirefoxAccountsTableSchema(**newline)


def _newsletter_modifier(i: int, line: dict) -> NewsletterTableSchema:
    del line["create_timestamp"]
    del line["update_timestamp"]
    newline = {}
    for key, val in line.items():
        key = re.sub("^newsletter_", "", key)
        newline[key] = val
    return NewsletterTableSchema(**newline)


def _vpn_waitlist_modifier(i: int, line: dict) -> VpnWaitlistTableSchema:
    del line["create_timestamp"]
    del line["update_timestamp"]
    newline = {}
    for key, val in line.items():
        key = re.sub("^vpn_waitlist_", "", key)
        newline[key] = val
    return VpnWaitlistTableSchema(**newline)


def main(db: Session, cfg: config.Settings, test_args=None) -> int:
    parser = argparse.ArgumentParser(
        description="""
        Load csv dumps of bigquery into the db. This requires...
        """
    )
    parser.add_argument(
        "-d", "--dir", help="Directory containing the csv files.", required=True
    )

    args = parser.parse_args(args=test_args)
    directory = args.dir
    inputs = InputIOs()
    for f in os.listdir(directory):
        if f == "CTMS_SAMPLE_contact_to_email.csv":
            inputs.emails = csv_reader(directory, f, _email_modifier)
        elif f == "CTMS_SAMPLE_contact_to_amo.csv":
            inputs.amo = csv_reader(directory, f, _amo_modifier)
        elif f == "CTMS_SAMPLE_contact_to_fxa.csv":
            inputs.fxa = csv_reader(directory, f, _fxa_modifier)
        elif f == "CTMS_SAMPLE_contact_to_newsletter.csv":
            inputs.newsletters = csv_reader(directory, f, _newsletter_modifier)
        elif f == "CTMS_SAMPLE_contact_to_vpn_waitlist.csv":
            inputs.vpn_waitlist = csv_reader(directory, f, _vpn_waitlist_modifier)
    try:
        inputs.finalize()
    except BaseException as e:  # pylint:disable = W0703
        print(e)
        return 1

    ingester = Ingester(inputs, session)
    ingester.run()

    return 0


if __name__ == "__main__":
    import sys

    # Get the database
    config_settings = config.Settings()
    engine, session_factory = get_db_engine(config_settings)
    session = session_factory()

    try:
        ret = main(session, config_settings)  # pylint:disable = C0103
    finally:
        session.close()

    sys.exit(ret)
