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
)
from ctms.database import SessionLocal
from ctms.exception_capture import init_sentry
from ctms.log import configure_logging


@click.group()
@click.pass_context
def cli(ctx):
    settings = config.Settings()
    configure_logging(logging_level=settings.logging_level.name)
    init_sentry()


@cli.command()
@click.option("--email-file", type=click.File("r"))
@click.option("--newsletter")
@click.option("--waitlist")
@click.pass_context
def resync(
    ctx,
    email_file: TextIO,
    newsletter: Optional[str] = None,
    waitlist: Optional[str] = None,
):
    """CTMS command to sync contacts with Acoustic."""
    with SessionLocal() as dbsession:
        return do_resync(dbsession, emails_file, newsletter, waitlist)


def do_resync(dbsession, emails_file=None, newsletter=None, waitlist=None):
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

    print("Force resync of %s contacts", len(to_resync))
    bulk_schedule_acoustic_records(dbsession, to_resync)
    dbsession.commit()
    return os.EX_OK


if __name__ == "__main__":
    sys.exit(cli(obj={}))  # pylint: disable=no-value-for-parameter
