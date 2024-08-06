"""Unit tests for POST /ctms (create record)"""

import logging
from uuid import UUID

import pytest

from tests.unit.conftest import SAMPLE_CONTACT_PARAMS

from .test_api import _compare_written_contacts

POST_TEST_PARAMS = pytest.mark.parametrize(
    "post_contact", SAMPLE_CONTACT_PARAMS, indirect=True
)


@POST_TEST_PARAMS
def test_create_basic_no_id(post_contact):
    """Most straightforward contact creation succeeds when email_id is not a key."""

    def _remove_id(contact):
        del contact.email.email_id
        return contact

    saved_contacts, sample, email_id = post_contact(
        modifier=_remove_id, check_redirect=False
    )
    _compare_written_contacts(
        saved_contacts[0], sample, email_id, ids_should_be_identical=False
    )


@POST_TEST_PARAMS
def test_create_basic_id_is_none(post_contact):
    """Most straightforward contact creation succeeds when email_id is None."""

    def _remove_id(contact):
        contact.email.email_id = None
        return contact

    saved_contacts, sample, email_id = post_contact(
        modifier=_remove_id, check_redirect=False
    )
    _compare_written_contacts(
        saved_contacts[0], sample, email_id, ids_should_be_identical=False
    )


@POST_TEST_PARAMS
def test_create_basic_with_id(post_contact):
    """Most straightforward contact creation succeeds when email_id is specified."""
    saved_contacts, sample, email_id = post_contact()
    _compare_written_contacts(saved_contacts[0], sample, email_id)


@POST_TEST_PARAMS
def test_create_basic_idempotent(post_contact):
    """Creating a contact works across retries."""
    saved_contacts, sample, email_id = post_contact()
    _compare_written_contacts(saved_contacts[0], sample, email_id)
    saved_contacts, _, _ = post_contact(code=200)
    _compare_written_contacts(saved_contacts[0], sample, email_id)


@POST_TEST_PARAMS
def test_create_basic_with_id_collision(post_contact):
    """Creating a contact with the same id but different data fails."""
    _, sample, _ = post_contact()

    def _change_mailing(contact):
        assert contact.email.mailing_country != "mx", "sample data has changed"
        contact.email.mailing_country = "mx"
        return contact

    # We set check_written to False because the rows it would check for normally
    # are actually here due to the first write
    saved_contacts, _, _ = post_contact(
        modifier=_change_mailing, code=409, check_redirect=False, check_written=False
    )
    assert saved_contacts[0].email.mailing_country == sample.email.mailing_country


@POST_TEST_PARAMS
def test_create_basic_with_basket_collision(post_contact):
    """Creating a contact with diff ids but same email fails.
    We override the basket token so that we know we're not colliding on that here.
    See test_create_basic_with_email_collision below for that check
    """
    saved_contacts, orig_sample, email_id = post_contact()
    _compare_written_contacts(saved_contacts[0], orig_sample, email_id)

    def _change_basket(contact):
        contact.email.email_id = UUID("229cfa16-a8c9-4028-a9bd-fe746dc6bf73")
        contact.email.basket_token = UUID("df9f7086-4949-4b2d-8fcf-49167f8f783d")
        return contact

    saved_contacts, _, _ = post_contact(
        modifier=_change_basket, code=409, check_redirect=False
    )
    _compare_written_contacts(saved_contacts[0], orig_sample, email_id)


@POST_TEST_PARAMS
def test_create_basic_with_email_collision(post_contact):
    """Creating a contact with diff ids but same basket token fails.
    We override the email so that we know we're not colliding on that here.
    See other test for that check
    """
    saved_contacts, orig_sample, email_id = post_contact()
    _compare_written_contacts(saved_contacts[0], orig_sample, email_id)

    def _change_primary_email(contact):
        contact.email.email_id = UUID("229cfa16-a8c9-4028-a9bd-fe746dc6bf73")
        contact.email.primary_email = "foo@example.com"
        return contact

    saved_contacts, _, _ = post_contact(
        modifier=_change_primary_email, code=409, check_redirect=False
    )
    _compare_written_contacts(saved_contacts[0], orig_sample, email_id)


def test_create_with_non_json_is_error(client, caplog):
    """When non-JSON is posted /ctms, a 422 is returned"""
    data = b"this is not JSON"
    with caplog.at_level(logging.INFO, logger="ctms.web"):
        resp = client.post("/ctms", content=data)

    assert resp.status_code == 422
    assert resp.json()["detail"][0]["msg"] == "JSON decode error"
    assert len(caplog.records) == 1
    assert not hasattr(caplog.records[0], "trace")
