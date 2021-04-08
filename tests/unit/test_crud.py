"""Test database operations"""

from uuid import uuid4

import pytest
import sqlalchemy.event

from ctms.crud import (
    create_amo,
    create_email,
    create_fxa,
    create_mofo,
    create_newsletter,
    get_contact_by_email_id,
    get_contacts_by_any_id,
    get_email,
    get_emails_by_any_id,
)
from ctms.schemas import (
    AddOnsInSchema,
    EmailInSchema,
    FirefoxAccountsInSchema,
    MozillaFoundationInSchema,
    NewsletterInSchema,
)


class StatementWatcher:
    """
    Capture SQL statements emitted by code.

    Based on https://stackoverflow.com/a/33691585/10612

    Use as a context manager to count the number of execute()'s performed
    against the given session / connection.

    Usage:
        with StatementWatcher(dbsession.connection()) as sw:
            dbsession.query(Email).all()
        assert sw.count == 1
    """

    def __init__(self, connection):
        self.connection = connection
        self.statements = []

    def __enter__(self):
        sqlalchemy.event.listen(self.connection, "before_cursor_execute", self.callback)
        return self

    def __exit__(self, *args):
        sqlalchemy.event.remove(self.connection, "before_cursor_execute", self.callback)

    def callback(self, conn, cursor, statement, parameters, context, execute_many):
        self.statements.append((statement, parameters, execute_many))

    @property
    def count(self):
        return len(self.statements)


def test_get_email(dbsession, example_contact):
    """An email is retrived in two queries, and newsletters are sorted by name."""
    email_id = example_contact.email.email_id
    with StatementWatcher(dbsession.connection()) as watcher:
        email = get_email(dbsession, email_id)
    assert watcher.count == 2
    assert email.email_id == email_id
    newsletter_names = [newsletter.name for newsletter in email.newsletters]
    assert newsletter_names == ["firefox-welcome", "mozilla-welcome"]
    assert sorted(newsletter_names) == newsletter_names


def test_get_email_miss(dbsession):
    """A missed email is one query."""
    with StatementWatcher(dbsession.connection()) as watcher:
        email = get_email(dbsession, str(uuid4()))
    assert watcher.count == 1
    assert email is None


@pytest.mark.parametrize(
    "alt_id_name,alt_id_value",
    [
        ("email_id", "67e52c77-950f-4f28-accb-bb3ea1a2c51a"),
        ("primary_email", "mozilla-fan@example.com"),
        ("amo_user_id", "123"),
        ("basket_token", "d9ba6182-f5dd-4728-a477-2cc11bf62b69"),
        ("fxa_id", "611b6788-2bba-42a6-98c9-9ce6eb9cbd34"),
        ("fxa_primary_email", "fxa-firefox-fan@example.com"),
        ("sfdc_id", "001A000001aMozFan"),
        ("mofo_contact_id", "5e499cc0-eeb5-4f0e-aae6-a101721874b8"),
        ("mofo_email_id", "195207d2-63f2-4c9f-b149-80e9c408477a"),
    ],
)
def test_get_emails_by_any_id(dbsession, sample_contacts, alt_id_name, alt_id_value):
    """An email is fetched by alternate id in two queries."""
    with StatementWatcher(dbsession.connection()) as watcher:
        emails = get_emails_by_any_id(dbsession, **{alt_id_name: alt_id_value})
    assert watcher.count == 2
    assert len(emails) == 1
    newsletter_names = [newsletter.name for newsletter in emails[0].newsletters]
    assert sorted(newsletter_names) == newsletter_names


def test_get_emails_by_any_id_missing(dbsession, sample_contacts):
    """One query is needed to find no emails."""
    with StatementWatcher(dbsession.connection()) as watcher:
        emails = get_emails_by_any_id(dbsession, basket_token=str(uuid4()))
    assert watcher.count == 1
    assert len(emails) == 0


@pytest.mark.parametrize(
    "alt_id_name,alt_id_value",
    [
        ("amo_user_id", "123"),
        ("fxa_primary_email", "fxa-firefox-fan@example.com"),
        ("sfdc_id", "001A000001aMozFan"),
        ("mofo_contact_id", "5e499cc0-eeb5-4f0e-aae6-a101721874b8"),
    ],
)
def test_get_multiple_emails_by_any_id(
    dbsession, sample_contacts, alt_id_name, alt_id_value
):
    """Two emails are retrieved in two queries."""

    dupe_id = str(uuid4())
    create_email(
        dbsession,
        EmailInSchema(
            email_id=dupe_id,
            primary_email="dupe@example.com",
            basket_token=str(uuid4()),
            sfdc_id=alt_id_value
            if alt_id_name == "sfdc_id"
            else "other_sdfc_alt_id_value",
        ),
    )
    if alt_id_name == "amo_user_id":
        create_amo(dbsession, dupe_id, AddOnsInSchema(user_id=alt_id_value))
    if alt_id_name == "fxa_primary_email":
        create_fxa(
            dbsession, dupe_id, FirefoxAccountsInSchema(primary_email=alt_id_value)
        )
    if alt_id_name == "mofo_contact_id":
        create_mofo(
            dbsession,
            dupe_id,
            MozillaFoundationInSchema(
                mofo_email_id=str(uuid4()), mofo_contact_id=alt_id_value
            ),
        )

    create_newsletter(dbsession, dupe_id, NewsletterInSchema(name="zzz_sleepy_news"))
    create_newsletter(dbsession, dupe_id, NewsletterInSchema(name="aaa_game_news"))
    dbsession.flush()

    with StatementWatcher(dbsession.connection()) as watcher:
        emails = get_emails_by_any_id(dbsession, **{alt_id_name: alt_id_value})
    assert watcher.count == 2
    assert len(emails) == 2
    for email in emails:
        newsletter_names = [newsletter.name for newsletter in email.newsletters]
        assert sorted(newsletter_names) == newsletter_names


