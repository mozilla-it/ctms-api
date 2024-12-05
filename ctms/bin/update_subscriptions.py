#!/usr/bin/env python

import csv
import sys
from collections import defaultdict

import click
import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ctms_")
    api_url: str = "http://127.0.0.1:8000"
    client_id: str
    client_secret: str


@click.command()
@click.argument("csv_file", type=click.File("r"))
def cli(csv_file):
    """
    Update a user's subscriptions

    The expected file is of the format:

        email_id: UUID4, name: str (newsletter slug), subscribed: bool

    The script will output all email_ids with either 404 or a colon-separated list of currently
    subscribed newsletters. E.g.:

        <email_id>,slug1;slug2
        <email_id>,404

    """

    # Set up the bearer token.
    config = Settings()
    resp = httpx.post(
        f"{config.api_url}/token",
        auth=httpx.BasicAuth(config.client_id, config.client_secret),
    ).raise_for_status()

    client = httpx.Client(
        headers={"Authorization": f"Bearer {resp.json()['access_token']}"}
    )

    # Process input CSV file.
    reader = csv.DictReader(csv_file)

    grouped_data = defaultdict(list)
    for row in reader:
        email_id = row["email_id"]
        grouped_data[email_id].append(
            {
                "name": row["name"],
                "subscribed": row["subscribed"].lower() == "true",
            }
        )

    # Send data to the API
    for email_id, newsletters in grouped_data.items():
        payload = {"newsletters": newsletters}

        try:
            resp = client.patch(f"{config.api_url}/ctms/{email_id}", json=payload)

            if not resp.status_code == 200:
                if resp.status_code == 404:
                    print(f"{email_id},404")
                else:
                    resp.raise_for_status()

            else:
                data = resp.json()
                subscribed = ";".join(
                    [n["name"] for n in data["newsletters"] if n["subscribed"]]
                )
                output = f"{data["email"]["email_id"]},{subscribed}"
                print(output)

        except Exception as e:
            print(f"ERROR: email_id: {email_id}, error: {e}")


if __name__ == "__main__":
    cli()
