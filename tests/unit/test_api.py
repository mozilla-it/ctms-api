"""pytest tests for API functionality"""
from typing import Any, Callable, Optional, Tuple
from uuid import UUID, uuid4

import pytest

from ctms.crud import (
    get_amo_by_email_id,
    get_contacts_by_any_id,
    get_fxa_by_email_id,
    get_newsletters_by_email_id,
    get_vpn_by_email_id,
)
from ctms.sample_data import SAMPLE_CONTACTS
from ctms.schemas import ContactInSchema, ContactSchema, NewsletterInSchema


def test_get_ctms_for_minimal_contact(client, minimal_contact):
    """GET /ctms/{email_id} returns a contact with most fields unset."""
    email_id = minimal_contact.email.email_id
    resp = client.get(f"/ctms/{email_id}")
    assert resp.status_code == 200
    assert resp.json() == {
        "amo": {
            "add_on_ids": None,
            "create_timestamp": None,
            "display_name": None,
            "email_opt_in": False,
            "language": None,
            "last_login": None,
            "location": None,
            "profile_url": None,
            "update_timestamp": None,
            "user": False,
            "user_id": None,
            "username": None,
        },
        "email": {
            "basket_token": "142e20b6-1ef5-43d8-b5f4-597430e956d7",
            "create_timestamp": "2014-01-22T15:24:00+00:00",
            "double_opt_in": False,
            "email_format": "H",
            "email_id": "93db83d4-4119-4e0c-af87-a713786fa81d",
            "email_lang": "en",
            "first_name": None,
            "has_opted_out_of_email": False,
            "last_name": None,
            "mailing_country": "us",
            "mofo_id": None,
            "mofo_relevant": False,
            "primary_email": "ctms-user@example.com",
            "sfdc_id": "001A000001aABcDEFG",
            "unsubscribe_reason": None,
            "update_timestamp": "2020-01-22T15:24:00+00:00",
        },
        "fxa": {
            "created_date": None,
            "account_deleted": False,
            "first_service": None,
            "fxa_id": None,
            "lang": None,
            "primary_email": None,
        },
        "newsletters": [
            {
                "format": "H",
                "lang": "en",
                "name": "app-dev",
                "source": None,
                "subscribed": True,
                "unsub_reason": None,
            },
            {
                "format": "H",
                "lang": "en",
                "name": "maker-party",
                "source": None,
                "subscribed": True,
                "unsub_reason": None,
            },
            {
                "format": "H",
                "lang": "en",
                "name": "mozilla-foundation",
                "source": None,
                "subscribed": True,
                "unsub_reason": None,
            },
            {
                "format": "H",
                "lang": "en",
                "name": "mozilla-learning-network",
                "source": None,
                "subscribed": True,
                "unsub_reason": None,
            },
        ],
        "status": "ok",
        "vpn_waitlist": {"geo": None, "platform": None},
    }


