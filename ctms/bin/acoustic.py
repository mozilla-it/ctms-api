#!/usr/bin/env python3
"""Schedule contacts to be synced to Acoustic."""
import csv
import datetime
import os
import sys
from typing import Optional, TextIO

import click

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
    get_all_contacts,
    get_contacts_from_newsletter,
    get_contacts_from_waitlist,
    reset_retry_acoustic_records,
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


@cli.command()
@click.argument("dump-file", type=click.File("r"))
@click.pass_context
def compare(ctx, dump_file):
    # Build a set of email IDs, to compare with the Acoustic dump.
    db_email_ids = {}
    with SessionLocal() as dbsession:
        for contact in get_all_contacts(dbsession):
            db_email_ids[str(contact.email_id)] = contact.primary_email
    print(f"{len(db_email_ids)} contacts selected in database.")

    reader = csv.DictReader(dump_file)
    acoustic_extras = {}
    i = 0
    for row in reader:
        if i % (len(db_email_ids) / 1000) == 0:
            print(".", end="")
        email_id = row["email_id"]
        try:
            del db_email_ids[email_id]
        except KeyError:
            acoustic_extras[email_id] = row
        i += 1
    total_csv_rows = i

    print()
    if db_email_ids:
        print(f"{len(db_email_ids)} extraneous contacts in CTMS")
        if confirm("Export data?"):
            # Write primary emails into file. To be potentially used by `delete_bulk.py`.
            filename = f"{datetime.datetime.now().isoformat()}.ctms-extras.csv"
            print(f"Writing file {filename}...", end="")
            with open(filename, "w", encoding="utf8") as f:
                f.writelines(db_email_ids.values())
            print("Done.")

    if acoustic_extras:
        print(f"{len(acoustic_extras)} extraneous contacts in Acoustic")
        if confirm("Export data?"):
            filename = f"{datetime.datetime.now().isoformat()}.acoustic-extras.csv"
            print(f"Writing file {filename}...", end="")
            with open(filename, "w", encoding="utf8") as f:
                writer = None
                for row in acoustic_extras.values():
                    if writer is None:
                        writer = csv.DictWriter(f, fieldnames=row.keys())
                        writer.writeheader()
                    writer.writerow(row)
            print("Done.")

    has_major_diff = db_email_ids or acoustic_extras
    if has_major_diff or not confirm("Compare individual records?"):
        return os.EX_OK

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

        iterator_db = iter(get_all_contacts(dbsession).all()) # TODO: yield_per(1000)
        iterator_acoustic = csv.DictReader(dump_file)

        filename = f"{datetime.datetime.now().isoformat()}.acoustic-diff.csv"
        with open(filename, "w", encoding="utf8") as output:
            i = 0
            writer = None
            while True:
                if i % (total_csv_rows / 1000) == 0:
                    print(".", end="")
                i += 1
                try:
                    # This assumes that both sources are sorted consistently.
                    email = next(iterator_db)
                    csv_row = next(iterator_acoustic)
                except StopIteration:
                    break

                if email.email_id != csv_row["email_id"]:
                    raise ValueError(
                        f"Rows are unsync ({email.email_id} != {csv_row['email_id']}). Cannot proceed with line to line comparison."
                    )

                # Build Acoustic row from database record.
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
                # Compare naively.
                stripped_csv_row = {
                    k: v
                    for k, v in csv_row.items()
                    if k
                    not in (
                        "RECIPIENT_ID",
                        "Email",
                        "Opt In Date",
                        "Opted Out",
                        "Opt In Details",
                        "Email Type",
                        "Opted Out Date",
                        "Opt Out Details",
                        "CRM LeadSource",
                        "Last Modified Date",
                        "Clicked Date",
                        "FLAG_FOR_CONTACT_DELETION",
                        "Open Date",
                        "Sent Date",
                    )
                }
                print(i, stripped_csv_row == main_table_row)
                if stripped_csv_row == main_table_row:
                    continue
                # Write diff to file.
                if writer is None:
                    print(f"Writing file {filename}...", end="")
                    writer = csv.DictWriter(
                        output, fieldnames=("__source__",) + tuple(csv_row.keys())
                    )
                    writer.writeheader()
                writer.writerow({"__source__": "acoustic", **csv_row})
                writer.writerow({"__source__": "ctms", **main_table_row})
            print("Done.")

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


if __name__ == "__main__":
    sys.exit(cli(obj={}))  # pylint: disable=no-value-for-parameter
