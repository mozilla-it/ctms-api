#!/usr/bin/env python3
"""Load csv dumps of bigquery into the db."""

import argparse
import csv
import os
import sys
from typing import Set


def main(test_args=None) -> int:
    parser = argparse.ArgumentParser(
        description="""
        Find dups
        """
    )
    parser.add_argument(
        "-d", "--dir", help="Directory containing the csv files.", required=True
    )
    parser.add_argument(
        "-c", "--collectfile", help="File to store pairs in.", required=True
    )

    args = parser.parse_args(args=test_args)
    directory = args.dir

    total = 0
    estimated_records = 87339348
    # TODO: THIS NEEDS TO WORK FOR BASKET TOKEN TOO
    with open(args.collectfile, "w") as col:
        for f in os.listdir(directory):
            if "contact_to_email" in f:
                path = os.path.join(directory, f)
                with open(path, "r", newline="") as csvfile:
                    reader = csv.DictReader(csvfile)
                    for i, line in enumerate(reader):
                        print(line["primary_email"], line["email_id"], file=col)
                        total += 1
                        if i % 100000 == 0:
                            print(
                                total,
                                estimated_records,
                                int((total / estimated_records) * 100),
                            )

    sorted_file = f"sorted_{args.collectfile}"

    # TODO: Add a shell out to sort the file here, write it to the sorted_ file

    with open(sorted_file, "r") as sorted_records:
        previous = None
        ids: Set[str] = set()
        for row in sorted_records:
            email, _, _id = row.rstrip("\n").rpartition(" ")
            if not email:
                continue  # These will get rejected in other ways
            if email != previous:
                previous = email
                if len(ids) > 0:
                    print(_id, *ids)
                    ids = set()
            else:
                ids.add(_id)

    return 0


if __name__ == "__main__":
    ret = main()  # pylint:disable = C0103
    sys.exit(ret)
