#!/usr/bin/env python3
"""Schedule contacts to be synced to Acoustic."""
import csv
import os
import sys
from typing import Optional, TextIO
from uuid import UUID

import click
import sqlalchemy

from ctms import config
from ctms.acoustic_service import CTMSToAcousticService
from ctms.crud import (
    bulk_schedule_acoustic_records,
    create_acoustic_field,
    create_acoustic_newsletters_mapping,
    delete_acoustic_field,
    delete_acoustic_newsletters_mapping,
    get_all_acoustic_fields,
    get_all_acoustic_newsletters_mapping,
    get_all_contacts_from_ids,
    get_contacts_from_newsletter,
    get_contacts_from_waitlist,
    reset_retry_acoustic_records,
)
from ctms.database import SessionLocal
from ctms.exception_capture import init_sentry
from ctms.log import configure_logging
from ctms.schemas.contact import ContactSchema, get_stripe_products


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
@click.option(
    "--reset-retries",
    is_flag=True,
    show_default=True,
    default=False,
    help="Reset retry count of failing contacts",
)
@click.option("--email-file", type=click.File("r"))
@click.option("--newsletter")
@click.option("--waitlist")
@click.pass_context
def resync(
    ctx,
    yes: bool,
    reset_retries: bool,
    email_file: TextIO,
    newsletter: Optional[str] = None,
    waitlist: Optional[str] = None,
):
    """CTMS command to sync contacts with Acoustic."""
    with SessionLocal() as dbsession:
        return do_resync(
            dbsession, yes, reset_retries, email_file, newsletter, waitlist
        )


@cli.group(help="Manage Acoustic fields")
@click.pass_context
def fields(ctx):
    pass


@fields.command(name="list")
@click.option(
    "-t", "--tablename", default="main", help="Acoustic table name (default: 'main')"
)
@click.pass_context
def fields_list(ctx, tablename):
    with SessionLocal() as dbsession:
        entries = get_all_acoustic_fields(dbsession)
    print("\n".join(sorted(f"- {e.tablename}.{e.field}" for e in entries)))


@fields.command(name="add")
@click.option(
    "-t", "--tablename", default="main", help="Acoustic table name (default: 'main')"
)
@click.argument("field")
@click.pass_context
def fields_add(ctx, field, tablename):
    with SessionLocal() as dbsession:
        row = create_acoustic_field(dbsession, tablename, field)
    print(f"Added '{row.tablename}.{row.field}'.")


@fields.command(name="remove")
@click.option(
    "-t", "--tablename", default="main", help="Acoustic table name (default: 'main')"
)
@click.argument("field")
@click.pass_context
def fields_remove(ctx, field, tablename):
    with SessionLocal() as dbsession:
        row = delete_acoustic_field(dbsession, tablename, field)
    if not row:
        print(f"Unknown field '{tablename}.{field}'. Give up.")
        return os.EX_DATAERR
    print(f"Removed '{row.tablename}.{row.field}'.")
    return os.EX_OK


@cli.group(name="newsletter-mappings", help="Manage newsletter Acoustic mappings")
@click.pass_context
def newsletter_mappings(ctx):
    pass


@newsletter_mappings.command(name="list")
@click.pass_context
def newsletter_mappings_list(ctx):
    with SessionLocal() as dbsession:
        entries = get_all_acoustic_newsletters_mapping(dbsession)
    print("\n".join(sorted(f"- {e.source!r} → {e.destination!r}" for e in entries)))
    return os.EX_OK


@newsletter_mappings.command(
    name="add", help='Specified as "<newsletter-name>:<acoustic-column>"'
)
@click.argument("mapping")
@click.pass_context
def newsletter_mappings_add(ctx, mapping):
    source, destination = mapping.split(":")
    # This will fail if mapping already exists.
    with SessionLocal() as dbsession:
        create_acoustic_newsletters_mapping(dbsession, source, destination)
    print(f"Added {source!r} → {destination!r}.")
    return os.EX_OK


@newsletter_mappings.command(name="remove")
@click.argument("source")
@click.pass_context
def newsletter_mappings_remove(ctx, source):
    with SessionLocal() as dbsession:
        row = delete_acoustic_newsletters_mapping(dbsession, source)
    if not row:
        print(f"Unknown mapping '{source}'. Give up.")
        return os.EX_DATAERR
    print(f"Removed {row.source!r} → {row.destination!r}.")
    return os.EX_OK


def do_resync(
    dbsession,
    assume_yes=False,
    reset_retries=False,
    emails_file=None,
    newsletter=None,
    waitlist=None,
):
    resetted = 0
    if reset_retries:
        resetted = reset_retry_acoustic_records(dbsession)

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

    print(f"Force resync of {resetted + len(to_resync)} contacts")
    if to_resync and (assume_yes or confirm("Continue?")):
        bulk_schedule_acoustic_records(dbsession, to_resync)
    dbsession.commit()
    print("Done.")
    return os.EX_OK


@cli.command(help="Dump the contacts database in the same format as Acoustic")
@click.option(
    "-q",
    "--query",
    help="Query to select contacts to be dumped",
    default="SELECT email_id FROM emails;",
)
@click.option("-o", "--output", type=click.File("w"))
@click.pass_context
def dump(
    ctx,
    query: str,
    output: TextIO,
):
    """CTMS command to dump the contacts database."""
    if output is None:
        output = sys.stdout

    with SessionLocal() as dbsession:
        result = dbsession.execute(sqlalchemy.text(query))
        email_ids = [row[0] for row in result.all()]

        if not email_ids:
            print("No contact found for query.")
            sys.exit(os.EX_UNAVAILABLE)

        first = email_ids[0]
        if not isinstance(first, UUID):
            print(f"Query should return UUID, found: {first}")
            sys.exit(os.EX_USAGE)

        answer = input(f"Dump CSV for {len(email_ids)} contacts [y/N]? ")
        if not answer or answer.lower() != "y":
            sys.exit(os.EX_OK)

        contacts = get_all_contacts_from_ids(dbsession, email_ids=email_ids)
        return do_dump(dbsession, contacts, output)


def do_dump(dbsession, contacts, output: TextIO):
    service = CTMSToAcousticService(
        acoustic_client=None,
        acoustic_main_table_id=-1,
        acoustic_newsletter_table_id=-1,
        acoustic_product_table_id=-1,
    )
    main_fields = {
        f.field for f in get_all_acoustic_fields(dbsession, tablename="main")
    }
    newsletters_mapping = {
        m.source: m.destination for m in get_all_acoustic_newsletters_mapping(dbsession)
    }

    fieldnames = None
    writer = None
    for email in contacts:
        contact_mapping = {
            "amo": email.amo,
            "email": email,
            "fxa": email.fxa,
            "mofo": email.mofo,
            "newsletters": email.newsletters,
            "products": get_stripe_products(email),
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