def test_get_ctms_for_maximal_contact(client, maximal_contact):
    """GET /ctms/{email_id} returns a contact with almost all fields set."""
    email_id = maximal_contact.email.email_id
    resp = client.get(f"/ctms/{email_id}")
    assert resp.status_code == 200
    assert resp.json() == {
        "amo": {
            "add_on_ids": "fanfox,foxfan",
            "create_timestamp": "2017-05-12T15:16:00+00:00",
            "display_name": "#1 Mozilla Fan",
            "email_opt_in": True,
            "language": "fr,en",
            "last_login": "2020-01-27",
            "location": "The Inter",
            "profile_url": "firefox/user/14508209",
            "update_timestamp": "2020-01-27T14:25:43+00:00",
            "user": True,
            "user_id": "123",
            "username": "Mozilla1Fan",
        },
        "email": {
            "basket_token": "d9ba6182-f5dd-4728-a477-2cc11bf62b69",
            "create_timestamp": "2010-01-01T08:04:00+00:00",
            "double_opt_in": True,
            "email_format": "H",
            "email_id": "67e52c77-950f-4f28-accb-bb3ea1a2c51a",
            "email_lang": "fr",
            "first_name": "Fan",
            "has_opted_out_of_email": False,
            "last_name": "of Mozilla",
            "mailing_country": "ca",
            "mofo_id": "195207d2-63f2-4c9f-b149-80e9c408477a",
            "mofo_relevant": True,
            "primary_email": "mozilla-fan@example.com",
            "sfdc_id": "001A000001aMozFan",
            "unsubscribe_reason": "done with this mailing list",
            "update_timestamp": "2020-01-28T14:50:00+00:00",
        },
        "fxa": {
            "created_date": "2019-05-22T08:29:31.906094+00:00",
            "account_deleted": False,
            "first_service": "monitor",
            "fxa_id": "611b6788-2bba-42a6-98c9-9ce6eb9cbd34",
            "lang": "fr,fr-CA",
            "primary_email": "fxa-firefox-fan@example.com",
        },
        "newsletters": [
            {
                "format": "H",
                "lang": "en",
                "name": "ambassadors",
                "source": "https://www.mozilla.org/en-US/contribute/studentambassadors/",
                "subscribed": False,
                "unsub_reason": "Graduated, don't have time for FSA",
            },
            {
                "format": "T",
                "lang": "fr",
                "name": "common-voice",
                "source": "https://commonvoice.mozilla.org/fr",
                "subscribed": True,
                "unsub_reason": None,
            },
            {
                "format": "H",
                "lang": "fr",
                "name": "firefox-accounts-journey",
                "source": "https://www.mozilla.org/fr/firefox/accounts/",
                "subscribed": False,
                "unsub_reason": "done with this mailing list",
            },
            {
                "format": "H",
                "lang": "en",
                "name": "firefox-os",
                "source": None,
                "subscribed": True,
                "unsub_reason": None,
            },
            {
                "format": "H",
                "lang": "fr",
                "name": "hubs",
                "source": None,
                "subscribed": True,
                "unsub_reason": None,
            },
            {
                "format": "H",
                "lang": "en",
                "name": "mozilla-festival",
                "source": None,
                "subscribed": True,
                "unsub_reason": None,
            },
            {
                "format": "H",
                "lang": "fr",
                "name": "mozilla-foundation",
                "source": None,
                "subscribed": True,
                "unsub_reason": None,
            },
        ],
        "status": "ok",
        "vpn_waitlist": {"geo": "ca", "platform": "windows,android"},
    }


def test_get_ctms_for_api_example(client, example_contact):
    """The API examples represent a valid contact with many fields set.
    Test that the API examples are valid."""
    email_id = example_contact.email.email_id
    resp = client.get(f"/ctms/{email_id}")
    assert resp.status_code == 200
    assert resp.json() == {
        "amo": {
            "add_on_ids": "add-on-1,add-on-2",
            "create_timestamp": "2020-12-05T19:21:50.908000+00:00",
            "display_name": "Add-ons Author",
            "email_opt_in": False,
            "language": "en",
            "last_login": "2021-01-28",
            "location": "California",
            "profile_url": "firefox/user/98765",
            "update_timestamp": "2021-02-04T15:36:57.511000+00:00",
            "user": True,
            "user_id": "98765",
            "username": "AddOnAuthor",
        },
        "email": {
            "basket_token": "c4a7d759-bb52-457b-896b-90f1d3ef8433",
            "create_timestamp": "2020-03-28T15:41:00+00:00",
            "double_opt_in": True,
            "email_format": "H",
            "email_id": "332de237-cab7-4461-bcc3-48e68f42bd5c",
            "email_lang": "en",
            "first_name": "Jane",
            "has_opted_out_of_email": False,
            "last_name": "Doe",
            "mailing_country": "us",
            "mofo_id": None,
            "mofo_relevant": False,
            "primary_email": "contact@example.com",
            "sfdc_id": "001A000023aABcDEFG",
            "unsubscribe_reason": None,
            "update_timestamp": "2021-01-28T21:26:57.511000+00:00",
        },
        "fxa": {
            "account_deleted": False,
            "created_date": "2021-01-29T18:43:49.082375+00:00",
            "first_service": "sync",
            "fxa_id": "6eb6ed6ac3b64259968aa490c6c0b9df",
            "lang": "en,en-US",
            "primary_email": "my-fxa-acct@example.com",
        },
        "newsletters": [
            {
                "format": "H",
                "lang": "en",
                "name": "firefox-welcome",
                "source": None,
                "subscribed": True,
                "unsub_reason": None,
            },
            {
                "format": "H",
                "lang": "en",
                "name": "mozilla-welcome",
                "source": None,
                "subscribed": True,
                "unsub_reason": None,
            },
        ],
        "status": "ok",
        "vpn_waitlist": {"geo": "fr", "platform": "ios,mac"},
    }


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
                "basket_token": str(uuid4()),
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
        assert method == "POST"
        resp = anon_client.post(path, json=params)
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Not authenticated"}


