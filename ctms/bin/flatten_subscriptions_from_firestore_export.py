#!/usr/bin/env python3

import argparse
import json
import logging
from typing import List

logger = logging.getLogger(__name__)


def allowlist_extraction(allowlist_file=None):
    allowlist = None
    if allowlist_file:
        with open(allowlist_file, "r", encoding="utf8") as data_file:
            data = json.load(data_file)
            allowlist = data
    return allowlist


def main(filenames: List[str], env="prod", allowlist_file=None) -> None:
    logger.info("Running script with params: %s %s %s", filenames, allowlist_file, env)
    allowlist = allowlist_extraction(allowlist_file)

    flattened_json = []
    for filename in filenames:
        logger.info("Reading data from %s...", filename)
        with open(filename, "r", encoding="utf8") as data_file:
            data = json.load(data_file)
            customer_collection = data.get(f"fxa-auth-{env}-stripe-customers")
            for _, customer in customer_collection.items():
                _object = customer.get("object")
                cus_allowed = not allowlist or customer.get("id") in allowlist
                if _object and cus_allowed:
                    logger.info("Customer data allowed %s...", customer.get("id"))
                    flattened_json.append(customer)
                subscription_collection = customer.get(
                    f"fxa-auth-{env}-stripe-subscriptions"
                )
                if subscription_collection:
                    for _, subscription in subscription_collection.items():
                        sub_allowed = cus_allowed or subscription.get("id") in allowlist
                        _object = subscription.get("object")
                        if _object and sub_allowed:
                            logger.info(
                                "Subscription data allowed %s...",
                                subscription.get("id"),
                            )
                            new_items = subscription["items"]["data"]
                            subscription["items"]["data"] = [new_items]
                            flattened_json.append(subscription)
                        invoice_collection = subscription.get(
                            f"fxa-auth-{env}-stripe-invoices"
                        )
                        for _, invoice in invoice_collection.items():
                            inv_allowed = sub_allowed or invoice.get("id") in allowlist
                            _object = invoice.get("object")
                            customer = invoice.get("customer")
                            if customer:
                                inv_allowed = inv_allowed or customer in allowlist

                            if _object and inv_allowed:
                                new_items = [invoice["lines"]["data"]]
                                invoice["lines"]["data"] = new_items
                                logger.info(
                                    "Invoice data allowed %s...", invoice.get("id")
                                )
                                flattened_json.append(invoice)
        new_filename = filename.replace(".json", "_ctms_parsable.json")
        with open(new_filename, "w", encoding="utf8") as new_data_file:
            json.dump(flattened_json, new_data_file, indent=4)
            logger.info("Loading data into %s...", new_filename)


def get_parser():
    the_parser = argparse.ArgumentParser(
        description="Flatten Firestore json data export"
    )
    the_parser.add_argument(
        "filenames",
        metavar="data.json",
        nargs="+",
        help="Firestore data blobs to flatten",
    )
    the_parser.add_argument("--env", help="Env: stage, prod", default="prod")
    the_parser.add_argument(
        "--allowlist", help="Stripe IDs that are allowed", nargs="?", default=None
    )
    return the_parser


if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    main(args.filenames, args.env, args.allowlist)
