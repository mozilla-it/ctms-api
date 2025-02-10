import sys

import click
from sqlalchemy.orm import Session

from ctms.models import Permissions


@click.group()
@click.pass_context
def permissions_cli(ctx: click.Context) -> None:
    """Manage permissions."""
    ctx.ensure_object(dict)


@permissions_cli.command("list")
@click.pass_context
def list_permissions(ctx: click.Context) -> None:
    """List all available permissions."""
    db: Session = ctx.obj["db"]

    permissions: list[Permissions] = db.query(Permissions).all()

    if not permissions:
        click.echo("No permissions found.")
        return

    click.echo("Available Permissions:")
    for perm in permissions:
        click.echo(f"- {perm.name}: {perm.description or 'No description'}")


@permissions_cli.command("create")
@click.argument("permission_name", type=str)
@click.argument("description", required=False, default="", type=str)
@click.pass_context
def create_permission(ctx: click.Context, permission_name: str, description: str) -> None:
    """Create a new permission."""
    db: Session = ctx.obj["db"]

    # Check if the permission already exists.
    existing_permission: Permissions | None = db.query(Permissions).filter(Permissions.name == permission_name).first()
    if existing_permission:
        click.echo(f"Permission '{permission_name}' already exists.")
        sys.exit(10)

    permission: Permissions = Permissions(name=permission_name, description=description)
    db.add(permission)

    db.commit()
    click.echo(f"✅ Created permission '{permission_name}' with description: '{description}'.")


@permissions_cli.command("delete")
@click.argument("permission_name", type=str)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.pass_context
def delete_permission(ctx: click.Context, permission_name: str, yes: bool) -> None:
    """Delete a permission, but only if no roles are using it."""
    db: Session = ctx.obj["db"]

    permission: Permissions | None = db.query(Permissions).filter(Permissions.name == permission_name).first()
    if not permission:
        click.echo(f"Permission '{permission_name}' not found.")
        sys.exit(4)

    # Check if any roles have this permission.
    if permission.roles:
        click.echo(f"Cannot delete permission '{permission_name}' because it is assigned to roles.")
        click.echo("To proceed, revoke the permission from roles first:")
        for role_perm in permission.roles:
            click.echo(f"  ctms-cli roles revoke {role_perm.role.name} {permission_name}")
        sys.exit(10)

    if not yes and not click.confirm(f"Are you sure you want to delete permission '{permission_name}'?"):
        click.echo("Operation cancelled.")
        return

    # Safe to delete the permission.
    db.delete(permission)
    db.commit()
    click.echo(f"✅ Successfully deleted permission '{permission_name}'.")