@pytest.mark.parametrize("method,path,params", API_TEST_CASES)
def test_authorized_api_call_succeeds(client, example_contact, method, path, params):
    """Calling the API without credentials fails."""
    if method == "GET":
        resp = client.get(path, params=params)
    else:
        assert method == "POST"
        resp = client.post(path, json=params)
    assert resp.status_code in {200, 303}


def test_get_ctms_not_found(client, dbsession):
    """GET /ctms/{unknown email_id} returns a 404."""
    email_id = "cad092ec-a71a-4df5-aa92-517959caeecb"
    resp = client.get(f"/ctms/{email_id}")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Unknown email_id"}


@pytest.mark.parametrize(
    "alt_id_name,alt_id_value",
    [
        ("email_id", "67e52c77-950f-4f28-accb-bb3ea1a2c51a"),
        ("primary_email", "mozilla-fan@example.com"),
        ("amo_user_id", 123),
        ("basket_token", "d9ba6182-f5dd-4728-a477-2cc11bf62b69"),
        ("fxa_id", "611b6788-2bba-42a6-98c9-9ce6eb9cbd34"),
        ("fxa_primary_email", "fxa-firefox-fan@example.com"),
        ("sfdc_id", "001A000001aMozFan"),
        ("mofo_id", "195207d2-63f2-4c9f-b149-80e9c408477a"),
    ],
)
def test_get_ctms_by_alt_id(sample_contacts, client, alt_id_name, alt_id_value):
    """The desired contact can be fetched by alternate ID."""
    maximal_id, _ = sample_contacts["maximal"]
    resp = client.get("/ctms", params={alt_id_name: alt_id_value})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["email"]["email_id"] == str(maximal_id)


def test_get_ctms_by_no_ids_is_error(client, dbsession):
    """Calling GET /ctms with no ID query is an error."""
    resp = client.get("/ctms")
    assert resp.status_code == 400
    assert resp.json() == {
        "detail": "No identifiers provided, at least one is needed: email_id, primary_email, basket_token, sfdc_id, mofo_id, amo_user_id, fxa_id, fxa_primary_email"
    }


@pytest.mark.parametrize(
    "alt_id_name,alt_id_value",
    [
        ("email_id", "cad092ec-a71a-4df5-aa92-517959caeecb"),
        ("primary_email", "unknown-user@example.com"),
        ("amo_user_id", 404),
        ("basket_token", "cad092ec-a71a-4df5-aa92-517959caeecb"),
        ("fxa_id", "cad092eca71a-4df5-aa92-517959caeecb"),
        ("fxa_primary_email", "unknown-user@example.com"),
        ("sfdc_id", "001A000404aUnknown"),
        ("mofo_id", "cad092ec-a71a-4df5-aa92-517959caeecb"),
    ],
)
def test_get_ctms_by_alt_id_none_found(client, dbsession, alt_id_name, alt_id_value):
    """An empty list is returned when no contacts have the alternate ID."""
    resp = client.get("/ctms", params={alt_id_name: alt_id_value})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 0


