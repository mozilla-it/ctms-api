#!/usr/bin/env python3
"""Schedule contacts to be synced to Acoustic."""
import os
import sys
from typing import Optional, TextIO

import click

from ctms import config
from ctms.crud import (
    bulk_schedule_acoustic_records,
    get_contacts_from_newsletter,
    get_contacts_from_waitlist,
    reset_retry_acoustic_records,
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
