"""Test core ingestion logic"""
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from ctms.ingest import Ingester, InputIOs
from ctms.models import AmoAccount, Email, Newsletter, Waitlist
from ctms.schemas import (
    AddOnsTableSchema,
    EmailTableSchema,
    NewsletterTableSchema,
    WaitlistTableSchema,
)


def test_input_io_can_finalize():
    ios = InputIOs()
    ios.amo = iter(())
    ios.emails = iter(())
    ios.fxa = iter(())
    ios.newsletters = iter(())
    ios.waitlists = iter(())
    ios.finalize()


def test_input_io_rejects_if_empty():
    ios = InputIOs()
    with pytest.raises(BaseException) as e:
        ios.finalize()

        assert "fxa" in str(e)


def test_input_io_rejects_if_incomplete():
    ios = InputIOs()
    ios.fxa = iter(())
    with pytest.raises(BaseException) as e:
        ios.finalize()

        assert "fxa" not in str(e)


@pytest.fixture
def empty_ios():
    ios = InputIOs()
    ios.amo = iter(())
    ios.emails = iter(())
    ios.fxa = iter(())
    ios.newsletters = iter(())
    ios.waitlists = iter(())
    ios.finalize()
    return ios


def _check_saved(dbsession, emails=None, amos=None, newsletters=None, waitlists=None):
    if emails:
        saved_emails = dbsession.query(Email).all()
        assert len(saved_emails) == len(emails)
    if amos:
        saved_amos = dbsession.query(AmoAccount).all()
        assert len(saved_amos) == len(amos)
    if newsletters:
        saved_newsletters = dbsession.query(Newsletter).all()
        assert len(saved_newsletters) == len(newsletters)
    if waitlists:
        saved_waitlists = dbsession.query(Waitlist).all()
        assert len(saved_waitlists) == len(waitlists)


def test_ingest_empty(connection, empty_ios):
    ingester = Ingester(empty_ios, connection)
    ingester.run()


@pytest.mark.parametrize("batch_size", [10, 1, 2, 100])
def test_ingest_only_emails(connection, empty_ios, dbsession, batch_size):
    emails = [
        EmailTableSchema(
            email_id=uuid4(),
            primary_email="foo@example.com",
            create_timestamp=datetime.now(timezone.utc),
            update_timestamp=datetime.now(timezone.utc),
        ).dict(),
        EmailTableSchema(
            email_id=uuid4(),
            primary_email="bar@example.com",
            create_timestamp=datetime.now(timezone.utc),
            update_timestamp=datetime.now(timezone.utc),
        ).dict(),
        EmailTableSchema(
            email_id=uuid4(),
            primary_email="baz@example.com",
            create_timestamp=datetime.now(timezone.utc),
            update_timestamp=datetime.now(timezone.utc),
        ).dict(),
        EmailTableSchema(
            email_id=uuid4(),
            primary_email="bing@example.com",
            create_timestamp=datetime.now(timezone.utc),
            update_timestamp=datetime.now(timezone.utc),
        ).dict(),
    ]
    empty_ios.emails = emails
    ingester = Ingester(empty_ios, connection, batch_size=batch_size)
    ingester.run()
    _check_saved(dbsession, emails)


@pytest.mark.parametrize("batch_size", [10, 1, 2, 100])
def test_ingest_emails_and_amo(connection, empty_ios, dbsession, batch_size):
    emails = [
        EmailTableSchema(
            email_id=uuid4(),
            primary_email="foo@example.com",
            create_timestamp=datetime.now(timezone.utc),
            update_timestamp=datetime.now(timezone.utc),
        ).dict()
    ]
    amos = [
        AddOnsTableSchema(
            email_id=emails[0]["email_id"],
            create_timestamp=datetime.now(timezone.utc),
            update_timestamp=datetime.now(timezone.utc),
        ).dict()
    ]
    empty_ios.emails = emails
    empty_ios.amo = amos
    ingester = Ingester(empty_ios, connection, batch_size=batch_size)
    ingester.run()
    _check_saved(dbsession, emails, amos)


@pytest.mark.parametrize("batch_size", [10, 1, 2, 100])
def test_ingest_emails_and_newsletters_and_waitlists(
    connection, empty_ios, dbsession, batch_size
):
    emails = [
        EmailTableSchema(
            email_id=uuid4(),
            primary_email="foo@example.com",
            create_timestamp=datetime.now(timezone.utc),
            update_timestamp=datetime.now(timezone.utc),
        ).dict()
    ]
    newsletters = [
        NewsletterTableSchema(
            email_id=emails[0]["email_id"],
            name="FOO",
            create_timestamp=datetime.now(timezone.utc),
            update_timestamp=datetime.now(timezone.utc),
        ).dict(),
        NewsletterTableSchema(
            email_id=emails[0]["email_id"],
            name="BAR",
            create_timestamp=datetime.now(timezone.utc),
            update_timestamp=datetime.now(timezone.utc),
        ).dict(),
        NewsletterTableSchema(
            email_id=emails[0]["email_id"],
            name="BAZ",
            create_timestamp=datetime.now(timezone.utc),
            update_timestamp=datetime.now(timezone.utc),
        ).dict(),
    ]
    waitlists = [
        WaitlistTableSchema(
            email_id=emails[0]["email_id"],
            name="fans",
            geo="mx",
            create_timestamp=datetime.now(timezone.utc),
            update_timestamp=datetime.now(timezone.utc),
        ).dict(),
    ]
    empty_ios.emails = emails
    empty_ios.newsletters = newsletters
    empty_ios.waitlists = waitlists
    ingester = Ingester(empty_ios, connection, batch_size=batch_size)
    ingester.run()
    _check_saved(dbsession, emails, newsletters=newsletters, waitlists=waitlists)