@pytest.fixture
def post_contact(request, client, dbsession):
    _id = (
        request.param
        if hasattr(request, "param")
        else "d1da1c99-fe09-44db-9c68-78a75752574d"
    )
    email_id = UUID(str(_id))
    contact = SAMPLE_CONTACTS[email_id]
    fields_not_written = SAMPLE_CONTACTS.get_not_written(email_id)

    def _add(
        modifier: Callable[[ContactSchema], ContactSchema] = lambda x: x,
        code: int = 303,
        stored_contacts: int = 1,
        check_redirect: bool = True,
        query_fields: Optional[dict] = None,
        check_written: bool = True,
    ):
        if query_fields is None:
            query_fields = {"primary_email": contact.email.primary_email}
        sample = contact.copy(deep=True)
        sample = modifier(sample)
        resp = client.post("/ctms", sample.json())
        assert resp.status_code == code, resp.text
        if check_redirect:
            assert resp.headers["location"] == f"/ctms/{sample.email.email_id}"
        saved = [
            ContactSchema(**c)
            for c in get_contacts_by_any_id(dbsession, **query_fields)
        ]
        assert len(saved) == stored_contacts

        # Now make sure that we skip writing default models
        def _check_written(field, getter, result_list=False):
            # We delete this field in one test case so we have to check
            # to see if it is even there
            if hasattr(sample.email, "email_id") and sample.email.email_id is not None:
                written_id = sample.email.email_id
            else:
                written_id = resp.headers["location"].split("/")[-1]
            results = getter(dbsession, written_id)
            if sample.dict().get(field) and code == 303:
                if field in fields_not_written:
                    if result_list:
                        assert (
                            results == []
                        ), f"{email_id} has field `{field}` but it is _default_ and it should _not_ have been written to db"
                    else:
                        assert (
                            results is None
                        ), f"{email_id} has field `{field}` but it is _default_ and it should _not_ have been written to db"
                else:
                    assert (
                        results
                    ), f"{email_id} has field `{field}` and it should have been written to db"
            else:
                if result_list:
                    assert (
                        results == []
                    ), f"{email_id} does not have field `{field}` and it should _not_ have been written to db"
                else:
                    assert (
                        results is None
                    ), f"{email_id} does not have field `{field}` and it should _not_ have been written to db"

        if check_written:
            _check_written("amo", get_amo_by_email_id)
            _check_written("fxa", get_fxa_by_email_id)
            _check_written("newsletters", get_newsletters_by_email_id, result_list=True)
            _check_written("vpn_waitlist", get_vpn_by_email_id)

        return saved, sample, email_id

    return _add


