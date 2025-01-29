"""Unit tests for POST /ctms (create record)"""

import logging
from uuid import uuid4

from fastapi.encoders import jsonable_encoder

from ctms import models, schemas


def test_create_basic_no_email_id(client, dbsession):
    """Most straightforward contact creation succeeds when email_id is not a key."""

    contact_data = jsonable_encoder(schemas.ContactInSchema(email={"primary_email": "hello@example.com"}).model_dump(exclude_none=True))
    assert "email_id" not in contact_data["email"].keys()

    resp = client.post("/ctms", json=contact_data)
    assert resp.status_code == 201

    assert dbsession.get(models.Email, resp.json()["email"]["email_id"])


def test_create_basic_email_id_is_none(client, dbsession):
    """Most straightforward contact creation succeeds when email_id is not a key."""

    contact_data = jsonable_encoder(schemas.ContactInSchema(email={"primary_email": "hello@example.com"}))
    assert contact_data["email"]["email_id"] is None

    resp = client.post("/ctms", json=contact_data)
    assert resp.status_code == 201

    assert dbsession.get(models.Email, resp.json()["email"]["email_id"])


def test_create_basic_with_id(client, dbsession, email_factory):
    """Most straightforward contact creation succeeds when email_id is specified."""
    provided_email_id = str(uuid4())

    contact_data = jsonable_encoder(schemas.ContactInSchema(email={"email_id": provided_email_id, "primary_email": "hello@example.com"}))
    assert contact_data["email"]["email_id"] == provided_email_id

    resp = client.post("/ctms", json=contact_data)
    assert resp.status_code == 201

    assert dbsession.get(models.Email, provided_email_id)


def test_create_basic_idempotent(client, dbsession):
    """Creating a contact works across retries."""

    contact_data = jsonable_encoder(schemas.ContactInSchema(email={"primary_email": "hello@example.com"}))

    resp = client.post("/ctms", json=contact_data)
    assert resp.status_code == 201
    assert dbsession.get(models.Email, resp.json()["email"]["email_id"])

    resp = client.post("/ctms", json=resp.json())
    assert resp.status_code == 200
    assert dbsession.get(models.Email, resp.json()["email"]["email_id"])
    assert dbsession.query(models.Email).count() == 1


def test_create_basic_with_id_collision(client, email_factory):
    """Creating a contact with the same id but different data fails."""

    contact_data = jsonable_encoder(schemas.ContactInSchema(email={"primary_email": "hello@example.com", "email_lang": "en"}))

    resp = client.post("/ctms", json=contact_data)
    assert resp.status_code == 201

    modified_data = resp.json()
    modified_data["email"]["email_lang"] = "XX"

    resp = client.post("/ctms", json=modified_data)
    assert resp.status_code == 409


def test_create_basic_with_email_collision(client, email_factory):
    """Creating a contact with diff ids but same email fails.
    We override the basket token so that we know we're not colliding on that here.
    See test_create_basic_with_email_collision below for that check
    """

    colliding_email = "foo@example.com"
    email_factory(primary_email=colliding_email)

    contact_data = jsonable_encoder(schemas.ContactInSchema(email={"primary_email": colliding_email}))

    resp = client.post("/ctms", json=contact_data)
    assert resp.status_code == 409


def test_create_basic_with_basket_collision(client, email_factory):
    """Creating a contact with diff ids but same basket token fails.
    We override the email so that we know we're not colliding on that here.
    See other test for that check
    """
    colliding_basket_token = str(uuid4())
    email_factory(basket_token=colliding_basket_token)

    contact_data = jsonable_encoder(
        schemas.ContactInSchema(
            email={
                "primary_email": "hello@example.com",
                "basket_token": colliding_basket_token,
            }
        )
    )

    resp = client.post("/ctms", json=contact_data)
    assert resp.status_code == 409


def test_default_is_not_written(client, dbsession):
    """Schema defaults are not written to the database"""

    contact = schemas.ContactInSchema(
        email=schemas.EmailInSchema(primary_email="hello@example.com"),
        fxa=schemas.FirefoxAccountsInSchema(),
        mofo=schemas.MozillaFoundationInSchema(),
        amo=schemas.AddOnsInSchema(),
        newsletters=[],
        waitlists=[],
    )
    for attr in ["amo", "fxa", "mofo"]:
        assert getattr(contact, attr).is_default()

    resp = client.post("/ctms", json=jsonable_encoder(contact.model_dump()))
    assert resp.status_code == 201

    for model in [
        models.Newsletter,
        models.Waitlist,
        models.FirefoxAccount,
        models.AmoAccount,
        models.MozillaFoundationContact,
    ]:
        assert dbsession.query(model).count() == 0


def test_post_example_contact(client, example_contact_data):
    """We can POST the example contact data that we include in our Swagger docs"""

    resp = client.post("/ctms", json=jsonable_encoder(example_contact_data))
    assert resp.status_code == 201


def test_create_with_non_json_is_error(client, caplog):
    """When non-JSON is posted /ctms, a 422 is returned"""
    data = b"this is not JSON"
    with caplog.at_level(logging.INFO):
        resp = client.post("/ctms", content=data)

    assert resp.status_code == 422
    assert resp.json()["detail"][0]["msg"] == "JSON decode error"
    assert len(caplog.records) == 1
    assert caplog.records[0].code == 422
