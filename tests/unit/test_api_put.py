"""Unit tests for PUT /ctms/{email_id} (Create or update)"""
from uuid import UUID

import pytest

from tests.unit.sample_data import SAMPLE_CONTACTS
from tests.unit.test_api import _compare_written_contacts


def test_create_or_update_basic_id_is_different(client, minimal_contact):
    """This should fail since we require an email_id to PUT"""

    # This id is different from the one in the contact
    resp = client.put(
        "/ctms/d16c4ec4-caa0-4bf2-a06f-1bbf07bf03c7", minimal_contact.json()
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.parametrize("put_contact", SAMPLE_CONTACTS.keys(), indirect=True)
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


@pytest.mark.parametrize("put_contact", SAMPLE_CONTACTS.keys(), indirect=True)
def test_create_or_update_basic_empty_db(put_contact):
    """Most straightforward contact creation succeeds when there is no collision"""
    saved_contacts, sample, email_id = put_contact()
    _compare_written_contacts(saved_contacts[0], sample, email_id)


@pytest.mark.parametrize("put_contact", SAMPLE_CONTACTS.keys(), indirect=True)
def test_create_or_update_identical(put_contact):
    """Writing the same thing twice works both times"""
    saved_contacts, sample, email_id = put_contact()
    _compare_written_contacts(saved_contacts[0], sample, email_id)
    saved_contacts, sample, email_id = put_contact()
    _compare_written_contacts(saved_contacts[0], sample, email_id)


@pytest.mark.parametrize("put_contact", SAMPLE_CONTACTS.keys(), indirect=True)
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


@pytest.mark.parametrize("put_contact", SAMPLE_CONTACTS.keys(), indirect=True)
def test_create_or_update_change_basket_token(put_contact):
    """We can update a basket_token given a ctms ID"""
    saved_contacts, sample, email_id = put_contact()
    _compare_written_contacts(saved_contacts[0], sample, email_id)

    def _change_basket(contact):
        contact.email.basket_token = UUID("c97fb13b-3a19-4f4a-ac2d-abf0717b8df1")
        return contact

    saved_contacts, sample, email_id = put_contact(modifier=_change_basket)
    _compare_written_contacts(saved_contacts[0], sample, email_id)


@pytest.mark.parametrize("put_contact", SAMPLE_CONTACTS.keys(), indirect=True)
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


@pytest.mark.parametrize("put_contact", SAMPLE_CONTACTS.keys(), indirect=True)
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
