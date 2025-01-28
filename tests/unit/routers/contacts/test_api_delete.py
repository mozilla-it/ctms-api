from tests.helpers import assign_role


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


def test_delete_contact_by_primary_email_without_permission(restricted_client, email_factory):
    """Use the restricted client with no permissions to test contact deletion."""
    email = email_factory()

    resp = restricted_client.delete(f"/ctms/{email.primary_email}")
    assert resp.status_code == 403


def test_delete_contact_by_primary_email_with_wrong_permission(dbsession, restricted_client, email_factory):
    """Use the restricted client with incorrect permissions to test contact deletion."""
    email = email_factory()
    assign_role(dbsession, "restricted_client", "view_contact")

    resp = restricted_client.delete(f"/ctms/{email.primary_email}")
    assert resp.status_code == 403


def test_delete_contact_by_primary_email_with_correct_permission(dbsession, restricted_client, email_factory):
    """Use the restricted client with incorrect permissions to test contact deletion."""
    email = email_factory()
    assign_role(dbsession, "restricted_client", "delete_contact")

    resp = restricted_client.delete(f"/ctms/{email.primary_email}")
    assert resp.status_code == 403
