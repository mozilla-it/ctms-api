from ctms import models
from ctms.cli.main import cli
from ctms.permissions import ADMIN_ROLE_NAME

# Tests for `ctms-cli roles list`


def test_list_roles(clirunner, role_factory):
    """Test `ctms-cli roles list` command."""
    r1 = role_factory(name="manager", description="Manager role")
    r2 = role_factory(name="viewer", description="Viewer role")

    result = clirunner.invoke(cli, ["roles", "list"])

    assert result.exit_code == 0
    assert f"{r1.name}: {r1.description}" in result.output
    assert f"{r2.name}: {r2.description}" in result.output
    assert "admin: No description" in result.output


def test_list_roles_no_roles(dbsession, clirunner):
    """Test `ctms-cli roles list` command when no roles exist."""
    # Delete the admin role.
    dbsession.query(models.Roles).filter_by(name=ADMIN_ROLE_NAME).delete()

    result = clirunner.invoke(cli, ["roles", "list"])

    assert result.exit_code == 0
    assert "No roles found." in result.output


# Tests for `ctms-cli roles show`


def test_show_role(
    dbsession,
    clirunner,
    role_factory,
    permission_factory,
    role_permissions_factory,
    api_client_factory,
    api_client_roles_factory,
):
    """Test `ctms-cli roles show` command."""
    p1 = permission_factory(name="delete_object", description="Allows deletion of objects")
    p2 = permission_factory(name="view_object", description="Allows viewing objects")

    r1 = role_factory(name="manager", description="Manager role")
    r2 = role_factory(name="viewer", description="Viewer role")

    role_permissions_factory(role=r1, permission=p1)
    role_permissions_factory(role=r2, permission=p2)

    c1 = api_client_factory(client_id="id_client1", email="client1@example.com")
    c2 = api_client_factory(client_id="id_client2", email="client2@example.com")

    api_client_roles_factory(api_client=c1, role=r1)
    api_client_roles_factory(api_client=c2, role=r2)

    dbsession.commit()

    result = clirunner.invoke(cli, ["roles", "show", "manager"])

    assert result.exit_code == 0
    assert "Role: manager" in result.output
    assert "Description: Manager role" in result.output
    assert "Permissions:" in result.output
    assert f"  - {p1.name}: {p1.description}" in result.output
    assert "Assigned API Clients:" in result.output
    assert f"  - {c1.client_id}" in result.output

    assert f"  - {p2.name}: {p2.description}" not in result.output
    assert f"  - {c2.client_id}" not in result.output


def test_show_role_no_role(clirunner):
    """Test `ctms-cli roles show` command when role does not exist."""
    result = clirunner.invoke(cli, ["roles", "show", "manager"])

    assert result.exit_code == 4
    assert "Role 'manager' not found." in result.output


def test_show_role_no_permissions_or_clients(clirunner, role_factory):
    """Test `ctms-cli roles show` command when role has no permissions or clients."""
    role_factory(name="manager", description="Manager role")

    result = clirunner.invoke(cli, ["roles", "show", "manager"])

    assert result.exit_code == 0
    assert "Role: manager" in result.output
    assert "Description: Manager role" in result.output
    assert "No permissions assigned." in result.output
    assert "No API clients assigned to this role." in result.output


# Tests for `ctms-cli roles create`


def test_create_role(dbsession, clirunner):
    """Test `ctms-cli roles create` command."""
    result = clirunner.invoke(cli, ["roles", "create", "manager", "Manager role"])

    assert result.exit_code == 0
    assert "✅ Created role 'manager' with description: 'Manager role'." in result.output

    role = dbsession.query(models.Roles).filter_by(name="manager").first()
    assert role is not None
    assert role.description == "Manager role"


def test_create_role_no_description(clirunner):
    """Test `ctms-cli roles create` command with no description."""
    result = clirunner.invoke(cli, ["roles", "create", "manager"])

    assert result.exit_code == 0
    assert "✅ Created role 'manager' with description: ''." in result.output


def test_create_role_no_name(clirunner):
    """Test `ctms-cli roles create` command with no name."""
    result = clirunner.invoke(cli, ["roles", "create"])

    assert result.exit_code == 2
    assert "Error: Missing argument 'ROLE_NAME'." in result.output


def test_create_role_already_exists(clirunner, role_factory):
    """Test `ctms-cli roles create` command when role already exists."""
    role_factory(name="manager")

    result = clirunner.invoke(cli, ["roles", "create", "manager", "Manager role"])

    assert result.exit_code == 10
    assert "Role 'manager' already exists." in result.output


# Tests for `ctms-cli roles grant`


