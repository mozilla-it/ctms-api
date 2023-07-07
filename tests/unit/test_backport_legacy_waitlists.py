import pytest

from ctms.crud import (
    create_or_update_contact,
    get_email,
    get_waitlists_by_email_id,
    update_contact,
)
from ctms.schemas import ContactPatchSchema, NewsletterInSchema
from ctms.schemas.contact import ContactSchema
from ctms.schemas.newsletter import NewsletterTableSchema
from ctms.schemas.waitlist import WaitlistTableSchema
from tests.unit.conftest import create_full_contact


@pytest.fixture
def minimal_contact_with_relay(dbsession, minimal_contact_data: ContactSchema):
    email_id = minimal_contact_data.email.email_id
    contact = minimal_contact_data.copy(
        update={
            "waitlists": [
                WaitlistTableSchema(
                    email_id=email_id,
                    name="relay",
                    fields={"geo": "es"},
                    create_timestamp="2014-01-22T15:24:00.000+0000",
                    update_timestamp="2020-01-22T15:24:00.000+0000",
                )
            ],
        }
    )
    create_full_contact(dbsession, contact)
    dbsession.commit()
    return contact


@pytest.fixture
def minimal_contact_with_relay_phone(dbsession, minimal_contact_data):
    email_id = minimal_contact_data.email.email_id
    contact = minimal_contact_data.copy(
        update={
            "waitlists": [
                WaitlistTableSchema(
                    email_id=email_id,
                    name="relay-vpn",
                    fields={"geo": "es"},
                    create_timestamp="2014-01-22T15:24:00.000+0000",
                    update_timestamp="2020-01-22T15:24:00.000+0000",
                ),
                WaitlistTableSchema(
                    email_id=email_id,
                    name="relay-phone-masking",
                    fields={"geo": "es"},
                    create_timestamp="2014-01-22T15:24:00.000+0000",
                    update_timestamp="2020-01-22T15:24:00.000+0000",
                ),
            ],
        }
    )
    create_full_contact(dbsession, contact)
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
                NewsletterTableSchema(
                    email_id=email_id,
                    name="amazing-product",
                    create_timestamp="2014-01-22T15:24:00.000+0000",
                    update_timestamp="2020-01-22T15:24:00.000+0000",
                ),
                NewsletterTableSchema(
                    email_id=email_id,
                    name="relay-phone-masking-waitlist",
                    create_timestamp="2014-01-22T15:24:00.000+0000",
                    update_timestamp="2020-01-22T15:24:00.000+0000",
                ),
            ],
        }
    )
    create_full_contact(dbsession, contact)
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
                NewsletterTableSchema(
                    email_id=email_id,
                    name="relay-phone-masking-waitlist",
                    create_timestamp="2014-01-22T15:24:00.000+0000",
                    update_timestamp="2020-01-22T15:24:00.000+0000",
                ),
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
    assert sorted(wl.name for wl in waitlists if wl.subscribed) == ["relay-vpn"]


def test_relay_waitlist_unsubscribed_on_all_newsletters_unsubscribed(
    dbsession, minimal_contact_with_relay_phone
):
    email_id = minimal_contact_with_relay_phone.email.email_id
    contact = get_email(dbsession, email_id)
    patch_data = ContactPatchSchema(newsletters="UNSUBSCRIBE")
    update_contact(dbsession, contact, patch_data.dict(exclude_unset=True), metrics={})
    dbsession.flush()

    waitlists = get_waitlists_by_email_id(dbsession, email_id)
    assert not any(wl.subscribed for wl in waitlists)
