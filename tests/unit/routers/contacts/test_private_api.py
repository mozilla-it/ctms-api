"""Tests for the private APIs that may be removed."""

import json
from typing import Any, Tuple

import pytest

from ctms.schemas.contact import ContactSchema

API_TEST_CASES: Tuple[Tuple[str, Any], ...] = (
    ("/identities", {"basket_token": "c4a7d759-bb52-457b-896b-90f1d3ef8433"}),
    ("/identity/332de237-cab7-4461-bcc3-48e68f42bd5c", {}),
)


@pytest.mark.parametrize("path,params", API_TEST_CASES)
def test_authorized_api_call_succeeds(client, email_factory, path, params):
    """Calling the API with credentials succeeds."""
    email_factory(
        email_id="332de237-cab7-4461-bcc3-48e68f42bd5c",
        basket_token="c4a7d759-bb52-457b-896b-90f1d3ef8433",
    )

    resp = client.get(path, params=params)
    assert resp.status_code == 200


@pytest.mark.parametrize("path,params", API_TEST_CASES)
def test_unauthorized_api_call_fails(anon_client, path, params):
    """Calling the API without credentials fails."""
    resp = anon_client.get(path, params=params)
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Not authenticated"}


def identity_response_for_contact(contact):
    """Construct the expected identity object for a contact."""
    return {
        "email_id": str(contact.email.email_id),
        "primary_email": contact.email.primary_email,
        "basket_token": str(contact.email.basket_token),
        "sfdc_id": contact.email.sfdc_id,
        "mofo_contact_id": contact.mofo.mofo_contact_id if contact.mofo else None,
        "mofo_email_id": contact.mofo.mofo_email_id if contact.mofo else None,
        "amo_user_id": contact.amo.user_id if contact.amo else None,
        "fxa_id": contact.fxa.fxa_id if contact.fxa else None,
        "fxa_primary_email": contact.fxa.primary_email if contact.fxa else None,
    }


@pytest.mark.parametrize(
    "name", ("minimal_contact", "maximal_contact", "example_contact")
)
def test_get_identity_by_email_id(client, name, request):
    """GET /identity/{email_id} returns the identity object."""

    contact = request.getfixturevalue(name)
    resp = client.get(f"/identity/{contact.email.email_id}")
    assert resp.status_code == 200
    assert resp.json() == identity_response_for_contact(contact)


def test_get_identity_not_found(client, dbsession):
    """GET /identity/{unknown email_id} returns a 404."""
    email_id = "cad092ec-a71a-4df5-aa92-517959caeecb"
    resp = client.get(f"/identity/{email_id}")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Unknown email_id"}


@pytest.mark.parametrize(
    "name,ident",
    (
        ("example_contact", "email_id"),
        ("minimal_contact", "primary_email"),
        ("maximal_contact", "basket_token"),
        ("minimal_contact", "sfdc_id"),
        ("maximal_contact", "amo_user_id"),
        ("maximal_contact", "fxa_id"),
        ("example_contact", "fxa_primary_email"),
        ("maximal_contact", "mofo_contact_id"),
        ("maximal_contact", "mofo_email_id"),
    ),
)
def test_get_identities_by_alt_id(client, request, name, ident):
    """GET /identities?alt_id=value returns a one-item identities list."""
    contact = request.getfixturevalue(name)
    identity = identity_response_for_contact(contact)
    assert identity[ident]
    resp = client.get(f"/identities?{ident}={identity[ident]}")
    assert resp.status_code == 200
    assert resp.json() == [identity]


def test_get_identities_by_two_alt_id_match(client, email_factory):
    """GET /identities, with two matching IDs, returns a one-item identities list."""
    email = email_factory(with_fxa=True, sfdc_id="001A000001aABcDEFG")
    sfdc_id = email.sfdc_id
    assert sfdc_id
    fxa_email = email.fxa.primary_email
    assert fxa_email

    resp = client.get(f"/identities?sfdc_id={sfdc_id}&fxa_primary_email={fxa_email}")
    identity = json.loads(
        ContactSchema.from_email(email).as_identity_response().model_dump_json()
    )
    assert resp.status_code == 200
    assert resp.json() == [identity]


def test_get_identities_by_two_alt_id_mismatch_fails(client, email_factory):
    """GET /identities with two non-matching IDs returns an empty identities list."""
    email_1 = email_factory(with_amo=True)
    email_2 = email_factory(with_amo=True)

    resp = client.get(
        f"/identities?primary_email={email_1.primary_email}&amo_user_id={email_2.amo.user_id}"
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_identities_by_two_alt_id_one_blank_fails(client, email_factory):
    """GET /identities with an empty parameter returns an empty list."""
    email = email_factory()
    assert not email.amo

    resp = client.get(f"/identities?primary_email={email.email_id}&amo_user_id=")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_identities_with_no_alt_ids_fails(client, dbsession):
    """GET /identities without an alternate IDs query return an error."""
    resp = client.get("/identities")
    assert resp.status_code == 400
    assert resp.json() == {
        "detail": (
            "No identifiers provided, at least one is needed: "
            "email_id, "
            "primary_email, "
            "basket_token, "
            "sfdc_id, "
            "mofo_contact_id, "
            "mofo_email_id, "
            "amo_user_id, "
            "fxa_id, "
            "fxa_primary_email"
        )
    }


@pytest.mark.parametrize(
    "alt_id_name,alt_id_value",
    [
        ("email_id", "cad092ec-a71a-4df5-aa92-517959caeecb"),
        ("primary_email", "unknown-user@example.com"),
        ("amo_user_id", 404),
        ("basket_token", "cad092ec-a71a-4df5-aa92-517959caeecb"),
        ("fxa_id", "cad092ec-a71a-4df5-aa92-517959caeecb"),
        ("fxa_primary_email", "unknown-user@example.com"),
        ("sfdc_id", "001A000404aUnknown"),
        ("mofo_contact_id", "cad092ec-a71a-4df5-aa92-517959caeecb"),
        ("mofo_email_id", "cad092ec-a71a-4df5-aa92-517959caeecb"),
    ],
)
def test_get_identities_with_unknown_ids_fails(
    client, dbsession, alt_id_name, alt_id_value
):
    """GET /identities returns an empty list if no IDs match."""
    resp = client.get(f"/identities?{alt_id_name}={alt_id_value}")
    assert resp.status_code == 200
    assert resp.json() == []
