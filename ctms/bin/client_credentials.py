#!/usr/bin/env python3
"""Generate OAuth2 client credentials."""

import argparse
import re
from secrets import token_urlsafe

from ctms import config
from ctms.auth import hash_password
from ctms.crud import create_api_client, get_api_client_by_id
from ctms.database import get_db_engine
from ctms.schemas import ApiClientSchema


def create_secret():
    """Generate a new secret."""
    return "secret_" + token_urlsafe(32)


def create_client(db, client_id, email, enabled=True):
    """Return a new OAuth2 client_id and client_secret."""
    api_client = ApiClientSchema(client_id=client_id, email=email, enabled=enabled)
    secret = create_secret()
    create_api_client(db, api_client, secret)
    db.flush()
    return (client_id, secret)


def update_client(db, client, email=None, enabled=None, new_secret=None):
    """Update an existing OAuth2 client."""
    assert not (email is None and enabled is None and new_secret is None)
    if email is not None:
        client.email = email
    if enabled is not None:
        client.enabled = enabled
    if new_secret:
        client.hashed_secret = hash_password(new_secret)
    db.flush()


def print_new_credentials(
    client_id,
    client_secret,
    settings,
    sample_email="contact@example.com",
    sample_token="a_very_long_base64_string",
    enabled=True,
):

    print(
        f"""\
Your OAuth2 client credentials are:

      client_id: {client_id}
  client_secret: {client_secret}
"""
    )

    if enabled:
        print(
            f"""\
You can generate a token with an Authentication header:

  curl --user {client_id}:{client_secret} -F grant_type=client_credentials {settings.server_prefix}/token

or passing credentials in the form body:

  curl -v -F client_id={client_id} -F client_secret={client_secret} -F grant_type=client_credentials {settings.server_prefix}/token

The JSON response will have an access token, such as:

  {{
    "access_token": "{sample_token}",
    "token_type": "bearer",
    "expires_in": {int(settings.token_expiration.total_seconds())}
  }}

This can be used to access the API, such as:

  curl --oauth2-bearer {sample_token} {settings.server_prefix}/ctms?primary_email={sample_email}

"""
        )
    else:
        print(
            "These credentials are currently disabled, and can not be used to get an OAuth2 access token."
        )


def main(db, settings, test_args=None):
    """
    Process the command line and create or update client credentials

    db - the database session
    settings - the application settings
    test_args - command line arguments for testing, or None to read from sys.argv

    Return is 0 for success, 1 for failure, appropriate for sys.exit()
    """
    parser = argparse.ArgumentParser(description="Create or update client credentials.")
    parser.add_argument("name", help="short name of the client")
    parser.add_argument("-e", "--email", help="contact email for the client")
    parser.add_argument(
        "--enable", action="store_true", help="enable a disabled client"
    )
    parser.add_argument(
        "--disable", action="store_true", help="disable a new or enabled client"
    )
    parser.add_argument(
        "--rotate-secret", action="store_true", help="generate a new secret key"
    )

    args = parser.parse_args(args=test_args)
    name = args.name
    email = args.email
    enable = args.enable
    disable = args.disable
    rotate = args.rotate_secret

    if not re.match(r"^[-_.a-zA-Z0-9]*$", name):
        print(
            f"name '{name}' should have only alphanumeric characters, '-', '_', or '.'"
        )
        return 1

    if enable and disable:
        print(f"Can only pick one of --enable and --disable")
        return 1

    if name.startswith("id_"):
        client_id = name
    else:
        client_id = f"id_{name}"
    existing = get_api_client_by_id(db, client_id)
    if existing:
        if disable and existing.enabled:
            enabled = False
        elif enable and not existing.enabled:
            enabled = True
        else:
            enabled = None

        if rotate:
            new_secret = create_secret()
        else:
            new_secret = None

        if new_secret is None and enabled is None and email in (None, existing.email):
            print(f"Nothing to change for existing credentials for {name}.")
            return 0

        update_client(db, existing, email=email, enabled=enabled, new_secret=new_secret)
        db.commit()
        if new_secret:
            print_new_credentials(
                existing.client_id,
                new_secret,
                settings,
                sample_email=email,
                enabled=enabled,
            )
        else:
            print(f"Credentials for {name} are updated.")
    else:
        if email is None:
            print("email is required for new credentials.")
            return 1

        enabled = not disable
        client_id, client_secret = create_client(db, client_id, email, enabled)
        db.commit()
        print_new_credentials(
            client_id, client_secret, settings, sample_email=email, enabled=enabled
        )
    return 0


if __name__ == "__main__":
    import sys

    # Get the database
    settings = config.Settings()
    engine, session_factory = get_db_engine(settings)
    db = session_factory()

    try:
        ret = main(db, settings)
    finally:
        db.close()

    sys.exit(ret)
