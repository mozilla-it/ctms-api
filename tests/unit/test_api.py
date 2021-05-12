"""pytest tests for API functionality"""
from typing import Any, Callable, Optional, Tuple
from uuid import UUID, uuid4

import pytest

from ctms.crud import (
    get_amo_by_email_id,
    get_contacts_by_any_id,
    get_fxa_by_email_id,
    get_mofo_by_email_id,
    get_newsletters_by_email_id,
    get_vpn_by_email_id,
)
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
        code: int = 201,
        stored_contacts: int = 1,
        query_fields: Optional[dict] = None,
        check_written: bool = True,
        record: Optional[ContactSchema] = None,
        new_default_fields: Optional[set] = None,
    ):
        if record:
            contact = record
        else:
            contact = _contact
        if query_fields is None:
            query_fields = {"primary_email": contact.email.primary_email}
        new_default_fields = new_default_fields or set()
        sample = contact.copy(deep=True)
        sample = modifier(sample)
        resp = client.put(f"/ctms/{sample.email.email_id}", sample.json())
        assert resp.status_code == code, resp.text
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
            if sample.dict().get(field) and code in {200, 201}:
                if field in fields_not_written or field in new_default_fields:
                    assert results is None or (
                        isinstance(results, list) and len(results) == 0
                    ), f"{sample_email_id} has field `{field}` but it is _default_ and it should _not_ have been written to db"
                else:
                    assert (
                        results
                    ), f"{sample_email_id} has field `{field}` and it should have been written to db"
            else:
                assert results is None or (
                    isinstance(results, list) and len(results) == 0
                ), f"{sample_email_id} does not have field `{field}` and it should _not_ have been written to db"

        if check_written:
            _check_written("amo", get_amo_by_email_id)
            _check_written("fxa", get_fxa_by_email_id)
            _check_written("mofo", get_mofo_by_email_id)
            _check_written("newsletters", get_newsletters_by_email_id)
            _check_written("vpn_waitlist", get_vpn_by_email_id)

        # Check that GET returns the same contact
        if code in {200, 201}:
            dbsession.expunge_all()
            get_resp = client.get(f"/ctms/{sample.email.email_id}")
            assert resp.json() == get_resp.json()

        return saved, sample, sample_email_id

    return _add


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
