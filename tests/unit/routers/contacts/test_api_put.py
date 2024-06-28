"""Unit tests for PUT /ctms/{email_id} (Create or update)"""

import json
from uuid import UUID, uuid4

import pytest
from structlog.testing import capture_logs

from tests.unit.conftest import SAMPLE_CONTACT_PARAMS

from .test_api import _compare_written_contacts

PUT_TEST_PARAMS = pytest.mark.parametrize(
    "put_contact", SAMPLE_CONTACT_PARAMS, indirect=True
)


def test_create_or_update_basic_id_is_different(client, minimal_contact):
    """This should fail since we require an email_id to PUT"""

    # This id is different from the one in the contact
    resp = client.put(
        "/ctms/d16c4ec4-caa0-4bf2-a06f-1bbf07bf03c7", content=minimal_contact.json()
    )
    assert resp.status_code == 422, resp.text


@PUT_TEST_PARAMS
def test_create_or_update_basic_id_is_none(put_contact):
    """This should fail since we require an email_id to PUT"""

    def _remove_id(contact):
        contact.email.email_id = None
        return contact

    put_contact(
        modifier=_remove_id,
        code=422,
        stored_contacts=0,
        check_written=False,
    )


@PUT_TEST_PARAMS
def test_create_or_update_basic_empty_db(put_contact):
    """Most straightforward contact creation succeeds when there is no collision"""
    saved_contacts, sample, email_id = put_contact()
    _compare_written_contacts(saved_contacts[0], sample, email_id)


@PUT_TEST_PARAMS
def test_create_or_update_identical(put_contact):
    """Writing the same thing twice works both times"""
    saved_contacts, sample, email_id = put_contact()
    _compare_written_contacts(saved_contacts[0], sample, email_id)
    saved_contacts, sample, email_id = put_contact()
    _compare_written_contacts(saved_contacts[0], sample, email_id)


@PUT_TEST_PARAMS
def test_create_or_update_change_primary_email(put_contact):
    """We can update a primary_email given a ctms ID"""
    saved_contacts, sample, email_id = put_contact()
    _compare_written_contacts(saved_contacts[0], sample, email_id)

    def _change_email(contact):
        contact.email.primary_email = "something-new@example.com"
        return contact

    saved_contacts, sample, email_id = put_contact(
        modifier=_change_email, query_fields={"email_id": email_id}
    )
    _compare_written_contacts(saved_contacts[0], sample, email_id)


@PUT_TEST_PARAMS
def test_create_or_update_change_basket_token(put_contact):
    """We can update a basket_token given a ctms ID"""
    saved_contacts, sample, email_id = put_contact()
    _compare_written_contacts(saved_contacts[0], sample, email_id)

    def _change_basket(contact):
        contact.email.basket_token = UUID("c97fb13b-3a19-4f4a-ac2d-abf0717b8df1")
        return contact

    saved_contacts, sample, email_id = put_contact(modifier=_change_basket)
    _compare_written_contacts(saved_contacts[0], sample, email_id)


@PUT_TEST_PARAMS
def test_create_or_update_with_basket_collision(put_contact):
    """Updating a contact with diff ids but same email fails.
    We override the basket token so that we know we're not colliding on that here.
    See test_create_basic_with_email_collision below for that check
    """
    saved_contacts, orig_sample, email_id = put_contact()
    _compare_written_contacts(saved_contacts[0], orig_sample, email_id)

    def _change_basket(contact):
        contact.email.email_id = UUID("229cfa16-a8c9-4028-a9bd-fe746dc6bf73")
        contact.email.basket_token = UUID("df9f7086-4949-4b2d-8fcf-49167f8f783d")
        return contact

    saved_contacts, _, _ = put_contact(modifier=_change_basket, code=409)
    _compare_written_contacts(saved_contacts[0], orig_sample, email_id)


@PUT_TEST_PARAMS
def test_create_or_update_with_email_collision(put_contact):
    """Updating a contact with diff ids but same basket token fails.
    We override the email so that we know we're not colliding on that here.
    See other test for that check
    """
    saved_contacts, orig_sample, email_id = put_contact()
    _compare_written_contacts(saved_contacts[0], orig_sample, email_id)

    def _change_primary_email(contact):
        contact.email.email_id = UUID("229cfa16-a8c9-4028-a9bd-fe746dc6bf73")
        contact.email.primary_email = "foo@example.com"
        return contact

    saved_contacts, _, _ = put_contact(modifier=_change_primary_email, code=409)
    _compare_written_contacts(saved_contacts[0], orig_sample, email_id)


def test_put_create_no_trace(client, dbsession):
    """PUT does not trace most new contacts"""
    email_id = str(uuid4())
    data = {
        "email": {"email_id": email_id, "primary_email": "test+no-trace@example.com"}
    }
    with capture_logs() as caplogs:
        resp = client.put(f"/ctms/{email_id}", json=data)
    assert resp.status_code == 201
    assert len(caplogs) == 1
    assert "trace" not in caplogs[0]


def test_put_replace_no_trace(client, minimal_contact):
    """PUT does not trace most replaced contacts"""
    email_id = minimal_contact.email.email_id
    data = json.loads(minimal_contact.json())
    data["email"]["first_name"] = "Jeff"
    with capture_logs() as caplogs:
        resp = client.put(f"/ctms/{email_id}", json=data)
    assert resp.status_code == 201
    assert len(caplogs) == 1
    assert "trace" not in caplogs[0]


def test_put_with_not_json_is_error(client, dbsession):
    """Calling PUT with a text body is a 422 validation error."""
    email_id = str(uuid4())
    data = b"make a contact please"
    with capture_logs() as caplogs:
        resp = client.put(f"/ctms/{email_id}", content=data)
    assert resp.status_code == 422
    assert resp.json()["detail"][0]["msg"] == "JSON decode error"
    assert len(caplogs) == 1
    assert "trace" not in caplogs[0]


def test_put_create_with_trace(client, dbsession):
    """PUT traces new contacts by email address"""
    email_id = str(uuid4())
    data = {
        "email": {
            "email_id": email_id,
            "primary_email": "test+trace-me-mozilla-2021-05-13@example.com",
        }
    }
    with capture_logs() as caplogs:
        resp = client.put(f"/ctms/{email_id}", json=data)
    assert resp.status_code == 201
    assert len(caplogs) == 1
    assert caplogs[0]["trace"] == "test+trace-me-mozilla-2021-05-13@example.com"
    assert caplogs[0]["trace_json"] == data


def test_put_replace_with_trace(client, minimal_contact):
    """PUT traces replaced contacts by email"""
    email_id = minimal_contact.email.email_id
    data = json.loads(minimal_contact.json())
    data["email"]["first_name"] = "Jeff"
    data["email"]["primary_email"] = "test+trace-me-mozilla-2021-05-13@example.com"
    with capture_logs() as caplogs:
        resp = client.put(f"/ctms/{email_id}", json=data)
    assert resp.status_code == 201
    assert len(caplogs) == 1
    assert caplogs[0]["trace"] == "test+trace-me-mozilla-2021-05-13@example.com"
    assert caplogs[0]["trace_json"] == data