def test_get_contact_by_email_id_found(dbsession, example_contact):
    """A contact is retrived in two queries, and newsletters are sorted by name."""
    email_id = example_contact.email.email_id
    with StatementWatcher(dbsession.connection()) as sw:
        contact = get_contact_by_email_id(dbsession, email_id)
    assert sw.count == 2
    assert contact["email"].email_id == email_id
    newsletter_names = [nl.name for nl in contact["newsletters"]]
    assert newsletter_names == ["firefox-welcome", "mozilla-welcome"]
    assert sorted(newsletter_names) == newsletter_names


def test_get_contact_by_email_id_miss(dbsession):
    """A missed contact is 1 query."""
    with StatementWatcher(dbsession.connection()) as sw:
        contact = get_contact_by_email_id(dbsession, str(uuid4()))
    assert sw.count == 1
    assert contact is None


@pytest.mark.parametrize(
    "alt_id_name,alt_id_value",
    [
        ("email_id", "67e52c77-950f-4f28-accb-bb3ea1a2c51a"),
        ("primary_email", "mozilla-fan@example.com"),
        ("amo_user_id", "123"),
        ("basket_token", "d9ba6182-f5dd-4728-a477-2cc11bf62b69"),
        ("fxa_id", "611b6788-2bba-42a6-98c9-9ce6eb9cbd34"),
        ("fxa_primary_email", "fxa-firefox-fan@example.com"),
        ("sfdc_id", "001A000001aMozFan"),
        ("mofo_contact_id", "5e499cc0-eeb5-4f0e-aae6-a101721874b8"),
        ("mofo_email_id", "195207d2-63f2-4c9f-b149-80e9c408477a"),
    ],
)
def test_get_contact_by_any_id(dbsession, sample_contacts, alt_id_name, alt_id_value):
    """A contacts is fetched by alternate id in two queries."""
    with StatementWatcher(dbsession.connection()) as sw:
        contacts = get_contacts_by_any_id(dbsession, **{alt_id_name: alt_id_value})
    assert sw.count == 2
    assert len(contacts) == 1
    newsletter_names = [nl.name for nl in contacts[0]["newsletters"]]
    assert sorted(newsletter_names) == newsletter_names


def test_get_contact_by_any_id_missing(dbsession, sample_contacts):
    """A contacts is fetched by alternate id in two queries."""
    with StatementWatcher(dbsession.connection()) as sw:
        contact = get_contacts_by_any_id(dbsession, basket_token=str(uuid4()))
    assert sw.count == 1
    assert len(contact) == 0


@pytest.mark.parametrize(
    "alt_id_name,alt_id_value",
    [
        ("amo_user_id", "123"),
        ("fxa_primary_email", "fxa-firefox-fan@example.com"),
        ("sfdc_id", "001A000001aMozFan"),
        ("mofo_contact_id", "5e499cc0-eeb5-4f0e-aae6-a101721874b8"),
    ],
)
def test_get_multiple_contacts_by_any_id(
    dbsession, sample_contacts, alt_id_name, alt_id_value
):
    """2 contacts are retrieved in 2 queries."""

    dupe_id = str(uuid4())
    create_email(
        dbsession,
        EmailInSchema(
            email_id=dupe_id,
            primary_email="dupe@example.com",
            basket_token=str(uuid4()),
            sfdc_id=alt_id_value
            if alt_id_name == "sfdc_id"
            else "other_sdfc_alt_id_value",
        ),
    )
    if alt_id_name == "amo_user_id":
        create_amo(dbsession, dupe_id, AddOnsInSchema(user_id=alt_id_value))
    if alt_id_name == "fxa_primary_email":
        create_fxa(
            dbsession, dupe_id, FirefoxAccountsInSchema(primary_email=alt_id_value)
        )
    if alt_id_name == "mofo_contact_id":
        create_mofo(
            dbsession,
            dupe_id,
            MozillaFoundationInSchema(
                mofo_email_id=str(uuid4()), mofo_contact_id=alt_id_value
            ),
        )

    create_newsletter(dbsession, dupe_id, NewsletterInSchema(name="zzz_sleepy_news"))
    create_newsletter(dbsession, dupe_id, NewsletterInSchema(name="aaa_game_news"))
    dbsession.flush()

    with StatementWatcher(dbsession.connection()) as sw:
        contacts = get_contacts_by_any_id(dbsession, **{alt_id_name: alt_id_value})
    assert sw.count == 2
    assert len(contacts) == 2
    for contact in contacts:
        newsletter_names = [nl.name for nl in contacts[0]["newsletters"]]
        assert sorted(newsletter_names) == newsletter_names
