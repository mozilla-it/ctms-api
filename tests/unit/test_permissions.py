from ctms import models
from ctms.permissions import ADMIN_ROLE_NAME, has_any_permission


def test_has_permission_granted(
    dbsession,
    api_client_factory,
    api_client_roles_factory,
    permission_factory,
    role_factory,
    role_permissions_factory,
):
    """Test that a user with the required permission is granted access."""
    role = role_factory(name="editor")
    permission = permission_factory(name="edit_contact")
    role_permissions_factory(role=role, permission=permission)

    api_client = api_client_factory()
    api_client_roles_factory(api_client=api_client, role=role)

    dbsession.commit()

    assert has_any_permission(dbsession, api_client.client_id, ["edit_contact"]) is True


def test_has_permission_denied(dbsession, api_client_factory):
    """Test that a user without the required permission is denied access."""
    api_client = api_client_factory()
    dbsession.commit()

    assert has_any_permission(dbsession, api_client.client_id, ["edit_contact"]) is False


def test_admin_role_grants_all_permissions(
    dbsession,
    api_client_factory,
    api_client_roles_factory,
    role_factory,
):
    """Test that a user with the admin role is granted access to all actions."""
    admin_role = dbsession.query(models.Roles).filter_by(name=ADMIN_ROLE_NAME).first()
    api_client = api_client_factory()
    api_client_roles_factory(api_client=api_client, role=admin_role)
    dbsession.commit()

    assert has_any_permission(dbsession, api_client.client_id, ["any_perm", "other_perm"]) is True
