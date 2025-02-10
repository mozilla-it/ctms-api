import re
import sys
from secrets import token_urlsafe

import click
from pydantic import EmailStr
from pydantic_core import PydanticCustomError
from sqlalchemy.orm import Session

from ctms import config
from ctms.crud import create_api_client, update_api_client_secret
from ctms.models import ApiClient, ApiClientRoles, Roles
from ctms.schemas import ApiClientSchema


def validate_client_id(client_id: str) -> bool:
    """
    Validate that a client ID follows the required format.

    Requirements:
    - Must start with 'id_'
    - Must only contain alphanumeric characters, hyphens, underscores, or periods

    Returns:
        bool: True if valid, False otherwise
    """
    return client_id.startswith("id_") and re.match(r"^[-_.a-zA-Z0-9]*$", client_id) is not None


class ClientIdParamType(click.ParamType):
    name = "client_id"

    def convert(self, value, param, ctx):
        if not validate_client_id(value):
            self.fail(
                f"Client ID '{value}' is invalid. It must start with 'id_' and should contain only "
                "alphanumeric characters, hyphens, underscores, or periods.",
                param,
                ctx,
            )
        return value


class EmailParamType(click.ParamType):
    name = "email"

    def convert(self, value, param, ctx):
        try:
            return EmailStr._validate(value)
        except PydanticCustomError as e:
            self.fail(e, param, ctx)


@click.group()
@click.pass_context
def clients_cli(ctx: click.Context) -> None:
    """Manage API clients and their roles."""
    ctx.ensure_object(dict)


@clients_cli.command("list")
@click.pass_context
def list_clients(ctx: click.Context) -> None:
    """List all API clients, showing last accessed datetime for enabled clients."""
    db: Session = ctx.obj["db"]
    clients: list[ApiClient] = db.query(ApiClient).all()

    if not clients:
        click.echo("No API clients found.")
        return

    click.echo("API Clients:")
    for client in clients:
        status: str = "Enabled" if client.enabled else "Disabled"
        last_access_display: str = client.last_access.strftime("%Y-%m-%d %H:%M:%S") if client.enabled and client.last_access else "Never"

        if client.enabled:
            click.echo(f"- {client.client_id} ({client.email}) - {status} | Last Access: {last_access_display}")
        else:
            click.echo(f"- {client.client_id} ({client.email}) - {status}")


@clients_cli.command("show")
@click.argument("client_id", type=ClientIdParamType())
@click.pass_context
def show_client(ctx: click.Context, client_id: str) -> None:
    """Show details of an API client."""
    db: Session = ctx.obj["db"]

    client: ApiClient | None = db.query(ApiClient).filter(ApiClient.client_id == client_id).first()
    if not client:
        click.echo(f"API client '{client_id}' not found.")
        sys.exit(4)

    click.echo(f"API Client: {client.client_id}")
    click.echo(f"Email: {client.email}")
    click.echo(f"Enabled: {'Yes' if client.enabled else 'No'}")
    click.echo(f"Last Access: {client.last_access or 'Never'}")

    if client.roles:
        click.echo("Assigned Roles:")
        for client_role in client.roles:
            click.echo(f"  - {client_role.role.name}")
    else:
        click.echo("No roles assigned.")


@clients_cli.command("grant")
@click.argument("client_id", type=ClientIdParamType())
@click.argument("role_name", type=str)
@click.pass_context
def grant_role(ctx: click.Context, client_id: str, role_name: str) -> None:
    """Grant a role to an API client."""
    db: Session = ctx.obj["db"]

    client: ApiClient | None = db.query(ApiClient).filter(ApiClient.client_id == client_id).first()
    if not client:
        click.echo(f"API client '{client_id}' not found.")
        sys.exit(4)

    role: Roles | None = db.query(Roles).filter(Roles.name == role_name).first()
    if not role:
        click.echo(f"Role '{role_name}' not found.")
        sys.exit(4)

    if any(client_role.role_id == role.id for client_role in client.roles):
        click.echo(f"API client '{client_id}' already has role '{role_name}'.")
        return

    new_assignment: ApiClientRoles = ApiClientRoles(api_client_id=client_id, role_id=role.id)
    db.add(new_assignment)
    db.commit()

    click.echo(f"✅ Granted role '{role_name}' to API client '{client_id}'.")


@clients_cli.command("revoke")
@click.argument("client_id", type=ClientIdParamType())
@click.argument("role_name", type=str)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.pass_context
def remove_role(ctx: click.Context, client_id: str, role_name: str, yes: bool) -> None:
    """Revoke a role from an API client."""
    db: Session = ctx.obj["db"]

    client: ApiClient | None = db.query(ApiClient).filter(ApiClient.client_id == client_id).first()
    if not client:
        click.echo(f"API client '{client_id}' not found.")
        sys.exit(4)

    role: Roles | None = db.query(Roles).filter(Roles.name == role_name).first()
    if not role:
        click.echo(f"Role '{role_name}' not found.")
        sys.exit(4)

    role_assignment = next((cr for cr in client.roles if cr.role_id == role.id), None)

    if not role_assignment:
        click.echo(f"API client '{client_id}' does not have role '{role_name}'.")
        sys.exit(10)

    if not yes and not click.confirm(f"Are you sure you want to revoke role '{role_name}' from API client '{client_id}'?"):
        click.echo("Operation cancelled.")
        return

    db.delete(role_assignment)
    db.commit()

    click.echo(f"✅ Revoked role '{role_name}' from API client '{client_id}'.")


