#!/usr/bin/env python

import sys

import click
from pydantic_settings import BaseSettings, SettingsConfigDict
from requests import Session
from requests.auth import HTTPBasicAuth


class Settings(BaseSettings):
    api_url: str = "http://127.0.0.1:8000"
    client_id: str
    client_secret: str
    session: Session
    model_config = SettingsConfigDict(env_prefix="ctms_")


@click.group()
@click.pass_context
def cli(ctx):
    """Delete a list of contacts"""
    ctx.obj = Settings(session=Session())

    response = ctx.obj.session.post(
        f"{ctx.obj.api_url}/token",
        auth=HTTPBasicAuth(ctx.obj.client_id, ctx.obj.client_secret),
    )

    if not response.ok:
        print(f"{response.status_code}: {response.reason}", file=sys.stderr)

    else:
        data = response.json()
        token = data["access_token"]

        ctx.obj.session.headers.update({"Authorization": f"Bearer {token}"})


@cli.command()
@click.option("--email")
@click.option("--email-file", type=click.File("r"))
@click.pass_obj
def delete(obj, email, email_file):
    """delete single contact or a list of contacts from ctms"""
    to_be_deleted = []

    if email_file:
        for line in email_file.readlines():
            to_be_deleted.append(line.rstrip())

    if email:
        to_be_deleted.append(email)

    for item in to_be_deleted:
        response = obj.session.delete(f"{obj.api_url}/ctms/{item}")

        if not response.ok:
            if response.status_code == 404:
                print(f"{item} not found in CTMS")

            else:
                print(f"{response.status_code}: {response.reason}", file=sys.stderr)

        else:
            data = response.json()

            for contact in data:
                email_id = contact["email_id"]
                msg = f"DELETING {item} (ctms id: {email_id})."

                if contact["fxa_id"]:
                    msg += " fxa: YES."

                if contact["mofo_contact_id"]:
                    msg += " mofo: YES."

                print(msg)


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
