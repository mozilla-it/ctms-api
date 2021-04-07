"""Test core ingestion logic"""
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from ctms.ingest import Ingester, InputIOs
from ctms.models import AmoAccount, Email, Newsletter
from ctms.schemas import AddOnsTableSchema, EmailTableSchema, NewsletterTableSchema


def test_input_io_can_finalize():
    ios = InputIOs()
    ios.amo = iter(())
    ios.emails = iter(())
    ios.fxa = iter(())
    ios.vpn_waitlist = iter(())
    ios.newsletters = iter(())
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
    ios.vpn_waitlist = iter(())
    ios.newsletters = iter(())
    ios.finalize()
    return ios


def _check_saved(dbsession, emails=None, amos=None, newsletters=None):
    if emails:
        saved_emails = dbsession.query(Email).all()
        assert len(saved_emails) == len(emails)
    if amos:
        saved_amos = dbsession.query(AmoAccount).all()
        assert len(saved_amos) == len(amos)
    if newsletters:
        saved_newsletters = dbsession.query(Newsletter).all()
        assert len(saved_newsletters) == len(newsletters)


def test_ingest_empty(connection, empty_ios):
    ingester = Ingester(empty_ios, connection)


@pytest.mark.parametrize("batch_size", [10, 1, 2, 100])
def test_ingest_only_emails(connection, empty_ios, dbsession, batch_size):
    emails = [
        EmailTableSchema(
            email_id=uuid4(),
            primary_email="foo@example.com",
            create_timestamp=datetime.now(timezone.utc),
            update_timestamp=datetime.now(timezone.utc),
        ),
        EmailTableSchema(
            email_id=uuid4(),
            primary_email="bar@example.com",
            create_timestamp=datetime.now(timezone.utc),
            update_timestamp=datetime.now(timezone.utc),
        ),
        EmailTableSchema(
            email_id=uuid4(),
            primary_email="baz@example.com",
            create_timestamp=datetime.now(timezone.utc),
            update_timestamp=datetime.now(timezone.utc),
        ),
        EmailTableSchema(
            email_id=uuid4(),
            primary_email="bing@example.com",
            create_timestamp=datetime.now(timezone.utc),
            update_timestamp=datetime.now(timezone.utc),
        ),
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
        )
    ]
    amos = [
        AddOnsTableSchema(
            email_id=emails[0].email_id,
            create_timestamp=datetime.now(timezone.utc),
            update_timestamp=datetime.now(timezone.utc),
        )
    ]
    empty_ios.emails = emails
    empty_ios.amo = amos
    ingester = Ingester(empty_ios, connection, batch_size=batch_size)
    ingester.run()
    _check_saved(dbsession, emails, amos)


@pytest.mark.parametrize("batch_size", [10, 1, 2, 100])
def test_ingest_emails_and_newsletters(connection, empty_ios, dbsession, batch_size):
    emails = [
        EmailTableSchema(
            email_id=uuid4(),
            primary_email="foo@example.com",
            create_timestamp=datetime.now(timezone.utc),
            update_timestamp=datetime.now(timezone.utc),
        )
    ]
    newsletters = [
        NewsletterTableSchema(
            email_id=emails[0].email_id,
            name="FOO",
            create_timestamp=datetime.now(timezone.utc),
            update_timestamp=datetime.now(timezone.utc),
        ),
        NewsletterTableSchema(
            email_id=emails[0].email_id,
            name="BAR",
            create_timestamp=datetime.now(timezone.utc),
            update_timestamp=datetime.now(timezone.utc),
        ),
        NewsletterTableSchema(
            email_id=emails[0].email_id,
            name="BAZ",
            create_timestamp=datetime.now(timezone.utc),
            update_timestamp=datetime.now(timezone.utc),
        ),
    ]
    empty_ios.emails = emails
    empty_ios.newsletters = newsletters
    ingester = Ingester(empty_ios, connection, batch_size=batch_size)
    ingester.run()
    _check_saved(dbsession, emails, newsletters=newsletters)
