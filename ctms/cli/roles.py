import sys

import click
from sqlalchemy.orm import Session

from ctms.models import Permissions, RolePermissions, Roles


@click.group()
@click.pass_context
def roles_cli(ctx: click.Context) -> None:
    """Manage roles."""
    ctx.ensure_object(dict)


@roles_cli.command("list")
@click.pass_context
def list_roles(ctx: click.Context) -> None:
    """List all available roles."""
    db: Session = ctx.obj["db"]
    roles: list[Roles] = db.query(Roles).all()

    if not roles:
        click.echo("No roles found.")
        return

    for role in roles:
        click.echo(f"- {role.name}: {role.description or 'No description'}")


@roles_cli.command("show")
@click.argument("role_name", type=str)
@click.pass_context
def show_role(ctx: click.Context, role_name: str) -> None:
    """Show details of a specific role, including assigned permissions and API clients."""
    db: Session = ctx.obj["db"]

    role: Roles | None = db.query(Roles).filter(Roles.name == role_name).first()
    if not role:
        click.echo(f"Role '{role_name}' not found.")
        sys.exit(4)

    click.echo(f"Role: {role.name}")
    click.echo(f"Description: {role.description or 'No description'}")

    if role.permissions:
        click.echo("Permissions:")
        for rp in role.permissions:
            click.echo(f"  - {rp.permission.name}: {rp.permission.description or 'No description'}")
    else:
        click.echo("No permissions assigned.")

    if role.api_clients:
        click.echo("Assigned API Clients:")
        for api_client_role in role.api_clients:
            click.echo(f"  - {api_client_role.api_client_id}")
    else:
        click.echo("No API clients assigned to this role.")


@roles_cli.command("create")
@click.argument("role_name", type=str)
@click.argument("description", required=False, default="", type=str)
@click.pass_context
def create_role(ctx: click.Context, role_name: str, description: str) -> None:
    """Create a new role."""
    db: Session = ctx.obj["db"]

    # Check if role already exists.
    existing_role: Roles | None = db.query(Roles).filter(Roles.name == role_name).first()
    if existing_role:
        click.echo(f"Role '{role_name}' already exists.")
        sys.exit(10)

    role: Roles = Roles(name=role_name, description=description)
    db.add(role)

    db.commit()
    click.echo(f"✅ Created role '{role_name}' with description: '{description}'.")


@roles_cli.command("grant")
@click.argument("role_name", type=str)
@click.argument("permission_name", type=str)
@click.pass_context
def grant_permission(ctx: click.Context, role_name: str, permission_name: str) -> None:
    """Grant a permission to a role."""
    db: Session = ctx.obj["db"]

    role: Roles | None = db.query(Roles).filter(Roles.name == role_name).first()
    if not role:
        click.echo(f"Role '{role_name}' not found.")
        sys.exit(4)

    permission: Permissions | None = db.query(Permissions).filter(Permissions.name == permission_name).first()
    if not permission:
        click.echo(f"Permission '{permission_name}' not found.")
        sys.exit(4)

    existing: RolePermissions | None = db.query(RolePermissions).filter_by(role_id=role.id, permission_id=permission.id).first()
    if existing:
        click.echo(f"Role '{role_name}' already has permission '{permission_name}'.")
        sys.exit(10)

    new_role_permission: RolePermissions = RolePermissions(role_id=role.id, permission_id=permission.id)
    db.add(new_role_permission)

    db.commit()
    click.echo(f"✅ Granted permission '{permission_name}' to role '{role_name}'.")


@roles_cli.command("revoke")
@click.argument("role_name", type=str)
@click.argument("permission_name", type=str)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.pass_context
def revoke_permission(ctx: click.Context, role_name: str, permission_name: str, yes: bool) -> None:
    """Revoke a permission from a role."""
    db: Session = ctx.obj["db"]

    role: Roles | None = db.query(Roles).filter(Roles.name == role_name).first()
    if not role:
        click.echo(f"Role '{role_name}' not found.")
        sys.exit(4)

    permission: Permissions | None = db.query(Permissions).filter(Permissions.name == permission_name).first()
    if not permission:
        click.echo(f"Permission '{permission_name}' not found.")
        sys.exit(4)

    role_permission = next((rp for rp in role.permissions if rp.permission_id == permission.id), None)

    if not role_permission:
        click.echo(f"Role '{role_name}' does not have permission '{permission_name}'.")
        sys.exit(10)

    if not yes and not click.confirm(f"Are you sure you want to revoke permission '{permission_name}' from role '{role_name}'?"):
        click.echo("Operation cancelled.")
        return

    db.delete(role_permission)
    db.commit()

    click.echo(f"✅ Revoked permission '{permission_name}' from role '{role_name}'.")


@roles_cli.command("delete")
@click.argument("role_name", type=str)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.pass_context
def delete_role(ctx: click.Context, role_name: str, yes: bool) -> None:
    """Delete a role, but only if no API clients or permissions are using it."""
    db: Session = ctx.obj["db"]

    role: Roles | None = db.query(Roles).filter(Roles.name == role_name).first()
    if not role:
        click.echo(f"Role '{role_name}' not found.")
        sys.exit(4)

    # Check if any API clients are assigned this role.
    if role.api_clients:
        click.echo(f"Cannot delete role '{role_name}' because it is assigned to API clients.")
        click.echo("To proceed, remove the role from clients first:")
        for client_role in role.api_clients:
            click.echo(f"  ctms-cli clients revoke {client_role.api_client_id} {role_name}")
        sys.exit(10)

    # Check if any permissions are assigned to this role.
    if role.permissions:
        click.echo(f"Cannot delete role '{role_name}' because it has permissions assigned.")
        click.echo("To proceed, revoke these permissions first:")
        for role_perm in role.permissions:
            click.echo(f"  ctms-cli roles revoke {role_name} {role_perm.permission.name}")
        sys.exit(10)

    if not yes and not click.confirm(f"Are you sure you want to delete role '{role_name}'?"):
        click.echo("Operation cancelled.")
        return

    # Safe to delete the role.
    db.delete(role)
    db.commit()
    click.echo(f"✅ Successfully deleted role '{role_name}'.")
