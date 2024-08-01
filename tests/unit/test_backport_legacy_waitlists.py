from uuid import uuid4

from ctms.crud import (
    create_contact,
    create_or_update_contact,
    get_waitlists_by_email_id,
    update_contact,
)
from ctms.metrics import get_metrics
from ctms.schemas import (
    ContactInSchema,
    ContactPatchSchema,
    ContactPutSchema,
    NewsletterInSchema,
)


def test_relay_waitlist_created_on_newsletter_subscribe(dbsession):
    email_id = str(uuid4())
    contact = ContactInSchema(
        email={
            "email_id": email_id,
            "primary_email": "hello@example.com",
        },
        relay_waitlist={"geo": "fr"},
        newsletters=[
            {"email_id": email_id, "name": "amazing-product"},
            {"email_id": email_id, "name": "relay-phone-masking-waitlist"},
        ],
    )
    create_contact(dbsession, email_id, contact, get_metrics())
    dbsession.flush()

    waitlists_by_name = {
        wl.name: wl for wl in get_waitlists_by_email_id(dbsession, email_id)
    }
    assert sorted(waitlists_by_name.keys()) == ["relay-phone-masking"]
    assert waitlists_by_name["relay-phone-masking"].fields["geo"] == "fr"


def test_relay_waitlist_created_on_newsletter_updated(
    dbsession, email_factory, waitlist_factory
):
    email = email_factory()
    waitlist_factory(name="relay", fields={"geo": "fr"}, email=email)

    contact = ContactPutSchema(
        email={"email_id": email.email_id, "primary_email": email.primary_email},
        relay_waitlist={"geo": "es"},
        newsletters=[{"name": "relay-phone-masking-waitlist"}],
    )

    create_or_update_contact(dbsession, email.email_id, contact, metrics={})
    dbsession.flush()

    waitlists_by_name = {
        wl.name: wl for wl in get_waitlists_by_email_id(dbsession, email.email_id)
    }
    assert sorted(waitlists_by_name.keys()) == ["relay", "relay-phone-masking"]
    assert waitlists_by_name["relay-phone-masking"].fields["geo"] == "es"


def test_relay_waitlist_unsubscribed_on_newsletter_unsubscribed(
    dbsession, email_factory, waitlist_factory
):
    email = email_factory()
    waitlist_factory(name="relay-vpn", fields={"geo": "es"}, email=email)
    waitlist_factory(name="relay-phone-masking", fields={"geo": "es"}, email=email)

    patch_data = ContactPatchSchema(
        newsletters=[
            NewsletterInSchema(name="relay-phone-masking-waitlist", subscribed=False),
        ]
    )
    update_contact(
        dbsession,
        email,
        patch_data.model_dump(exclude_unset=True),
        metrics={},
    )
    dbsession.flush()

    waitlists = get_waitlists_by_email_id(dbsession, email.email_id)
    assert sorted(wl.name for wl in waitlists if wl.subscribed) == ["relay-vpn"]


def test_relay_waitlist_unsubscribed_on_all_newsletters_unsubscribed(
    dbsession, email_factory, waitlist_factory
):
    email = email_factory()
    waitlist_factory(name="relay-phone-masking", fields={"geo": "es"}, email=email)

    patch_data = ContactPatchSchema(newsletters="UNSUBSCRIBE")
    update_contact(
        dbsession, email, patch_data.model_dump(exclude_unset=True), metrics={}
    )
    dbsession.flush()

    waitlists = get_waitlists_by_email_id(dbsession, email.email_id)
    assert not any(wl.subscribed for wl in waitlists)
