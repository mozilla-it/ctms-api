from ctms.crud import (
    create_contact,
    create_or_update_contact,
    get_email,
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
from ctms.schemas.email import EMAIL_ID_EXAMPLE


def test_relay_waitlist_created_on_newsletter_subscribe(dbsession):
    contact = ContactInSchema(
        email={
            "email_id": EMAIL_ID_EXAMPLE,
            "primary_email": "hello@example.com",
        },
        relay_waitlist={"geo": "fr"},
        newsletters=[
            {"email_id": EMAIL_ID_EXAMPLE, "name": "amazing-product"},
            {"email_id": EMAIL_ID_EXAMPLE, "name": "relay-phone-masking-waitlist"},
        ],
    )
    create_contact(dbsession, EMAIL_ID_EXAMPLE, contact, get_metrics())
    dbsession.flush()

    waitlists_by_name = {
        wl.name: wl for wl in get_waitlists_by_email_id(dbsession, EMAIL_ID_EXAMPLE)
    }
    assert sorted(waitlists_by_name.keys()) == ["relay-phone-masking"]
    assert waitlists_by_name["relay-phone-masking"].fields["geo"] == "fr"


def test_relay_waitlist_created_on_newsletter_updated(
    dbsession, email_factory, waitlist_factory
):
    email = email_factory(email_id=EMAIL_ID_EXAMPLE, newsletters=1)
    waitlist_factory(name="relay", fields={"geo": "es"}, email=email)
    dbsession.commit()

    contact = ContactPutSchema(
        email={
            "email_id": EMAIL_ID_EXAMPLE,
            "primary_email": email.primary_email,
        },
        relay_waitlist={"geo": "es"},
        newsletters=[{"name": "relay-phone-masking-waitlist"}],
    )
    create_or_update_contact(dbsession, EMAIL_ID_EXAMPLE, contact, metrics={})
    dbsession.flush()

    waitlists_by_name = {
        wl.name: wl for wl in get_waitlists_by_email_id(dbsession, EMAIL_ID_EXAMPLE)
    }
    assert sorted(waitlists_by_name.keys()) == ["relay", "relay-phone-masking"]
    assert waitlists_by_name["relay-phone-masking"].fields["geo"] == "es"


def test_relay_waitlist_unsubscribed_on_newsletter_unsubscribed(
    dbsession, email_factory, waitlist_factory
):
    email = email_factory(email_id=EMAIL_ID_EXAMPLE, newsletters=1)
    waitlist_factory(name="relay-vpn", fields={"geo": "es"}, email=email)
    waitlist_factory(name="relay-phone-masking", fields={"geo": "es"}, email=email)
    dbsession.flush()

    contact = get_email(dbsession, EMAIL_ID_EXAMPLE)

    patch_data = ContactPatchSchema(
        newsletters=[
            NewsletterInSchema(name="relay-phone-masking-waitlist", subscribed=False),
        ]
    )
    update_contact(dbsession, contact, patch_data.dict(exclude_unset=True), metrics={})
    dbsession.flush()

    waitlists = get_waitlists_by_email_id(dbsession, EMAIL_ID_EXAMPLE)
    assert sorted(wl.name for wl in waitlists if wl.subscribed) == ["relay-vpn"]


def test_relay_waitlist_unsubscribed_on_all_newsletters_unsubscribed(
    dbsession, email_factory, waitlist_factory
):
    email = email_factory(email_id=EMAIL_ID_EXAMPLE, newsletters=1)
    waitlist_factory(name="relay-vpn", fields={"geo": "es"}, email=email)
    waitlist_factory(name="relay-phone-masking", fields={"geo": "es"}, email=email)
    dbsession.flush()

    contact = get_email(dbsession, EMAIL_ID_EXAMPLE)

    patch_data = ContactPatchSchema(newsletters="UNSUBSCRIBE")
    update_contact(dbsession, contact, patch_data.dict(exclude_unset=True), metrics={})
    dbsession.flush()

    waitlists = get_waitlists_by_email_id(dbsession, EMAIL_ID_EXAMPLE)
    assert not any(wl.subscribed for wl in waitlists)