def test_grant_role(dbsession, clirunner, role_factory, permission_factory):
    """Test `ctms-cli roles grant` command."""
    role_factory(name="manager", description="Manager role")
    p1 = permission_factory(name="delete_object", description="Allows deletion of objects")

    dbsession.commit()

    result = clirunner.invoke(cli, ["roles", "grant", "manager", "delete_object"])

    assert result.exit_code == 0
    assert "✅ Granted permission 'delete_object' to role 'manager'." in result.output

    role = dbsession.query(models.Roles).filter_by(name="manager").first()
    assert role is not None
    assert len(role.permissions) == 1
    assert role.permissions[0].permission == p1


def test_grant_role_no_role(clirunner):
    """Test `ctms-cli roles grant` command when role does not exist."""
    result = clirunner.invoke(cli, ["roles", "grant", "manager", "delete_object"])

    assert result.exit_code == 4
    assert "Role 'manager' not found." in result.output


def test_grant_role_no_permission(clirunner, role_factory):
    """Test `ctms-cli roles grant` command when permission does not exist."""
    role_factory(name="manager")

    result = clirunner.invoke(cli, ["roles", "grant", "manager", "delete_object"])

    assert result.exit_code == 4
    assert "Permission 'delete_object' not found." in result.output


def test_grant_role_already_has_permission(dbsession, clirunner, role_factory, permission_factory, role_permissions_factory):
    """Test `ctms-cli roles grant` command when role already has permission."""
    role = role_factory(name="manager", description="Manager role")
    p1 = permission_factory(name="delete_object", description="Allows deletion of objects")
    role_permissions_factory(role=role, permission=p1)

    dbsession.commit()

    result = clirunner.invoke(cli, ["roles", "grant", "manager", "delete_object"])

    assert result.exit_code == 10
    assert "Role 'manager' already has permission 'delete_object'." in result.output


def test_grant_role_no_name(clirunner):
    """Test `ctms-cli roles grant` command with no name."""
    result = clirunner.invoke(cli, ["roles", "grant"])

    assert result.exit_code == 2
    assert "Error: Missing argument 'ROLE_NAME'." in result.output


def test_grant_role_no_permission_name(clirunner):
    """Test `ctms-cli roles grant` command with no permission name."""
    result = clirunner.invoke(cli, ["roles", "grant", "manager"])

    assert result.exit_code == 2
    assert "Error: Missing argument 'PERMISSION_NAME'." in result.output


# Tests for `ctms-cli roles revoke`


def test_revoke_role(dbsession, clirunner, role_factory, permission_factory, role_permissions_factory):
    """Test `ctms-cli roles revoke` command."""
    role = role_factory(name="manager", description="Manager role")
    p1 = permission_factory(name="delete_object", description="Allows deletion of objects")
    role_permissions_factory(role=role, permission=p1)

    dbsession.commit()

    result = clirunner.invoke(cli, ["roles", "revoke", "--yes", "manager", "delete_object"])

    assert result.exit_code == 0
    assert "✅ Revoked permission 'delete_object' from role 'manager'." in result.output

    role = dbsession.query(models.Roles).filter_by(name="manager").first()
    assert role is not None
    assert len(role.permissions) == 0


def test_revoke_role_with_confirmation_declined(dbsession, clirunner, role_factory, permission_factory, role_permissions_factory):
    """Test `ctms-cli roles revoke` command when confirmation is declined."""
    role = role_factory(name="manager", description="Manager role")
    p1 = permission_factory(name="delete_object", description="Allows deletion of objects")
    role_permissions_factory(role=role, permission=p1)

    dbsession.commit()

    # Simulate user entering 'n' at the prompt
    result = clirunner.invoke(cli, ["roles", "revoke", "manager", "delete_object"], input="n\n")

    assert result.exit_code == 0
    assert "Operation cancelled." in result.output
    # Permission should still be assigned to the role
    role = dbsession.query(models.Roles).filter_by(name="manager").first()
    assert len(role.permissions) == 1


def test_revoke_role_with_confirmation_accepted(dbsession, clirunner, role_factory, permission_factory, role_permissions_factory):
    """Test `ctms-cli roles revoke` command when confirmation is accepted."""
    role = role_factory(name="manager", description="Manager role")
    p1 = permission_factory(name="delete_object", description="Allows deletion of objects")
    role_permissions_factory(role=role, permission=p1)

    dbsession.commit()

    # Simulate user entering 'y' at the prompt
    result = clirunner.invoke(cli, ["roles", "revoke", "manager", "delete_object"], input="y\n")

    assert result.exit_code == 0
    assert "✅ Revoked permission 'delete_object' from role 'manager'." in result.output
    # Permission should be revoked from the role
    role = dbsession.query(models.Roles).filter_by(name="manager").first()
    assert len(role.permissions) == 0


def test_revoke_role_no_role(clirunner):
    """Test `ctms-cli roles revoke` command when role does not exist."""
    result = clirunner.invoke(cli, ["roles", "revoke", "manager", "delete_object"])

    assert result.exit_code == 4
    assert "Role 'manager' not found." in result.output


