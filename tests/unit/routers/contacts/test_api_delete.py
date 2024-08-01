"""Unit tests for DELETE /ctms/{primar_email}"""


def test_delete_contact_by_primary_email_not_found(client):
    resp = client.delete("/ctms/foo@bar.com")
    assert resp.status_code == 404


def test_delete_contact_by_primary_email(client, email_factory):
    primary_email = email_factory().primary_email

    resp = client.delete(f"/ctms/{primary_email}")
    assert resp.status_code == 200
    resp = client.delete(f"/ctms/{primary_email}")
    assert resp.status_code == 404


def test_delete_contact_by_primary_email_with_basket_token_unset(client, email_factory):
    email = email_factory(basket_token=None)

    resp = client.delete(f"/ctms/{email.primary_email}")
    assert resp.status_code == 200
