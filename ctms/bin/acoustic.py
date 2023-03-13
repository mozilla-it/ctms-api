#!/usr/bin/env python3
"""Schedule contacts to be synced to Acoustic."""
import csv
import os
import sys
from typing import Optional, TextIO

import click

from ctms import config
from ctms.acoustic_service import CTMSToAcousticService
from ctms.crud import (
    bulk_schedule_acoustic_records,
    get_all_acoustic_fields,
    get_all_acoustic_newsletters_mapping,
    get_all_contacts,
    get_contacts_from_newsletter,
    get_contacts_from_waitlist,
)
from ctms.database import SessionLocal
from ctms.exception_capture import init_sentry
from ctms.log import configure_logging
from ctms.schemas.contact import ContactSchema


def confirm(msg):
    answer = None
    while answer not in ("", "y", "n"):
        answer = input(f"{msg} y/N ").lower()
    return answer == "y"


@click.group()
@click.pass_context
def cli(ctx):
    settings = config.Settings()
    configure_logging(logging_level=settings.logging_level.name)
    init_sentry()


@cli.command()
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    show_default=True,
    default=False,
    help="Automatic yes to prompts.",
)
@click.option("--email-file", type=click.File("r"))
@click.option("--newsletter")
@click.option("--waitlist")
@click.pass_context
def resync(
    ctx,
    yes: bool,
    email_file: TextIO,
    newsletter: Optional[str] = None,
    waitlist: Optional[str] = None,
):
    """CTMS command to sync contacts with Acoustic."""
    with SessionLocal() as dbsession:
        return do_resync(dbsession, yes, email_file, newsletter, waitlist)


def do_resync(
    dbsession, assume_yes=False, emails_file=None, newsletter=None, waitlist=None
):
    to_resync = []
    if emails_file:
        for line in emails_file.readlines():
            to_resync.append(line.rstrip().lower())

    if newsletter:
        contacts = get_contacts_from_newsletter(dbsession, newsletter)
        if not contacts:
            raise ValueError(f"Unknown newsletter {newsletter!r}")
        to_resync.extend(c.email.primary_email for c in contacts)

    if waitlist:
        contacts = get_contacts_from_waitlist(dbsession, waitlist)
        if not contacts:
            raise ValueError(f"Unknown waitlist {waitlist!r}")
        to_resync.extend(c.email.primary_email for c in contacts)

    print(f"Force resync of {len(to_resync)} contacts")
    if to_resync and (assume_yes or confirm("Continue?")):
        bulk_schedule_acoustic_records(dbsession, to_resync)
        dbsession.commit()
        print("Done.")
    return os.EX_OK


@cli.command(help="Dump the contacts database in the same format as Acoustic")
@click.option("-o", "--output", type=click.File("w"))
@click.pass_context
def dump(
    ctx,
    output: TextIO,
):
    """CTMS command to dump the contacts database."""
    if output is None:
        output = sys.stdout

    with SessionLocal() as dbsession:
        return do_dump(dbsession, output)


def do_dump(dbsession, output: TextIO):
    service = CTMSToAcousticService(
        acoustic_client=None,
        acoustic_main_table_id=-1,
        acoustic_newsletter_table_id=-1,
        acoustic_product_table_id=-1,
    )

    with SessionLocal() as dbsession:
        main_fields = {
            f.field for f in get_all_acoustic_fields(dbsession, tablename="main")
        }
        newsletters_mapping = {
            m.source: m.destination
            for m in get_all_acoustic_newsletters_mapping(dbsession)
        }

        fieldnames = None
        writer = None
        for email in get_all_contacts(dbsession):
            contact_mapping = {
                "amo": email.amo,
                "email": email,
                "fxa": email.fxa,
                "mofo": email.mofo,
                "newsletters": email.newsletters,
                "products": [],  # TODO get_stripe_products(email)
                "waitlists": email.waitlists,
            }
            contact = ContactSchema.parse_obj(contact_mapping)
            main_table_row, _, _ = service.convert_ctms_to_acoustic(
                contact, main_fields, newsletters_mapping
            )
            # Write header on the first iteration.
            if fieldnames is None:
                fieldnames = sorted(main_table_row.keys())
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
            writer.writerow(main_table_row)


if __name__ == "__main__":
    sys.exit(cli(obj={}))  # pylint: disable=no-value-for-parameter
