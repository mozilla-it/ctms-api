#!/usr/bin/env python3
"""Schedule contacts to be synced to Acoustic."""
import sys

import click
import structlog

from ctms import config
from ctms.crud import (
    bulk_schedule_acoustic_records,
    get_contacts_from_newsletter,
    get_contacts_from_waitlist,
)
from ctms.database import SessionLocal
from ctms.exception_capture import init_sentry
from ctms.log import configure_logging

logger = structlog.get_logger("ctms.bin.acoustic_resync")


@click.command()
@click.option("--email-list", type=click.File("r"))
@click.option("--newsletter")
@click.option("--waitlist")
def main(email_list=None, newsletter=None, waitlist=None):
    """CTMS command to sync contacts with Acoustic."""

    with SessionLocal() as session:
        sys.exit(resync(session, email_list, newsletter, waitlist))


def resync(dbsession, email_list=None, newsletter=None, waitlist=None):
    settings = config.Settings()
    init_sentry()
    configure_logging(logging_level=settings.logging_level.name)

    to_resync = []
    if email_list:
        for line in email_list.readlines():
            to_resync.append(line.decode("utf-8").rstrip().lower())

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

    logger.info("Force resync of %s contacts", len(to_resync))
    bulk_schedule_acoustic_records(dbsession, to_resync)
    dbsession.commit()


if __name__ == "__main__":
    sys.exit(main())