def _compare_written_contacts(
    contact,
    sample,
    email_id,
    ids_should_be_identical: bool = True,
    new_default_fields: set = set(),
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


@pytest.mark.parametrize("post_contact", SAMPLE_CONTACTS.keys(), indirect=True)
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


@pytest.mark.parametrize("post_contact", SAMPLE_CONTACTS.keys(), indirect=True)
def test_create_basic_with_id(post_contact):
    """Most straightforward contact creation succeeds when email_id is specified."""
    saved_contacts, sample, email_id = post_contact()
    _compare_written_contacts(saved_contacts[0], sample, email_id)


@pytest.mark.parametrize("post_contact", SAMPLE_CONTACTS.keys(), indirect=True)
def test_create_basic_idempotent(post_contact):
    """Creating a contact works across retries."""
    saved_contacts, sample, email_id = post_contact()
    _compare_written_contacts(saved_contacts[0], sample, email_id)
    saved_contacts, _, _ = post_contact()
    _compare_written_contacts(saved_contacts[0], sample, email_id)


@pytest.mark.parametrize("post_contact", SAMPLE_CONTACTS.keys(), indirect=True)
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


@pytest.mark.parametrize("post_contact", SAMPLE_CONTACTS.keys(), indirect=True)
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


@pytest.mark.parametrize("post_contact", SAMPLE_CONTACTS.keys(), indirect=True)
def test_create_basic_with_email_collision(post_contact):
    """Creating a contact with diff ids but same basket token fails.
    We override the email so that we know we're not colliding on that here.
    See other test for that check
    """
    saved_contacts, orig_sample, email_id = post_contact()
    _compare_written_contacts(saved_contacts[0], orig_sample, email_id)

    def _change_primary_email(contact):
        contact.email.email_id = UUID("229cfa16-a8c9-4028-a9bd-fe746dc6bf73")
        contact.email.primary_email = "foo@bar.com"
        return contact

    saved_contacts, _, _ = post_contact(
        modifier=_change_primary_email, code=409, check_redirect=False
    )
    _compare_written_contacts(saved_contacts[0], orig_sample, email_id)


@pytest.fixture
def put_contact(request, client, dbsession):
    _id = (
        request.param
        if hasattr(request, "param")
        else "d1da1c99-fe09-44db-9c68-78a75752574d"
    )
    sample_email_id = UUID(str(_id))
    _contact = SAMPLE_CONTACTS[sample_email_id]
    fields_not_written = SAMPLE_CONTACTS.get_not_written(sample_email_id)

    def _add(
        modifier: Callable[[ContactSchema], ContactSchema] = lambda x: x,
        code: int = 303,
        stored_contacts: int = 1,
        check_redirect: bool = True,
        query_fields: Optional[dict] = None,
        check_written: bool = True,
        record: Optional[ContactSchema] = None,
        new_default_fields: set = set(),
    ):
        if record:
            contact = record
        else:
            contact = _contact
        if query_fields is None:
            query_fields = {"primary_email": contact.email.primary_email}
        sample = contact.copy(deep=True)
        sample = modifier(sample)
        resp = client.put("/ctms", sample.json())
        assert resp.status_code == code, resp.text
        if check_redirect:
            assert resp.headers["location"] == f"/ctms/{sample.email.email_id}"
        saved = [
            ContactSchema(**c)
            for c in get_contacts_by_any_id(dbsession, **query_fields)
        ]
        assert len(saved) == stored_contacts

        # Now make sure that we skip writing default models
        def _check_written(field, getter):
            # We delete this field in one test case so we have to check
            # to see if it is even there
            if hasattr(sample.email, "email_id") and sample.email.email_id is not None:
                written_id = sample.email.email_id
            else:
                written_id = resp.headers["location"].split("/")[-1]
            results = getter(dbsession, written_id)
            if sample.dict().get(field) and code == 303:
                if field in fields_not_written or field in new_default_fields:
                    assert (
                        results is None
                    ), f"{sample_email_id} has field `{field}` but it is _default_ and it should _not_ have been written to db"
                else:
                    assert (
                        results
                    ), f"{sample_email_id} has field `{field}` and it should have been written to db"
            else:
                assert (
                    results is None
                ), f"{sample_email_id} does not have field `{field}` and it should _not_ have been written to db"

        if check_written:
            _check_written("amo", get_amo_by_email_id)
            _check_written("fxa", get_fxa_by_email_id)
            _check_written("newsletters", get_newsletters_by_email_id)
            _check_written("vpn_waitlist", get_vpn_by_email_id)

        return saved, sample, sample_email_id

    return _add


@pytest.mark.parametrize("put_contact", SAMPLE_CONTACTS.keys(), indirect=True)
def test_create_or_update_basic_no_id(put_contact):
    """This should fail since we require an email_id to PUT"""

    def _remove_id(contact):
        del contact.email.email_id
        return contact

    saved_contacts, sample, email_id = put_contact(
        modifier=_remove_id,
        check_redirect=False,
        code=422,
        stored_contacts=0,
        check_written=False,
    )


@pytest.mark.parametrize("put_contact", SAMPLE_CONTACTS.keys(), indirect=True)
def test_create_or_update_basic_id_is_none(put_contact):
    """This should fail since we require an email_id to PUT"""

    def _remove_id(contact):
        contact.email.email_id = None
        return contact

    saved_contacts, sample, email_id = put_contact(
        modifier=_remove_id,
        check_redirect=False,
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
        contact.email.primary_email = "something-new@whatever.com"
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
    contact.email.primary_email = "something-new@some-website.com"


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
