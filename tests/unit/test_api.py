"""Unit tests for cross-API functionality"""
from typing import Any, Optional, Tuple
from uuid import uuid4

import pytest

from ctms.schemas import ContactInSchema, ContactSchema, NewsletterInSchema
from tests.unit.sample_data import SAMPLE_CONTACTS

API_TEST_CASES: Tuple[Tuple[str, str, Any], ...] = (
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
)


@pytest.mark.parametrize("method,path,params", API_TEST_CASES)
def test_unauthorized_api_call_fails(
    anon_client, example_contact, method, path, params
):
    """Calling the API without credentials fails."""
    if method == "GET":
        resp = anon_client.get(path, params=params)
    else:
        assert method in ("PATCH", "POST", "PUT")
        resp = anon_client.request(method, path, json=params)
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Not authenticated"}


@pytest.mark.parametrize("method,path,params", API_TEST_CASES)
def test_authorized_api_call_succeeds(client, example_contact, method, path, params):
    """Calling the API without credentials fails."""
    if method == "GET":
        resp = client.get(path, params=params)
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


def _subscribe(contact):
    contact.newsletters.append(NewsletterInSchema(name="new-newsletter"))


def _unsubscribe(contact):
    contact.newsletters = contact.newsletters[0:-1]


def _subscribe_and_change(contact):
    if contact.newsletters:
        contact.newsletters[-1].subscribed = not contact.newsletters[-1].subscribed
    contact.newsletters.append(
        NewsletterInSchema(name="a-newsletter", subscribed=False)
    )
    contact.newsletters.append(
        NewsletterInSchema(name="another-newsletter", subscribed=True)
    )


def _un_amo(contact):
    if contact.amo:
        del contact.amo


def _change_email(contact):
    contact.email.primary_email = "something-new@example.com"


_test_get_put_modifiers = [
    _subscribe,
    _unsubscribe,
    _un_amo,
    _change_email,
    _subscribe_and_change,
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
    fields_not_written = new_default_fields or SAMPLE_CONTACTS.get_not_written(email_id)

    saved_contact = ContactInSchema(**contact.dict())
    sample = ContactInSchema(**sample.dict())

    if not ids_should_be_identical:
        assert saved_contact.email.email_id != sample.email.email_id
        del saved_contact.email.email_id
        del sample.email.email_id

    for f in fields_not_written:
        setattr(sample, f, [] if f == "newsletters" else None)

    assert saved_contact.idempotent_equal(sample)


@pytest.mark.parametrize("post_contact", SAMPLE_CONTACTS.keys(), indirect=True)
def test_post_get_put(client, post_contact, put_contact, update_fetched):
    """This encompasses the entire expected flow for basket"""
    saved_contacts, sample, email_id = post_contact()
    _compare_written_contacts(saved_contacts[0], sample, email_id)

    resp = client.get(f"/ctms/{email_id}")
    assert resp.status_code == 200

    fetched = ContactSchema(**resp.json())
    update_fetched(fetched)
    new_default_fields = fetched.find_default_fields()
    # We set new_default_fields here because the returned response above
    # _includes_ defaults for many fields and we want to not write
    # them when the record is PUT again
    saved_contacts, sample, email_id = put_contact(
        record=fetched, new_default_fields=new_default_fields
    )
    _compare_written_contacts(
        saved_contacts[0], sample, email_id, new_default_fields=new_default_fields
    )
