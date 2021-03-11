"""Tests for the private APIs that may be removed."""
from typing import Any, Tuple

import pytest

API_TEST_CASES: Tuple[Tuple[str, Any], ...] = (
    ("/identities", {"basket_token": "c4a7d759-bb52-457b-896b-90f1d3ef8433"}),
    ("/identity/332de237-cab7-4461-bcc3-48e68f42bd5c", {}),
    ("/contact/email/332de237-cab7-4461-bcc3-48e68f42bd5c", {}),
    ("/contact/amo/332de237-cab7-4461-bcc3-48e68f42bd5c", {}),
    ("/contact/vpn_waitlist/332de237-cab7-4461-bcc3-48e68f42bd5c", {}),
    ("/contact/fxa/332de237-cab7-4461-bcc3-48e68f42bd5c", {}),
)


@pytest.mark.parametrize("path,params", API_TEST_CASES)
def test_unauthorized_api_call_fails(anon_client, example_contact, path, params):
    """Calling the API without credentials fails."""
    resp = anon_client.get(path, params=params)
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Not authenticated"}


@pytest.mark.parametrize("path,params", API_TEST_CASES)
def test_authorized_api_call_succeeds(client, example_contact, path, params):
    """Calling the API without credentials fails."""
    resp = client.get(path, params=params)
    assert resp.status_code == 200


def identity_response_for_contact(contact):
    """Construct the expected identity object for a contact."""
    return {
        "email_id": str(contact.email.email_id),
        "primary_email": contact.email.primary_email,
        "basket_token": str(contact.email.basket_token),
        "sfdc_id": contact.email.sfdc_id,
        "mofo_id": contact.email.mofo_id,
        "amo_user_id": contact.amo.user_id if contact.amo else None,
        "fxa_id": contact.fxa.fxa_id if contact.fxa else None,
        "fxa_primary_email": contact.fxa.primary_email if contact.fxa else None,
    }


@pytest.mark.parametrize("name", ("minimal", "maximal", "example"))
def test_get_identity_by_email_id(client, sample_contacts, name):
    """GET /identity/{email_id} returns the identity object."""
    email_id, contact = sample_contacts[name]
    resp = client.get(f"/identity/{email_id}")
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
        ("example", "email_id"),
        ("minimal", "primary_email"),
        ("maximal", "basket_token"),
        ("minimal", "sfdc_id"),
        ("maximal", "amo_user_id"),
        ("maximal", "fxa_id"),
        ("example", "fxa_primary_email"),
    ),
)
def test_get_identities_by_alt_id(client, sample_contacts, name, ident):
    """GET /identities?alt_id=value returns a one-item identities list."""
    email_id, contact = sample_contacts[name]
    identity = identity_response_for_contact(contact)
    assert identity[ident]
    resp = client.get(f"/identities?{ident}={identity[ident]}")
    assert resp.status_code == 200
    assert resp.json() == [identity]


def test_get_identities_by_two_alt_id_match(client, maximal_contact):
    """GET /identities, with two matching IDs, returns a one-item identities list."""
    identity = identity_response_for_contact(maximal_contact)
    sfdc_id = identity["sfdc_id"]
    assert sfdc_id
    fxa_email = identity["fxa_primary_email"]
    assert fxa_email

    resp = client.get(f"/identities?sfdc_id={sfdc_id}&fxa_primary_email={fxa_email}")
    assert resp.status_code == 200
    assert resp.json() == [identity]


def test_get_identities_by_two_alt_id_mismatch_fails(
    client, minimal_contact, example_contact
):
    """GET /identities with two non-matching IDs returns an empty identities list."""
    email = minimal_contact.email.primary_email
    amo_user_id = example_contact.amo.user_id
    assert amo_user_id

    resp = client.get(f"/identities?primary_email={email}&amo_user_id={amo_user_id}")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_identities_by_two_alt_id_one_blank_fails(client, minimal_contact):
    """GET /identities with an empty parameter returns an empty list."""
    email = minimal_contact.email.primary_email
    assert not minimal_contact.amo

    resp = client.get(f"/identities?primary_email={email}&amo_user_id=")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_identities_with_no_alt_ids_fails(client, dbsession):
    """GET /identities without an alternate IDs query return an error."""
    resp = client.get(f"/identities")
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
        ("fxa_id", "cad092ec-a71a-4df5-aa92-517959caeecb"),
        ("fxa_primary_email", "unknown-user@example.com"),
        ("sfdc_id", "001A000404aUnknown"),
        ("mofo_id", "cad092ec-a71a-4df5-aa92-517959caeecb"),
    ],
)
def test_get_identities_with_unknown_ids_fails(
    client, dbsession, alt_id_name, alt_id_value
):
    """GET /identities returns an empty list if no IDs match."""
    resp = client.get(f"/identities?{alt_id_name}={alt_id_value}")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.parametrize("subgroup", ("email", "amo", "vpn_waitlist", "fxa"))
def test_get_subgroup(client, minimal_contact, subgroup):
    """GET /contact/{subgroup}/{email_id} returns the subgroup data."""
    email_id = minimal_contact.email.email_id
    full_resp = client.get(f"/ctms/{email_id}")
    assert full_resp.status_code == 200
    full_json = full_resp.json()
    resp = client.get(f"/contact/{subgroup}/{email_id}")
    assert resp.status_code == 200
    assert resp.json() == full_json[subgroup]


@pytest.mark.parametrize("subgroup", ("email", "amo", "vpn_waitlist", "fxa"))
def test_get_subgroup_not_found(client, dbsession, subgroup):
    """GET /contact/{subgroup}/{unknown email_id} returns a 404."""
    email_id = "cad092ec-a71a-4df5-aa92-517959caeecb"
    resp = client.get(f"/contact/{subgroup}/{email_id}")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Unknown email_id"}
