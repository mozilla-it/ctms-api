import pytest

from ctms.crud import (
    create_contact,
    create_or_update_contact,
    get_email,
    get_waitlists_by_email_id,
    update_contact,
)
from ctms.schemas import (
    ContactPatchSchema,
    NewsletterInSchema,
    RelayWaitlistInSchema,
    WaitlistInSchema,
)
from tests.unit.sample_data import SAMPLE_MINIMAL


@pytest.fixture
def minimal_contact_with_relay(dbsession):
    email_id = SAMPLE_MINIMAL.email.email_id
    contact = SAMPLE_MINIMAL.copy(
        update={
            "waitlists": [WaitlistInSchema(name="relay", fields={"geo": "es"})],
        }
    )
    create_contact(dbsession, email_id, contact, metrics={})
    dbsession.commit()
    return contact


@pytest.fixture
def minimal_contact_with_relay_phone(dbsession):
    email_id = SAMPLE_MINIMAL.email.email_id
    contact = SAMPLE_MINIMAL.copy(
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


def test_relay_waitlist_created_on_newsletter_subscribe(dbsession):
    email_id = SAMPLE_MINIMAL.email.email_id
    contact = SAMPLE_MINIMAL.copy(
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
    dbsession, minimal_contact_with_relay
):
    email_id = minimal_contact_with_relay.email.email_id

    contact = SAMPLE_MINIMAL.copy(
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
