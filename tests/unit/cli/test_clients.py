from ctms import models
from ctms.cli.main import cli
from ctms.permissions import ADMIN_ROLE_NAME

# Tests for `ctms-cli clients list`


def test_list_clients(clirunner, api_client_factory):
    """Test `ctms-cli clients list` command."""
    # Create some clients
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com")
    c2 = api_client_factory(client_id="id_client2", email="client2@example.com", enabled=False)

    result = clirunner.invoke(cli, ["clients", "list"])

    assert result.exit_code == 0
    assert f"{c1.client_id} ({c1.email}) - Enabled | Last Access: Never" in result.output
    assert f"{c2.client_id} ({c2.email}) - Disabled" in result.output


def test_list_clients_no_clients(clirunner):
    """Test `ctms-cli clients list` command when no clients exist."""

    result = clirunner.invoke(cli, ["clients", "list"])

    assert result.exit_code == 0
    assert "No API clients found." in result.output


# Tests for `ctms-cli clients show`


def test_show_client(dbsession, clirunner, api_client_factory):
    """Test `ctms-cli clients show` command."""
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com")
    admin_role = dbsession.query(models.Roles).filter_by(name=ADMIN_ROLE_NAME).one()
    c1.roles.append(models.ApiClientRoles(role=admin_role))

    dbsession.commit()

    result = clirunner.invoke(cli, ["clients", "show", c1.client_id])

    assert result.exit_code == 0
    assert f"API Client: {c1.client_id}" in result.output
    assert f"Email: {c1.email}" in result.output
    assert f"Enabled: {'Yes' if c1.enabled else 'No'}" in result.output
    assert f"Last Access: {c1.last_access or 'Never'}" in result.output
    assert "Assigned Roles:" in result.output
    assert f"  - {c1.roles[0].role.name}" in result.output


def test_show_client_not_found(clirunner):
    """Test `ctms-cli clients show` command when client not found."""
    result = clirunner.invoke(cli, ["clients", "show", "id_non_existent_client"])

    assert result.exit_code == 4
    assert "API client 'id_non_existent_client' not found." in result.output


def test_show_client_no_roles(dbsession, clirunner, api_client_factory):
    """Test `ctms-cli clients show` command when client has no roles."""
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com")

    result = clirunner.invoke(cli, ["clients", "show", c1.client_id])

    assert result.exit_code == 0
    assert f"API Client: {c1.client_id}" in result.output
    assert f"Email: {c1.email}" in result.output
    assert f"Enabled: {'Yes' if c1.enabled else 'No'}" in result.output
    assert f"Last Access: {c1.last_access or 'Never'}" in result.output
    assert "No roles assigned." in result.output


# Tests for `ctms-cli clients grant`


def test_grant_role(dbsession, clirunner, api_client_factory, role_factory):
    """Test `ctms-cli clients grant` command."""
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com")
    r1 = role_factory(name="role1")

    result = clirunner.invoke(cli, ["clients", "grant", c1.client_id, r1.name])
    dbsession.refresh(c1)

    assert result.exit_code == 0
    assert f"✅ Granted role '{r1.name}' to API client '{c1.client_id}'." in result.output
    assert len(c1.roles) == 1
    assert c1.roles[0].role.name == r1.name


def test_grant_role_already_exists(dbsession, clirunner, api_client_factory, role_factory):
    """Test `ctms-cli clients grant` command when role already exists."""
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com")
    r1 = role_factory(name="role1")
    c1.roles.append(models.ApiClientRoles(role=r1))
    dbsession.commit()

    result = clirunner.invoke(cli, ["clients", "grant", c1.client_id, r1.name])

    assert result.exit_code == 0
    assert f"API client '{c1.client_id}' already has role '{r1.name}'." in result.output


def test_grant_role_client_not_found(clirunner):
    """Test `ctms-cli clients grant` command when client not found."""
    result = clirunner.invoke(cli, ["clients", "grant", "id_non_existent_client", "role1"])

    assert result.exit_code == 4
    assert "API client 'id_non_existent_client' not found." in result.output


def test_grant_role_role_not_found(clirunner, api_client_factory):
    """Test `ctms-cli clients grant` command when role not found."""
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com")

    result = clirunner.invoke(cli, ["clients", "grant", c1.client_id, "non_existent_role"])

    assert result.exit_code == 4
    assert "Role 'non_existent_role' not found." in result.output


