#!/usr/bin/env python3
"""Given a BQ project with some tables, ensure that the tables are synced into postgres"""

import argparse
import re
from datetime import datetime, timezone
from time import monotonic
from typing import Any, Callable, Dict
from uuid import uuid4

from google.cloud import bigquery
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


def bq_reader(
    client: bigquery.Client,
    table: str,
    modifier: Callable[[Dict[str, Any]], BaseModel],
    table_index: int,
    total_tables: int,
    report_frequency: int,
):
    # TODO: Probably want some sort of ordering here, a report of where
    # we are in that ordering, and a way to resume from that place if
    # things crash
    query = f"SELECT * FROM `mozilla-cdp-prod.sfdc_exports.{table}`"
    query_job_rows = client.query(query).result()
    total_rows = query_job_rows.total_rows
    report_prefix = f"{table} (table: {table_index}/{total_tables})"
    start = monotonic()
    for i, row in enumerate(query_job_rows):
        i = i + 1
        if i % report_frequency == 0 or i == total_rows:
            percent_done = int(i / total_rows * 100)
            time_since_start = monotonic() - start
            per_second = int(i / time_since_start)
            print(
                f"{report_prefix}: {percent_done}% Complete ({per_second} rows/s) ({int(time_since_start)}s since query)"
            )
        newrow = {}
        for key, value in row.items():
            if value != "":
                newrow[key] = value
        try:
            yield modifier(newrow)
        except ValidationError as e:
            # TODO: Write this to a table so we know what didn't work
            print(newrow["email_id"], str(e))


# TODO: make sure that ensure_timestamp is actually useful compared to making the server_defaults work
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
        "-b",
        "--batch-size",
        help="Maximum size of insert batch.",
        default=1000,
        type=int,
    )
    parser.add_argument(
        "-r",
        "--report_frequency",
        help="How often (in # of rows) this will report progress.",
        default=1000,
        type=int,
    )
    parser.add_argument(
        "-p",
        "--prefix",
        help="Which prefix to use for BQ tables.",
        default="CTMS",
    )

    args = parser.parse_args(args=test_args)
    inputs = InputIOs()

    # TODO: Get creds from config
    bq_client = bigquery.Client()

    report_frequency = args.report_frequency

    inputs.emails = bq_reader(
        bq_client,
        f"{args.prefix}_contact_to_email",
        _email_modifier,
        1,
        5,
        report_frequency,
    )
    inputs.amo = bq_reader(
        bq_client,
        f"{args.prefix}_contact_to_amo",
        _amo_modifier,
        2,
        5,
        report_frequency,
    )
    inputs.fxa = bq_reader(
        bq_client,
        f"{args.prefix}_contact_to_fxa",
        _fxa_modifier,
        3,
        5,
        report_frequency,
    )
    inputs.newsletters = bq_reader(
        bq_client,
        f"{args.prefix}_contact_to_newsletter",
        _newsletter_modifier,
        4,
        5,
        report_frequency,
    )
    inputs.vpn_waitlist = bq_reader(
        bq_client,
        f"{args.prefix}_contact_to_vpn_waitlist",
        _vpn_waitlist_modifier,
        5,
        5,
        report_frequency,
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
