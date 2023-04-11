import os
from uuid import uuid4

import pytest
from alembic import command as alembic_command
from alembic import config as alembic_config
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from ctms.crud import (
    create_contact,
    create_or_update_contact,
    get_email,
    get_waitlists_by_email_id,
    update_contact,
)
from ctms.schemas import ContactPatchSchema, NewsletterInSchema, WaitlistInSchema
from tests.unit.conftest import APP_FOLDER


@pytest.fixture
def minimal_contact_with_relay(dbsession, minimal_contact_data):
    email_id = minimal_contact_data.email.email_id
    contact = minimal_contact_data.copy(
        update={
            "waitlists": [WaitlistInSchema(name="relay", fields={"geo": "es"})],
        }
    )
    create_contact(dbsession, email_id, contact, metrics={})
    dbsession.commit()
    return contact


@pytest.fixture
def minimal_contact_with_relay_phone(dbsession, minimal_contact_data):
    email_id = minimal_contact_data.email.email_id
    contact = minimal_contact_data.copy(
        update={
            "waitlists": [
                WaitlistInSchema(name="relay-vpn", fields={"geo": "es"}),
                WaitlistInSchema(name="relay-phone-masking", fields={"geo": "es"}),
            ],
        }
    )
    create_contact(dbsession, email_id, contact, metrics={})
    dbsession.commit()
    return contact


def test_relay_waitlist_created_on_newsletter_subscribe(
    dbsession, minimal_contact_data
):
    email_id = minimal_contact_data.email.email_id
    contact = minimal_contact_data.copy(
        update={
            "relay_waitlist": {"geo": "fr"},
            "newsletters": [
                NewsletterInSchema(name="amazing-product"),
                NewsletterInSchema(name="relay-phone-masking-waitlist"),
            ],
        }
    )
    create_contact(dbsession, email_id, contact, metrics={})
    dbsession.flush()

    waitlists_by_name = {
        wl.name: wl for wl in get_waitlists_by_email_id(dbsession, email_id)
    }
    assert sorted(waitlists_by_name.keys()) == ["relay-phone-masking"]
    assert waitlists_by_name["relay-phone-masking"].fields["geo"] == "fr"


def test_relay_waitlist_created_on_newsletter_updated(
    dbsession, minimal_contact_data, minimal_contact_with_relay
):
    email_id = minimal_contact_with_relay.email.email_id

    contact = minimal_contact_data.copy(
        update={
            "relay_waitlist": {"geo": "es"},
            "newsletters": [
                NewsletterInSchema(name="relay-phone-masking-waitlist"),
            ],
        }
    )
    create_or_update_contact(dbsession, email_id, contact, metrics={})
    dbsession.flush()

    waitlists_by_name = {
        wl.name: wl for wl in get_waitlists_by_email_id(dbsession, email_id)
    }
    assert sorted(waitlists_by_name.keys()) == ["relay", "relay-phone-masking"]
    assert waitlists_by_name["relay-phone-masking"].fields["geo"] == "es"


def test_relay_waitlist_unsubscribed_on_newsletter_unsubscribed(
    dbsession, minimal_contact_with_relay_phone
):
    email_id = minimal_contact_with_relay_phone.email.email_id
    contact = get_email(dbsession, email_id)
    patch_data = ContactPatchSchema(
        newsletters=[
            NewsletterInSchema(name="relay-phone-masking-waitlist", subscribed=False),
        ]
    )
    update_contact(dbsession, contact, patch_data.dict(exclude_unset=True), metrics={})
    dbsession.flush()

    waitlists = get_waitlists_by_email_id(dbsession, email_id)
    assert sorted(wl.name for wl in waitlists) == ["relay-vpn"]


def test_relay_waitlist_unsubscribed_on_all_newsletters_unsubscribed(
    dbsession, minimal_contact_with_relay_phone
):
    email_id = minimal_contact_with_relay_phone.email.email_id
    contact = get_email(dbsession, email_id)
    patch_data = ContactPatchSchema(newsletters="UNSUBSCRIBE")
    update_contact(dbsession, contact, patch_data.dict(exclude_unset=True), metrics={})
    dbsession.flush()

    waitlists = get_waitlists_by_email_id(dbsession, email_id)
    assert waitlists == []


