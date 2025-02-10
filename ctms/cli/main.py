import click

from ctms.cli.clients import clients_cli
from ctms.cli.permissions import permissions_cli
from ctms.cli.roles import roles_cli
from ctms.database import SessionLocal


@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """CTMS Command Line Interface."""
    with SessionLocal() as session:
        ctx.obj = {"db": session}


cli.add_command(clients_cli, name="clients")
cli.add_command(permissions_cli, name="permissions")
cli.add_command(roles_cli, name="roles")

if __name__ == "__main__":
    cli()