def test_revoke_role_no_permission(clirunner, role_factory):
    """Test `ctms-cli roles revoke` command when permission does not exist."""
    role_factory(name="manager")

    result = clirunner.invoke(cli, ["roles", "revoke", "manager", "delete_object"])

    assert result.exit_code == 4
    assert "Permission 'delete_object' not found." in result.output


def test_revoke_role_does_not_have_permission(dbsession, clirunner, role_factory, permission_factory):
    """Test `ctms-cli roles revoke` command when role does not have permission."""
    role_factory(name="manager", description="Manager role")
    permission_factory(name="delete_object", description="Allows deletion of objects")

    dbsession.commit()

    result = clirunner.invoke(cli, ["roles", "revoke", "manager", "delete_object"])

    assert result.exit_code == 10
    assert "Role 'manager' does not have permission 'delete_object'." in result.output


def test_revoke_role_no_name(clirunner):
    """Test `ctms-cli roles revoke` command with no name."""
    result = clirunner.invoke(cli, ["roles", "revoke"])

    assert result.exit_code == 2
    assert "Error: Missing argument 'ROLE_NAME'." in result.output


def test_revoke_role_no_permission_name(clirunner):
    """Test `ctms-cli roles revoke` command with no permission name."""
    result = clirunner.invoke(cli, ["roles", "revoke", "manager"])

    assert result.exit_code == 2
    assert "Error: Missing argument 'PERMISSION_NAME'." in result.output


# Tests for `ctms-cli roles delete`


def test_delete_role(dbsession, clirunner, role_factory):
    """Test `ctms-cli roles delete` command."""
    role = role_factory(name="manager", description="Manager role")

    dbsession.commit()

    result = clirunner.invoke(cli, ["roles", "delete", "--yes", "manager"])

    assert result.exit_code == 0
    assert "✅ Successfully deleted role 'manager'." in result.output

    role = dbsession.query(models.Roles).filter_by(name="manager").first()
    assert role is None


def test_delete_role_with_confirmation_declined(dbsession, clirunner, role_factory):
    """Test `ctms-cli roles delete` command when confirmation is declined."""
    role = role_factory(name="manager", description="Manager role")

    dbsession.commit()

    # Simulate user entering 'n' at the prompt
    result = clirunner.invoke(cli, ["roles", "delete", "manager"], input="n\n")

    assert result.exit_code == 0
    assert "Operation cancelled." in result.output
    # Role should still exist
    role = dbsession.query(models.Roles).filter_by(name="manager").first()
    assert role is not None


def test_delete_role_with_confirmation_accepted(dbsession, clirunner, role_factory):
    """Test `ctms-cli roles delete` command when confirmation is accepted."""
    role = role_factory(name="manager", description="Manager role")

    dbsession.commit()

    # Simulate user entering 'y' at the prompt
    result = clirunner.invoke(cli, ["roles", "delete", "manager"], input="y\n")

    assert result.exit_code == 0
    assert "✅ Successfully deleted role 'manager'." in result.output
    # Role should be deleted
    role = dbsession.query(models.Roles).filter_by(name="manager").first()
    assert role is None


def test_delete_role_no_role(clirunner):
    """Test `ctms-cli roles delete` command when role does not exist."""
    result = clirunner.invoke(cli, ["roles", "delete", "manager"])

    assert result.exit_code == 4
    assert "Role 'manager' not found." in result.output


def test_delete_role_no_name(clirunner):
    """Test `ctms-cli roles delete` command with no name."""
    result = clirunner.invoke(cli, ["roles", "delete"])

    assert result.exit_code == 2
    assert "Error: Missing argument 'ROLE_NAME'." in result.output


def test_delete_role_with_permissions(
    dbsession,
    clirunner,
    role_factory,
    permission_factory,
    role_permissions_factory,
):
    """Test `ctms-cli roles delete` command when role has permissions."""
    role = role_factory(name="manager", description="Manager role")
    permission = permission_factory(name="delete_object", description="Allows deletion of objects")
    role_permissions_factory(role=role, permission=permission)

    dbsession.commit()

    result = clirunner.invoke(cli, ["roles", "delete", "manager"])

    assert result.exit_code == 10
    assert "Cannot delete role 'manager' because it has permissions assigned." in result.output
    assert f"ctms-cli roles revoke {role.name} {permission.name}" in result.output


def test_delete_role_with_clients(
    dbsession,
    clirunner,
    role_factory,
    api_client_factory,
    api_client_roles_factory,
):
    """Test `ctms-cli roles delete` command when role has clients."""
    role = role_factory(name="manager", description="Manager role")
    client = api_client_factory(client_id="id_client1", email="client1@example.com")
    api_client_roles_factory(api_client=client, role=role)

    dbsession.commit()

    result = clirunner.invoke(cli, ["roles", "delete", "manager"])

    assert result.exit_code == 10
    assert "Cannot delete role 'manager' because it is assigned to API clients." in result.output
    assert f"ctms-cli clients revoke {client.client_id} {role.name}" in result.output