# Tests for `ctms-cli clients revoke`


def test_revoke_role(dbsession, clirunner, api_client_factory, role_factory):
    """Test `ctms-cli clients revoke` command."""
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com")
    r1 = role_factory(name="role1")
    c1.roles.append(models.ApiClientRoles(role=r1))
    dbsession.commit()

    result = clirunner.invoke(cli, ["clients", "revoke", "--yes", c1.client_id, r1.name])
    dbsession.refresh(c1)

    assert result.exit_code == 0
    assert f"✅ Revoked role '{r1.name}' from API client '{c1.client_id}'." in result.output
    assert len(c1.roles) == 0


def test_revoke_role_with_confirmation_declined(dbsession, clirunner, api_client_factory, role_factory):
    """Test `ctms-cli clients revoke` command when confirmation is declined."""
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com")
    r1 = role_factory(name="role1")
    c1.roles.append(models.ApiClientRoles(role=r1))
    dbsession.commit()

    # Simulate user entering 'n' at the prompt
    result = clirunner.invoke(cli, ["clients", "revoke", c1.client_id, r1.name], input="n\n")
    dbsession.refresh(c1)

    assert result.exit_code == 0
    assert "Operation cancelled." in result.output
    # Role should still be assigned
    assert len(c1.roles) == 1


def test_revoke_role_with_confirmation_accepted(dbsession, clirunner, api_client_factory, role_factory):
    """Test `ctms-cli clients revoke` command when confirmation is accepted."""
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com")
    r1 = role_factory(name="role1")
    c1.roles.append(models.ApiClientRoles(role=r1))
    dbsession.commit()

    # Simulate user entering 'y' at the prompt
    result = clirunner.invoke(cli, ["clients", "revoke", c1.client_id, r1.name], input="y\n")
    dbsession.refresh(c1)

    assert result.exit_code == 0
    assert f"✅ Revoked role '{r1.name}' from API client '{c1.client_id}'." in result.output
    # Role should be revoked
    assert len(c1.roles) == 0


def test_revoke_role_not_assigned(dbsession, clirunner, api_client_factory, role_factory):
    """Test `ctms-cli clients revoke` command when role not assigned."""
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com")
    r1 = role_factory(name="role1")

    result = clirunner.invoke(cli, ["clients", "revoke", c1.client_id, r1.name])
    assert result.exit_code == 10
    assert f"API client '{c1.client_id}' does not have role '{r1.name}'." in result.output


def test_revoke_client_not_found(clirunner):
    """Test `ctms-cli clients revoke` command when client not found."""
    result = clirunner.invoke(cli, ["clients", "revoke", "id_non_existent_client", "role1"])

    assert result.exit_code == 4
    assert "API client 'id_non_existent_client' not found." in result.output


def test_revoke_role_not_found(clirunner, api_client_factory):
    """Test `ctms-cli clients revoke` command when role not found."""
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com")

    result = clirunner.invoke(cli, ["clients", "revoke", c1.client_id, "non_existent_role"])

    assert result.exit_code == 4
    assert "Role 'non_existent_role' not found." in result.output


# Tests for `ctms-cli clients create`


def test_create_client(clirunner):
    """Test `ctms-cli clients create` command."""
    result = clirunner.invoke(cli, ["clients", "create", "id_client1", "client1@example.com"])

    assert result.exit_code == 0
    assert "✅ Created API client 'id_client1' with email: 'client1@example.com'." in result.output
    assert "** 🔑 Client Credentials -- Store Securely! 🔑 **" in result.output
    assert "- Client ID: id_client1" in result.output
    assert "- Client Secret:" in result.output


def test_create_client_invalid_email(clirunner):
    """Test `ctms-cli clients create` command when email is invalid."""
    result = clirunner.invoke(cli, ["clients", "create", "id_client1", "invalid_email"])

    assert result.exit_code == 2
    assert "Error: Invalid value for 'EMAIL': value is not a valid email address: An email address must have an @-sign." in result.output


def test_create_client_invalid_id(clirunner):
    """Test `ctms-cli clients create` command when client ID is invalid."""
    result = clirunner.invoke(cli, ["clients", "create", "invalid_id", "client1@example.com"])
    assert result.exit_code == 2
    assert (
        "Client ID 'invalid_id' is invalid. It must start with 'id_' and should contain only "
        "alphanumeric characters, hyphens, underscores, or periods." in result.output
    )


