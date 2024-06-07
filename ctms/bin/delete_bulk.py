#!/usr/bin/env python
import click
from pydantic import BaseSettings, PostgresDsn
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ctms.crud import delete_contact, get_contacts_by_any_id


class DBSettings(BaseSettings):
    db_url: PostgresDsn

    class Config:
        env_prefix = "ctms_"


@click.command()
@click.option("--email")
@click.option("--email-file", type=click.File("r"))
def delete(email, email_file):
    """delete single contact or a list of contacts from ctms"""
    settings = DBSettings()

    to_be_deleted = []

    if email_file:
        for line in email_file.readlines():
            to_be_deleted.append(line.rstrip())

    if email:
        to_be_deleted.append(email)

    engine = create_engine(settings.db_url)
    with Session(engine) as dbsession:
        for item in to_be_deleted:
            contacts = get_contacts_by_any_id(dbsession, primary_email=item.lower())
            if not contacts:
                print(f"{item} not found in CTMS")

            for contact in contacts:
                delete_contact(db=dbsession, email_id=contact.email.email_id)

                email_id = contact["email_id"]
                msg = f"DELETING {item} (ctms id: {email_id})."
                if contact["fxa_id"]:
                    msg += " fxa: YES."
                if contact["mofo_contact_id"]:
                    msg += " mofo: YES."
                print(msg)


if __name__ == "__main__":
    delete()  # pylint: disable=no-value-for-parameter
