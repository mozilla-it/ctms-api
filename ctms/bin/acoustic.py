#!/usr/bin/env python3
"""Schedule contacts to be synced to Acoustic."""
import os
import sys
from typing import Optional, TextIO

import click

from ctms import config
from ctms.crud import (
    bulk_schedule_acoustic_records,
    create_acoustic_field,
    delete_acoustic_field,
    get_all_acoustic_fields,
    get_contacts_from_newsletter,
    get_contacts_from_waitlist,
)
from ctms.database import SessionLocal
from ctms.exception_capture import init_sentry
from ctms.log import configure_logging


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
    entries = get_all_acoustic_fields(ctx.obj["dbsession"])
    print("\n".join(sorted(f"- {e.tablename}.{e.field}" for e in entries)))


@fields.command(name="add")
@click.option(
    "-t", "--tablename", default="main", help="Acoustic table name (default: 'main')"
)
@click.argument("field")
@click.pass_context
def fields_add(ctx, field, tablename):
    row = create_acoustic_field(ctx.obj["dbsession"], tablename, field)
    print(f"Added '{row.tablename}.{row.field}'.")


@fields.command(name="remove")
@click.option(
    "-t", "--tablename", default="main", help="Acoustic table name (default: 'main')"
)
@click.argument("field")
@click.pass_context
def fields_remove(ctx, field, tablename):
    row = delete_acoustic_field(ctx.obj["dbsession"], tablename, field)
    if not row:
        print(f"Unknown field '{tablename}.{field}'. Give up.")
        return os.EX_DATAERR
    print(f"Removed '{row.tablename}.{row.field}'.")


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


if __name__ == "__main__":
    sys.exit(cli(obj={}))  # pylint: disable=no-value-for-parameter
