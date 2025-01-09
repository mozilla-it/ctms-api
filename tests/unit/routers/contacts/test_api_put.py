"""Unit tests for PUT /ctms/{email_id} (Create or update)"""

import logging
from uuid import uuid4

import pytest
from fastapi.encoders import jsonable_encoder

from ctms import models
from ctms.schemas import ContactPutSchema, EmailInSchema


def test_create_or_update_basic_id_is_different(client):
    """This should fail since we require an email_id to PUT"""

    contact = ContactPutSchema(
        email={"email_id": str(uuid4()), "primary_email": "hello@example.com"}
    )
    # This id is different from the one in the contact
    resp = client.put(
        f"/ctms/{str(uuid4())}",
        content=contact.model_dump_json(),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"] == "email_id in path must match email_id in contact"


def test_create_or_update_basic_id_is_none(client):
    """This should fail since we require an email_id to PUT"""

    contact_data = ContactPutSchema.model_construct(
        EmailInSchema(primary_email="foo@example.com")
    )
    resp = client.put(f"/ctms/{str(uuid4())}", json=jsonable_encoder(contact_data))
    assert resp.status_code == 422


def test_create_or_update_basic_empty_db(client):
    """Most straightforward contact creation succeeds when there is no collision"""
    email_id = str(uuid4())
    contact_data = ContactPutSchema(
        email={"email_id": email_id, "primary_email": "foo@example.com"}
    )
    resp = client.put(f"/ctms/{email_id}", json=jsonable_encoder(contact_data))
    assert resp.status_code == 201


def test_create_or_update_identical(client, dbsession):
    """Writing the same thing twice works both times"""

    email_id = str(uuid4())
    contact_data = ContactPutSchema(
        email={"email_id": email_id, "primary_email": "foo@example.com"}
    )

    resp = client.put(f"/ctms/{email_id}", json=jsonable_encoder(contact_data))
    assert resp.status_code == 201
    assert dbsession.get(models.Email, email_id)

    resp = client.put(f"/ctms/{email_id}", json=jsonable_encoder(contact_data))
    assert resp.status_code == 201
    assert dbsession.get(models.Email, email_id)
    assert dbsession.query(models.Email).count() == 1


def test_create_or_update_change_primary_email(client, email_factory, dbsession):
    """We can update a primary_email given a ctms ID"""

    email_id = str(uuid4())
    email_factory(email_id=email_id, primary_email="foo@example.com")

    contact_data = ContactPutSchema(
        email={"email_id": email_id, "primary_email": "bar@example.com"}
    )

    resp = client.put(f"/ctms/{email_id}", json=jsonable_encoder(contact_data))
    assert resp.status_code == 201
    assert resp.json()["email"]["primary_email"] == "bar@example.com"
    assert dbsession.get(models.Email, email_id).primary_email == "bar@example.com"
    assert dbsession.query(models.Email).count() == 1


def test_create_or_update_change_basket_token(client, email_factory, dbsession):
    """We can update a basket_token given a ctms ID"""

    email_id = str(uuid4())
    email_factory(
        email_id=email_id, primary_email="foo@example.com", basket_token=uuid4()
    )
    new_basket_token = str(uuid4())

    contact_data = ContactPutSchema(
        email={
            "email_id": email_id,
            "primary_email": "foo@example.com",
            "basket_token": new_basket_token,
        }
    )
    resp = client.put(f"/ctms/{email_id}", json=jsonable_encoder(contact_data))

    assert resp.status_code == 201
    assert resp.json()["email"]["basket_token"] == new_basket_token
    assert dbsession.get(models.Email, email_id).basket_token == new_basket_token
    assert dbsession.query(models.Email).count() == 1


def test_create_or_update_with_basket_collision(client, email_factory):
    """Updating a contact with diff ids but same basket token fails."""

    existing_basket_token = str(uuid4())
    email_factory(basket_token=existing_basket_token)

    new_contact_email_id = str(uuid4())
    contact_data = ContactPutSchema(
        email={
            "email_id": new_contact_email_id,
            "primary_email": "foo@example.com",
            "basket_token": existing_basket_token,
        }
    )
    resp = client.put(
        f"/ctms/{new_contact_email_id}", json=jsonable_encoder(contact_data)
    )

    assert resp.status_code == 409


def test_create_or_update_with_email_collision(client, email_factory):
    """Updating a contact with diff ids but same email fails."""

    existing_email_address = "foo@example.com"
    email_factory(email_id=str(uuid4()), primary_email=existing_email_address)

    new_contact_email_id = str(uuid4())
    contact_data = ContactPutSchema(
        email={
            "email_id": new_contact_email_id,
            "primary_email": existing_email_address,
        }
    )
    resp = client.put(
        f"/ctms/{new_contact_email_id}", json=jsonable_encoder(contact_data)
    )

    assert resp.status_code == 409


def test_put_with_not_json_is_error(client, caplog):
    """Calling PUT with a text body is a 422 validation error."""
    email_id = str(uuid4())
    data = b"make a contact please"
    with caplog.at_level(logging.INFO):
        resp = client.put(f"/ctms/{email_id}", content=data)
    assert resp.status_code == 422
    assert resp.json()["detail"][0]["msg"] == "JSON decode error"
    assert len(caplog.records) == 1
    assert caplog.records[0].code == 422