def test_alembic_migration_waitlists(engine):
    # Rollback to a revision before the waitlists were implemented as relationships.
    # As a side effect, this will test the rollback steps of the migrations files.
    cfg = alembic_config.Config(os.path.join(APP_FOLDER, "alembic.ini"))
    # pylint: disable-next=unsupported-assignment-operation
    cfg.attributes["connection"] = engine
    alembic_command.downgrade(cfg, "9c37ea9b5bba")

    # At this point we have the `waitlist` table, but the `vpn_waitlist`
    # and `relay_waitlist` haven't been migrated.

    # Create 3 contacts:
    # - subscribed to the vpn waitlist
    # - subscribed to the relay waitlist
    # - subscribed to the relay-vpn-waitlist newsletter

    email_id_vpn, email_id_relay, email_id_newsletter = uuid4(), uuid4(), uuid4()
    with engine.connect() as connection:
        with connection.begin():
            for email_id in email_id_vpn, email_id_relay, email_id_newsletter:
                create_statement = """
                INSERT INTO emails (email_id, primary_email, basket_token, sfdc_id, first_name, last_name, mailing_country, email_format, email_lang, double_opt_in, has_opted_out_of_email, unsubscribe_reason, create_timestamp, update_timestamp)
                VALUES (:email_id, :email, :token, '00VA000001aABcDEFG', NULL, NULL, 'us', 'H', 'en', False, False, NULL, NOW(), NOW())
                """
                connection.execute(
                    text(create_statement),
                    {
                        "email_id": str(email_id),
                        "email": f"{email_id}@example.org",
                        "token": str(uuid4()),
                    },
                )

            subscribe_vpn = """
            INSERT INTO vpn_waitlist(email_id, geo, platform, create_timestamp, update_timestamp)
            VALUES (:email_id, 'fr', 'linux', NOW(), NOW())
            """
            connection.execute(text(subscribe_vpn), {"email_id": email_id_vpn})

            subscribe_relay = """
            INSERT INTO relay_waitlist(email_id, geo, create_timestamp, update_timestamp)
            VALUES (:email_id, 'it', NOW(), NOW())
            """
            connection.execute(text(subscribe_relay), {"email_id": email_id_relay})

            subscribe_newsletter = """
            INSERT INTO newsletters(email_id, name, subscribed, format, lang, source, unsub_reason, update_timestamp)
            VALUES (:email_id, 'relay-vpn-waitlist', true, 'H', 'en', NULL, NULL, NOW());
            """
            connection.execute(
                text(subscribe_newsletter), {"email_id": email_id_newsletter}
            )
            subscribe_relay = """
            INSERT INTO relay_waitlist(email_id, geo, create_timestamp, update_timestamp)
            VALUES (:email_id, 'es', NOW(), NOW())
            """
            connection.execute(text(subscribe_relay), {"email_id": email_id_newsletter})

    # Now migrate.
    # pylint: disable-next=unsupported-assignment-operation
    cfg.attributes["connection"] = engine
    alembic_command.upgrade(cfg, "head")

    # Now use the ORM to inspect that the migration went as expected.
    with engine.connect() as connection:
        test_sessionmaker = sessionmaker(
            autocommit=False, autoflush=False, bind=connection
        )
        db = test_sessionmaker()

        contact_vpn = get_email(db, email_id_vpn)
        contact_relay = get_email(db, email_id_relay)
        contact_newsletter = get_email(db, email_id_newsletter)

    assert len(contact_vpn.waitlists) == 1
    assert contact_vpn.waitlists[0].name == "vpn"
    assert contact_vpn.waitlists[0].fields["geo"] == "fr"
    assert contact_vpn.waitlists[0].fields["platform"] == "linux"

    assert len(contact_relay.waitlists) == 1
    assert contact_relay.waitlists[0].name == "relay"
    assert contact_relay.waitlists[0].fields["geo"] == "it"

    assert len(contact_newsletter.waitlists) == 1
    assert contact_newsletter.waitlists[0].name == "relay-vpn"
    assert contact_newsletter.waitlists[0].fields["geo"] == "es"
