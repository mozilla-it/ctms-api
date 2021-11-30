#!/usr/bin/env python3
"""
Given a dump of csvs from bigquery, prepare it for being imported
into postgres with COPY.
"""

import argparse
import csv
import os
import sys
from time import monotonic
from typing import Any, Callable, Dict, Set

from ctms.csv_helpers import (
    NonCanonicalError,
    amo_modifier,
    email_modifier,
    fxa_modifier,
    newsletter_modifier,
    vpn_waitlist_modifier,
)


def csv_reader(
    directory,
    f,
    modifier: Callable[[int, Dict[str, Any], bool, Any, Any], Any],
    isdev: bool,
    canonical_mapping: Dict[str, str],
    skip_writes: Set[str],
    writer,
    total,
    start,
    estimated_total,
):
    path = os.path.join(directory, f)
    with open(path, "r", newline="", encoding="utf8") as csvfile:
        reader = csv.DictReader(csvfile)
        for i, line in enumerate(reader):
            total += 1
            if i % 100000 == 0:
                rps = total / (monotonic() - start)
                remaining = ((estimated_total - total) / rps) / 60
                print(
                    f"{int(total/estimated_total * 100)}% complete (processing {f}) ({rps} rows/sec) {remaining} minutes remain"
                )
            newline = {}
            for key, value in line.items():
                if value != "":
                    newline[key] = value
            try:
                row = modifier(i, newline, isdev, canonical_mapping, skip_writes)
                writer.writerow(row)
            except NonCanonicalError:
                print(
                    newline["email_id"],
                    "is non-canonical, skipping.",
                    file=sys.stderr,
                )

    # We delete the file here because we'll run out of space if we don't
    os.remove(path)


def main(test_args=None) -> int:
    parser = argparse.ArgumentParser(
        description="""
        Load csv dumps of bigquery into the db. This requires...
        """
    )
    parser.add_argument(
        "-d", "--dir", help="Directory containing the csv files.", required=True
    )
    parser.add_argument(
        "-o", "--out", help="Directory in which to write new files.", required=True
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

    # Track email_ids that we have determined should not be inserted for
    # one reason or another
    skip_writes: Set[str] = set()
    canonical_mapping: Dict[str, str] = {}

    with open(args.duplicates, "r", encoding="utf8") as dups:
        for line in dups:
            ids = line.strip("\n").split(" ")
            for _id in ids[1:]:
                canonical_mapping[_id] = ids[0]

    with open(
        os.path.join(args.out, "emails.csv"), "w", encoding="utf8"
    ) as email_out, open(
        os.path.join(args.out, "fxa.csv"), "w", encoding="utf8"
    ) as fxa_out, open(
        os.path.join(args.out, "newsletters.csv"), "w", encoding="utf8"
    ) as newsletters_out, open(
        os.path.join(args.out, "vpn_waitlist.csv"), "w", encoding="utf8"
    ) as vpn_waitlist_out, open(
        os.path.join(args.out, "amo.csv"), "w", encoding="utf8"
    ) as amo_out:
        email_writer = csv.DictWriter(
            email_out,
            fieldnames="primary_email,basket_token,sfdc_id,first_name,last_name,mailing_country,email_format,email_id,email_lang,double_opt_in,has_opted_out_of_email,unsubscribe_reason,create_timestamp,update_timestamp".split(
                ","
            ),
        )
        fxa_writer = csv.DictWriter(
            fxa_out,
            fieldnames="email_id,fxa_id,account_deleted,lang,first_service,created_date,primary_email,create_timestamp,update_timestamp".split(
                ","
            ),
        )
        newsletter_writer = csv.DictWriter(
            newsletters_out,
            fieldnames="email_id,name,subscribed,format,lang,source,unsub_reason,create_timestamp,update_timestamp".split(
                ","
            ),
        )
        vpn_waitlist_writer = csv.DictWriter(
            vpn_waitlist_out,
            fieldnames="email_id,geo,platform,create_timestamp,update_timestamp".split(
                ","
            ),
        )
        amo_writer = csv.DictWriter(
            amo_out,
            fieldnames="email_id,add_on_ids,display_name,email_opt_in,language,last_login,location,profile_url,user,user_id,username,create_timestamp,update_timestamp".split(
                ","
            ),
        )

        email_writer.writeheader()
        fxa_writer.writeheader()
        newsletter_writer.writeheader()
        vpn_waitlist_writer.writeheader()
        amo_writer.writeheader()

        total = 0
        start = monotonic()
        estimated_total = 442235069

        # First handle emails
        for f in os.listdir(directory):
            if "contact_to_email" in f:
                csv_reader(
                    directory,
                    f,
                    email_modifier,
                    isdev,
                    canonical_mapping,
                    skip_writes,
                    email_writer,
                    total,
                    start,
                    estimated_total,
                )

        for f in os.listdir(directory):
            if "contact_to_amo" in f:
                csv_reader(
                    directory,
                    f,
                    amo_modifier,
                    isdev,
                    canonical_mapping,
                    skip_writes,
                    amo_writer,
                    total,
                    start,
                    estimated_total,
                )
            elif "contact_to_fxa" in f:
                csv_reader(
                    directory,
                    f,
                    fxa_modifier,
                    isdev,
                    canonical_mapping,
                    skip_writes,
                    fxa_writer,
                    total,
                    start,
                    estimated_total,
                )
            elif "contact_to_newsletter" in f:
                csv_reader(
                    directory,
                    f,
                    newsletter_modifier,
                    isdev,
                    canonical_mapping,
                    skip_writes,
                    newsletter_writer,
                    total,
                    start,
                    estimated_total,
                )
            elif "contact_to_vpn_waitlist" in f:
                csv_reader(
                    directory,
                    f,
                    vpn_waitlist_modifier,
                    isdev,
                    canonical_mapping,
                    skip_writes,
                    vpn_waitlist_writer,
                    total,
                    start,
                    estimated_total,
                )

    return 0


if __name__ == "__main__":
    ret = main()  # pylint:disable = C0103

    sys.exit(ret)
