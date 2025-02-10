from ctms import models
from ctms.cli.main import cli

# Tests for `ctms-cli permissions list`


def test_list_permissions(clirunner, permission_factory):
    """Test `ctms-cli permissions list` command."""
    # Create some permissions
    p1 = permission_factory(name="delete_object", description="Allows deletion of objects")
    p2 = permission_factory(name="view_object", description="Allows viewing objects")

    result = clirunner.invoke(cli, ["permissions", "list"])

    assert result.exit_code == 0
    assert f"{p1.name}: {p1.description}" in result.output
    assert f"{p2.name}: {p2.description}" in result.output


def test_list_permissions_no_permissions(clirunner):
    """Test `ctms-cli permissions list` command when no permissions exist."""
    result = clirunner.invoke(cli, ["permissions", "list"])

    assert result.exit_code == 0
    assert "No permissions found." in result.output


# Tests for `ctms-cli permissions create`


def test_create_permission(dbsession, clirunner):
    """Test `ctms-cli permissions create` command."""
    result = clirunner.invoke(cli, ["permissions", "create", "delete_object", "Allows deletion of objects"])

    assert result.exit_code == 0
    assert "✅ Created permission 'delete_object' with description: 'Allows deletion of objects'." in result.output

    perm = dbsession.query(models.Permissions).filter_by(name="delete_object").first()
    assert perm is not None
    assert perm.description == "Allows deletion of objects"


def test_create_permission_no_description(clirunner):
    """Test `ctms-cli permissions create` command with no description."""
    result = clirunner.invoke(cli, ["permissions", "create", "delete_object"])

    assert result.exit_code == 0
    assert "✅ Created permission 'delete_object' with description: ''." in result.output


def test_create_permission_no_name(clirunner):
    """Test `ctms-cli permissions create` command with no name."""
    result = clirunner.invoke(cli, ["permissions", "create"])

    assert result.exit_code == 2
    assert "Error: Missing argument 'PERMISSION_NAME'." in result.output


def test_create_permission_already_exists(clirunner, permission_factory):
    """Test `ctms-cli permissions create` command when permission already exists."""
    permission_factory(name="delete_object")

    result = clirunner.invoke(cli, ["permissions", "create", "delete_object", "Allows deletion of objects"])

    assert result.exit_code == 10
    assert "Permission 'delete_object' already exists." in result.output


# Tests for `ctms-cli permissions delete`


def test_delete_permission(dbsession, clirunner, permission_factory):
    """Test `ctms-cli permissions delete` command."""
    perm = permission_factory(name="delete_object")

    result = clirunner.invoke(cli, ["permissions", "delete", "--yes", "delete_object"])

    assert result.exit_code == 0
    assert "✅ Successfully deleted permission 'delete_object'." in result.output

    perm = dbsession.query(models.Permissions).filter_by(name="delete_object").first()
    assert perm is None


def test_delete_permission_with_confirmation_declined(dbsession, clirunner, permission_factory):
    """Test `ctms-cli permissions delete` command when confirmation is declined."""
    perm = permission_factory(name="delete_object")

    # Simulate user entering 'n' at the prompt
    result = clirunner.invoke(cli, ["permissions", "delete", "delete_object"], input="n\n")

    assert result.exit_code == 0
    assert "Operation cancelled." in result.output
    # Permission should still exist
    perm = dbsession.query(models.Permissions).filter_by(name="delete_object").first()
    assert perm is not None


def test_delete_permission_with_confirmation_accepted(dbsession, clirunner, permission_factory):
    """Test `ctms-cli permissions delete` command when confirmation is accepted."""
    perm = permission_factory(name="delete_object")

    # Simulate user entering 'y' at the prompt
    result = clirunner.invoke(cli, ["permissions", "delete", "delete_object"], input="y\n")

    assert result.exit_code == 0
    assert "✅ Successfully deleted permission 'delete_object'." in result.output
    # Permission should be deleted
    perm = dbsession.query(models.Permissions).filter_by(name="delete_object").first()
    assert perm is None


def test_delete_permission_not_found(clirunner):
    """Test `ctms-cli permissions delete` command when permission does not exist."""
    result = clirunner.invoke(cli, ["permissions", "delete", "delete_object"])

    assert result.exit_code == 4
    assert "Permission 'delete_object' not found." in result.output


def test_delete_permission_no_name(clirunner):
    """Test `ctms-cli permissions delete` command with no name."""
    result = clirunner.invoke(cli, ["permissions", "delete"])

    assert result.exit_code == 2
    assert "Error: Missing argument 'PERMISSION_NAME'." in result.output


def test_delete_permission_with_role(dbsession, clirunner, permission_factory, role_factory, role_permissions_factory):
    """Test `ctms-cli permissions delete` command when permission is assigned to a role."""
    perm = permission_factory(name="delete_object")
    role = role_factory(name="tester")
    role_permissions_factory(role=role, permission=perm)

    result = clirunner.invoke(cli, ["permissions", "delete", "delete_object"])

    assert result.exit_code == 10
    assert "Cannot delete permission 'delete_object' because it is assigned to roles." in result.output
    assert f"ctms-cli roles revoke {role.name} {perm.name}" in result.output

    perm = dbsession.query(models.Permissions).filter_by(name="delete_object").first()
    # The permission should not be deleted.
    assert perm is not None
