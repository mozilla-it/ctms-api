"""Unit tests for GET /ctms?alt_id=value, returning list of contacts"""

import pytest


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
        ("mofo_contact_id", "5e499cc0-eeb5-4f0e-aae6-a101721874b8"),
        ("mofo_email_id", "195207d2-63f2-4c9f-b149-80e9c408477a"),
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
        ("fxa_id", "cad092eca71a-4df5-aa92-517959caeecb"),
        ("fxa_primary_email", "unknown-user@example.com"),
        ("sfdc_id", "001A000404aUnknown"),
        ("mofo_contact_id", "cad092ec-a71a-4df5-aa92-517959caeecb"),
        ("mofo_email_id", "cad092ec-a71a-4df5-aa92-517959caeecb"),
    ],
)
def test_get_ctms_by_alt_id_none_found(client, dbsession, alt_id_name, alt_id_value):
    """An empty list is returned when no contacts have the alternate ID."""
    resp = client.get("/ctms", params={alt_id_name: alt_id_value})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 0
