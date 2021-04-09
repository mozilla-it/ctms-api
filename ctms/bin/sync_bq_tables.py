#!/usr/bin/env python3
"""Given a BQ project with some tables, ensure that the tables are synced into postgres"""

import argparse
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict
from uuid import uuid4

from google.cloud import bigquery
from pydantic import BaseModel
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


# TODO: this should probably return afunction that can be called to do this lazily
def bq_reader(
    client: bigquery.Client,
    table: str,
    modifier: Callable[[Dict[str, Any]], BaseModel],
):
    query = f"SELECT * FROM `mozilla-cdp-prod.sfdc_exports.{table}`"
    query_job_rows = client.query(query)
    for row in query_job_rows:
        newrow = {}
        for key, value in row.items():
            if value != "":
                newrow[key] = value
        yield modifier(newrow)


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


def _email_modifier(line: dict) -> EmailTableSchema:
    _ensure_timestamps(line)
    line["primary_email"] = f"{line['primary_email']}@example.com"
    return EmailTableSchema(**line)


def _amo_modifier(line: dict) -> AddOnsTableSchema:
    _ensure_timestamps(line)
    newline = {}
    for key, val in line.items():
        key = re.sub("^amo_", "", key)
        newline[key] = val
    return AddOnsTableSchema(**newline)


# TODO: every minute or every 1000 records emit how many we've done and how long it has been since the last one
# emit failures in as much data as possible
# look into python inside docker stdout flushing
# TODO: make sure that ensure_timestamp is actually useful compared to making the server_defaults work


def _fxa_modifier(line: dict) -> FirefoxAccountsTableSchema:
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


def _newsletter_modifier(line: dict) -> NewsletterTableSchema:
    _ensure_timestamps(line)
    newline = {}
    for key, val in line.items():
        key = re.sub("^newsletter_", "", key)
        newline[key] = val
    return NewsletterTableSchema(**newline)


def _vpn_waitlist_modifier(line: dict) -> VpnWaitlistTableSchema:
    _ensure_timestamps(line)
    newline = {}
    for key, val in line.items():
        key = re.sub("^vpn_waitlist_", "", key)
        newline[key] = val
    return VpnWaitlistTableSchema(**newline)


def main(db: Connection, cfg: config.Settings, test_args=None) -> int:
    parser = argparse.ArgumentParser(
        description="""
        Load bq into the db. This requires...
        """
    )
    parser.add_argument(
        "-b", "--batch-size", help="Maximum size of insert batch.", default=1000
    )

    args = parser.parse_args(args=test_args)
    inputs = InputIOs()

    # TODO: Get creds from config
    bq_client = bigquery.Client()

    inputs.emails = bq_reader(
        bq_client, "CTMS_SAMPLE_contact_to_email", _email_modifier
    )
    inputs.amo = bq_reader(bq_client, "CTMS_SAMPLE_contact_to_amo", _amo_modifier)
    inputs.fxa = bq_reader(bq_client, "CTMS_SAMPLE_contact_to_fxa", _fxa_modifier)
    inputs.newsletters = bq_reader(
        bq_client, "CTMS_SAMPLE_contact_to_newsletter", _newsletter_modifier
    )
    inputs.vpn_waitlist = bq_reader(
        bq_client, "CTMS_SAMPLE_contact_to_vpn_waitlist", _vpn_waitlist_modifier
    )
    try:
        inputs.finalize()
    except BaseException as e:  # pylint:disable = W0703
        print(e)
        return 1

    ingester = Ingester(inputs, db, args.batch_size)
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
