"""Unit tests for cross-API functionality"""

from typing import Optional, Set
from uuid import uuid4

import pytest

from ctms.schemas import ContactInSchema, ContactSchema, NewsletterInSchema
from ctms.schemas.waitlist import WaitlistInSchema

API_TEST_CASES = (
    ("GET", "/ctms", {"primary_email": "contact@example.com"}),
    ("GET", "/ctms/332de237-cab7-4461-bcc3-48e68f42bd5c", None),
    (
        "POST",
        "/ctms",
        {
            "email": {
                "email_id": str(uuid4()),
                "primary_email": "new@example.com",
            }
        },
    ),
    (
        "PUT",
        "/ctms/332de237-cab7-4461-bcc3-48e68f42bd5c",
        {
            "email": {
                "email_id": "332de237-cab7-4461-bcc3-48e68f42bd5c",
                "primary_email": "put-new@example.com",
            }
        },
    ),
    (
        "PATCH",
        "/ctms/332de237-cab7-4461-bcc3-48e68f42bd5c",
        {
            "email": {
                "email_format": "T",
            }
        },
    ),
    (
        "DELETE",
        "/ctms/contact@example.com",
        None,
    ),
)


@pytest.mark.parametrize("method,path,params", API_TEST_CASES)
def test_unauthorized_api_call_fails(anon_client, method, path, params):
    """Calling the API without credentials fails."""
    if method in ("GET", "DELETE"):
        resp = anon_client.request(method, path)
    else:
        assert method in ("PATCH", "POST", "PUT")
        resp = anon_client.request(method, path, json=params)
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Not authenticated"}


@pytest.mark.parametrize("method,path,params", API_TEST_CASES)
def test_authorized_api_call_succeeds(client, email_factory, method, path, params):
    """Calling the API with credentials succeeds."""

    email_factory(
        email_id="332de237-cab7-4461-bcc3-48e68f42bd5c",
        primary_email="contact@example.com",
    )

    if method == "GET":
        resp = client.request(method, path, params=params)
        assert resp.status_code == 200
    elif method == "DELETE":
        resp = client.request(method, path)
        assert resp.status_code == 200
    else:
        assert method in ("PATCH", "POST", "PUT")
        resp = client.request(method, path, json=params)
        if method == "PUT":
            assert resp.status_code in {200, 201}  # Either creates or updates
        elif method == "POST":
            assert resp.status_code == 201
        else:  # PATCH
            assert resp.status_code == 200


def _subscribe_newsletter(contact):
    contact.newsletters.append(NewsletterInSchema(name="new-newsletter"))


def _unsubscribe_newsletter(contact):
    contact.newsletters = contact.newsletters[0:-1]


def _subscribe_newsletters_and_change(contact):
    if contact.newsletters:
        contact.newsletters[-1].subscribed = not contact.newsletters[-1].subscribed
    contact.newsletters.append(
        NewsletterInSchema(name="a-newsletter", subscribed=False)
    )
    contact.newsletters.append(
        NewsletterInSchema(name="another-newsletter", subscribed=True)
    )


def _subscribe_waitlists_and_change(contact):
    if contact.waitlists:
        contact.waitlists[-1].subscribed = not contact.waitlists[-1].subscribed
    contact.waitlists.append(WaitlistInSchema(name="a-waitlist", subscribed=False))
    contact.waitlists.append(WaitlistInSchema(name="another-waitlist", subscribed=True))


def _un_amo(contact):
    if contact.amo:
        del contact.amo


def _change_email(contact):
    contact.email.primary_email = "something-new@example.com"


_test_get_put_modifiers = [
    _subscribe_newsletter,
    _unsubscribe_newsletter,
    _un_amo,
    _change_email,
    _subscribe_newsletters_and_change,
    _subscribe_waitlists_and_change,
]


@pytest.fixture(params=_test_get_put_modifiers)
def update_fetched(request):
    return request.param


def _compare_written_contacts(
    contact,
    sample,
    email_id,
    ids_should_be_identical: bool = True,
    new_default_fields: Optional[set] = None,
):
    fields_not_written = new_default_fields or set()

    saved_contact = ContactInSchema(**contact.model_dump())
    sample = ContactInSchema(**sample.model_dump())

    if not ids_should_be_identical:
        assert saved_contact.email.email_id != sample.email.email_id
        del saved_contact.email.email_id
        del sample.email.email_id

    for f in fields_not_written:
        setattr(sample, f, [] if f in ("newsletters", "waitlists") else None)

    assert saved_contact.idempotent_equal(sample)


def find_default_fields(contact: ContactSchema) -> Set[str]:
    """Return names of fields that contain default values only"""
    default_fields = set()
    if hasattr(contact, "amo") and contact.amo and contact.amo.is_default():
        default_fields.add("amo")
    if hasattr(contact, "fxa") and contact.fxa and contact.fxa.is_default():
        default_fields.add("fxa")
    if hasattr(contact, "mofo") and contact.mofo and contact.mofo.is_default():
        default_fields.add("mofo")
    if all(n.is_default() for n in contact.newsletters):
        default_fields.add("newsletters")
    if all(n.is_default() for n in contact.waitlists):
        default_fields.add("waitlists")
    return default_fields


SAMPLE_CONTACT_PARAMS = [
    ("minimal_contact_data", set()),
    ("maximal_contact_data", set()),
    ("example_contact_data", set()),
    ("to_add_contact_data", set()),
    ("simple_default_contact_data", {"amo"}),
    ("default_newsletter_contact_data", {"newsletters"}),
    ("default_waitlist_contact_data", {"waitlists"}),
]


@pytest.mark.parametrize("post_contact", SAMPLE_CONTACT_PARAMS, indirect=True)
def test_post_get_put(client, post_contact, put_contact, update_fetched):
    """This encompasses the entire expected flow for basket"""
    saved_contacts, sample, email_id = post_contact()
    _compare_written_contacts(saved_contacts[0], sample, email_id)

    resp = client.get(f"/ctms/{email_id}")
    assert resp.status_code == 200

    # TODO: remove this once we remove support of `vpn_waitlist` and
    # `relay_waitlist` as input.
    # If we don't strip these two fields before turning the data into
    # a `ContactInSchema`, they will create waitlist objects.
    without_alias_fields = {
        k: v
        for k, v in resp.json().items()
        if k not in ("vpn_waitlist", "relay_waitlist")
    }
    fetched = ContactInSchema(**without_alias_fields)
    update_fetched(fetched)
    new_default_fields = find_default_fields(fetched)
    # We set new_default_fields here because the returned response above
    # _includes_ defaults for many fields and we want to not write
    # them when the record is PUT again
    saved_contacts, sample, email_id = put_contact(
        record=fetched, new_default_fields=new_default_fields
    )
    _compare_written_contacts(
        saved_contacts[0], sample, email_id, new_default_fields=new_default_fields
    )