def test_create_client_already_exists(dbsession, clirunner, api_client_factory):
    """Test `ctms-cli clients create` command when client already exists."""
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com")

    result = clirunner.invoke(cli, ["clients", "create", c1.client_id, c1.email])

    assert result.exit_code == 10
    assert "API client 'id_client1' already exists." in result.output


# Tests for `ctms-cli clients delete`


def test_delete_client(dbsession, clirunner, api_client_factory):
    """Test `ctms-cli clients delete` command."""
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com")
    client_id = c1.client_id

    result = clirunner.invoke(cli, ["clients", "delete", "--yes", client_id])

    assert result.exit_code == 0
    assert f"✅ Deleted API client '{client_id}'." in result.output
    assert dbsession.query(models.ApiClient).filter(models.ApiClient.client_id == client_id).first() is None


def test_delete_client_with_confirmation_declined(dbsession, clirunner, api_client_factory):
    """Test `ctms-cli clients delete` command when confirmation is declined."""
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com")
    client_id = c1.client_id

    # Simulate user entering 'n' at the prompt
    result = clirunner.invoke(cli, ["clients", "delete", client_id], input="n\n")

    assert result.exit_code == 0
    assert "Operation cancelled." in result.output
    # Verify client was not deleted
    assert dbsession.query(models.ApiClient).filter(models.ApiClient.client_id == client_id).first() is not None


def test_delete_client_with_confirmation_accepted(dbsession, clirunner, api_client_factory):
    """Test `ctms-cli clients delete` command when confirmation is accepted."""
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com")
    client_id = c1.client_id

    # Simulate user entering 'y' at the prompt
    result = clirunner.invoke(cli, ["clients", "delete", client_id], input="y\n")

    assert result.exit_code == 0
    assert f"✅ Deleted API client '{client_id}'." in result.output
    # Verify client was deleted
    assert dbsession.query(models.ApiClient).filter(models.ApiClient.client_id == client_id).first() is None


def test_delete_client_not_found(clirunner):
    """Test `ctms-cli clients delete` command when client not found."""
    result = clirunner.invoke(cli, ["clients", "delete", "id_non_existent"])

    assert result.exit_code == 4
    assert "API client 'id_non_existent' not found." in result.output


# Tests for `ctms-cli clients enable`


def test_enable_client(dbsession, clirunner, api_client_factory):
    """Test `ctms-cli clients enable` command."""
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com", enabled=False)
    client_id = c1.client_id

    result = clirunner.invoke(cli, ["clients", "enable", client_id])
    dbsession.refresh(c1)

    assert result.exit_code == 0
    assert f"✅ Enabled API client '{client_id}'." in result.output
    assert c1.enabled is True


def test_enable_client_already_enabled(dbsession, clirunner, api_client_factory):
    """Test `ctms-cli clients enable` command when client is already enabled."""
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com", enabled=True)
    client_id = c1.client_id

    result = clirunner.invoke(cli, ["clients", "enable", client_id])

    assert result.exit_code == 0
    assert f"API client '{client_id}' is already enabled." in result.output


def test_enable_client_not_found(clirunner):
    """Test `ctms-cli clients enable` command when client not found."""
    result = clirunner.invoke(cli, ["clients", "enable", "id_non_existent"])

    assert result.exit_code == 4
    assert "API client 'id_non_existent' not found." in result.output


# Tests for `ctms-cli clients disable`


def test_disable_client(dbsession, clirunner, api_client_factory):
    """Test `ctms-cli clients disable` command."""
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com", enabled=True)
    client_id = c1.client_id

    result = clirunner.invoke(cli, ["clients", "disable", "--yes", client_id])
    dbsession.refresh(c1)

    assert result.exit_code == 0
    assert f"✅ Disabled API client '{client_id}'." in result.output
    assert c1.enabled is False


def test_disable_client_with_confirmation_declined(dbsession, clirunner, api_client_factory):
    """Test `ctms-cli clients disable` command when confirmation is declined."""
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com", enabled=True)
    client_id = c1.client_id

    # Simulate user entering 'n' at the prompt
    result = clirunner.invoke(cli, ["clients", "disable", client_id], input="n\n")
    dbsession.refresh(c1)

    assert result.exit_code == 0
    assert "Operation cancelled." in result.output
    # Client should still be enabled
    assert c1.enabled is True