@clients_cli.command("create")
@click.argument("client_id", type=ClientIdParamType())
@click.argument("email", type=EmailParamType())
@click.pass_context
def create_client(ctx: click.Context, client_id: str, email: str) -> None:
    """Create a new API client and output credentials."""
    db: Session = ctx.obj["db"]

    # Check if client already exists.
    existing_client: ApiClient | None = db.query(ApiClient).filter(ApiClient.client_id == client_id).first()
    if existing_client:
        click.echo(f"API client '{client_id}' already exists.")
        sys.exit(10)

    api_client: ApiClientSchema = ApiClientSchema(client_id=client_id, email=email, enabled=True)
    client_secret: str = f"secret_{token_urlsafe(32)}"
    create_api_client(db, api_client, client_secret)
    db.commit()

    click.echo(f"✅ Created API client '{client_id}' with email: '{email}'.")
    output_client_credentials(client_id, client_secret)


@clients_cli.command("delete")
@click.argument("client_id", type=ClientIdParamType())
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.pass_context
def delete_client(ctx: click.Context, client_id: str, yes: bool) -> None:
    """Delete an API client."""
    db: Session = ctx.obj["db"]

    client: ApiClient | None = db.query(ApiClient).filter(ApiClient.client_id == client_id).first()
    if not client:
        click.echo(f"API client '{client_id}' not found.")
        sys.exit(4)

    if not yes and not click.confirm(f"Are you sure you want to delete API client '{client_id}'?"):
        click.echo("Operation cancelled.")
        return

    db.delete(client)
    db.commit()

    click.echo(f"✅ Deleted API client '{client_id}'.")


@clients_cli.command("enable")
@click.argument("client_id", type=ClientIdParamType())
@click.pass_context
def enable_client(ctx: click.Context, client_id: str) -> None:
    """Enable an API client."""
    db: Session = ctx.obj["db"]

    client: ApiClient | None = db.query(ApiClient).filter(ApiClient.client_id == client_id).first()
    if not client:
        click.echo(f"API client '{client_id}' not found.")
        sys.exit(4)

    if not client.enabled:
        client.enabled = True
        db.commit()
        click.echo(f"✅ Enabled API client '{client_id}'.")
    else:
        click.echo(f"API client '{client_id}' is already enabled.")


@clients_cli.command("disable")
@click.argument("client_id", type=ClientIdParamType())
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.pass_context
def disable_client(ctx: click.Context, client_id: str, yes: bool) -> None:
    """Disable an API client."""
    db: Session = ctx.obj["db"]

    client: ApiClient | None = db.query(ApiClient).filter(ApiClient.client_id == client_id).first()
    if not client:
        click.echo(f"API client '{client_id}' not found.")
        sys.exit(4)

    if client.enabled:
        if not yes and not click.confirm(f"Are you sure you want to disable API client '{client_id}'? This will prevent it from accessing the API."):
            click.echo("Operation cancelled.")
            return

        client.enabled = False
        db.commit()
        click.echo(f"✅ Disabled API client '{client_id}'.")
    else:
        click.echo(f"API client '{client_id}' is already disabled.")


@clients_cli.command("rotate-secret")
@click.argument("client_id", type=ClientIdParamType())
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.pass_context
def rotate_secret(ctx: click.Context, client_id: str, yes: bool) -> None:
    """Rotate the secret for an existing API client and output new credentials."""
    db: Session = ctx.obj["db"]

    api_client: ApiClient | None = db.query(ApiClient).filter(ApiClient.client_id == client_id).first()
    if not api_client:
        click.echo(f"API client '{client_id}' not found.")
        sys.exit(4)

    if not yes and not click.confirm(
        f"Are you sure you want to rotate the secret for API client '{client_id}'? This will invalidate the existing secret."
    ):
        click.echo("Operation cancelled.")
        return

    client_secret: str = f"secret_{token_urlsafe(32)}"
    update_api_client_secret(db, api_client, client_secret)
    db.commit()

    click.echo(f"✅ Rotated secret for API client '{client_id}'.")
    output_client_credentials(client_id, client_secret)


def output_client_credentials(client_id: str, client_secret: str) -> None:
    """Output the client credentials to the console."""
    settings = config.Settings()

    click.echo("\n** 🔑 Client Credentials -- Store Securely! 🔑 **")
    click.echo(f"  - Client ID: {client_id}")
    click.echo(f"  - Client Secret: {client_secret}")
    click.echo("\n** Example: Obtain an OAuth Token **")
    click.echo("Use the following curl command to get an access token:")
    click.echo(f"\n  curl --user {client_id}:{client_secret} -F grant_type=client_credentials {settings.server_prefix}/token\n")