def test_disable_client_with_confirmation_accepted(dbsession, clirunner, api_client_factory):
    """Test `ctms-cli clients disable` command when confirmation is accepted."""
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com", enabled=True)
    client_id = c1.client_id

    # Simulate user entering 'y' at the prompt
    result = clirunner.invoke(cli, ["clients", "disable", client_id], input="y\n")
    dbsession.refresh(c1)

    assert result.exit_code == 0
    assert f"✅ Disabled API client '{client_id}'." in result.output
    # Client should be disabled
    assert c1.enabled is False


def test_disable_client_already_disabled(dbsession, clirunner, api_client_factory):
    """Test `ctms-cli clients disable` command when client is already disabled."""
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com", enabled=False)
    client_id = c1.client_id

    result = clirunner.invoke(cli, ["clients", "disable", client_id])

    assert result.exit_code == 0
    assert f"API client '{client_id}' is already disabled." in result.output


def test_disable_client_not_found(clirunner):
    """Test `ctms-cli clients disable` command when client not found."""
    result = clirunner.invoke(cli, ["clients", "disable", "id_non_existent"])

    assert result.exit_code == 4
    assert "API client 'id_non_existent' not found." in result.output


# Tests for `ctms-cli clients rotate-secret`


def test_rotate_secret(dbsession, clirunner, api_client_factory):
    """Test `ctms-cli clients rotate-secret` command."""
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com")
    original_secret_hash = c1.hashed_secret

    result = clirunner.invoke(cli, ["clients", "rotate-secret", "--yes", c1.client_id])
    dbsession.refresh(c1)

    assert result.exit_code == 0
    assert f"✅ Rotated secret for API client '{c1.client_id}'." in result.output
    assert "** 🔑 Client Credentials -- Store Securely! 🔑 **" in result.output
    assert f"  - Client ID: {c1.client_id}" in result.output
    assert "  - Client Secret: " in result.output
    # Verify the hash changed
    assert c1.hashed_secret != original_secret_hash


def test_rotate_secret_with_confirmation_declined(dbsession, clirunner, api_client_factory):
    """Test `ctms-cli clients rotate-secret` command when confirmation is declined."""
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com")
    original_secret_hash = c1.hashed_secret

    # Simulate user entering 'n' at the prompt
    result = clirunner.invoke(cli, ["clients", "rotate-secret", c1.client_id], input="n\n")
    dbsession.refresh(c1)

    assert result.exit_code == 0
    assert "Operation cancelled." in result.output
    # Secret should not be rotated
    assert c1.hashed_secret == original_secret_hash


def test_rotate_secret_with_confirmation_accepted(dbsession, clirunner, api_client_factory):
    """Test `ctms-cli clients rotate-secret` command when confirmation is accepted."""
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com")
    original_secret_hash = c1.hashed_secret

    # Simulate user entering 'y' at the prompt
    result = clirunner.invoke(cli, ["clients", "rotate-secret", c1.client_id], input="y\n")
    dbsession.refresh(c1)

    assert result.exit_code == 0
    assert f"✅ Rotated secret for API client '{c1.client_id}'." in result.output
    # Secret should be rotated
    assert c1.hashed_secret != original_secret_hash


def test_rotate_secret_for_disabled_client(dbsession, clirunner, api_client_factory):
    """Test `ctms-cli clients rotate-secret` command with disabled client."""
    c1 = api_client_factory(client_id="id_client1", email="client1@example.com", enabled=False)

    # Secret can still be rotated for disabled clients - they might be re-enabled later.
    result = clirunner.invoke(cli, ["clients", "rotate-secret", "--yes", c1.client_id])

    assert result.exit_code == 0
    assert f"✅ Rotated secret for API client '{c1.client_id}'." in result.output


def test_rotate_secret_client_not_found(clirunner):
    """Test `ctms-cli clients rotate-secret` command when client not found."""
    result = clirunner.invoke(cli, ["clients", "rotate-secret", "id_non_existent"])

    assert result.exit_code == 4
    assert "API client 'id_non_existent' not found." in result.output
