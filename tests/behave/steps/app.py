import json
from difflib import ndiff
from uuid import UUID

from behave import fixture, given, step, then, use_fixture, when
from fastapi.testclient import TestClient
from pytest import fail
from sqlalchemy.orm.session import close_all_sessions

from ctms import config
from ctms.app import app, get_db
from ctms.crud import (
    create_amo,
    create_email,
    create_fxa,
    create_newsletter,
    create_vpn_waitlist,
)
from ctms.database import get_db_engine
from ctms.models import Base as ModelBase
from ctms.sample_data import SAMPLE_CONTACTS


@fixture
def with_postgres(context):
    try:
        settings = config.Settings()
        engine, SessionLocal = get_db_engine(settings)
        ModelBase.metadata.drop_all(bind=engine)
        ModelBase.metadata.create_all(bind=engine)
        yield SessionLocal
    finally:
        close_all_sessions()


@given("the TestClient is setup")
def setup_test_client(context):
    context.SessionLocal = use_fixture(with_postgres, context)

    def override_get_db():
        try:
            db = context.SessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    context.test_client = TestClient(app=app)
    context.post_body = None
    context.email_id = None


@given("the test contact {email_id} is setup")
def setup_test_contact(context, email_id):
    """TODO: Setup the test contact with a POST to /ctms"""
    assert UUID(email_id) in SAMPLE_CONTACTS

    contact = SAMPLE_CONTACTS.get(UUID(email_id))
    if not contact:
        raise Exception("Missing contact {}".format(email_id))
    if contact.email:
        create_email(context.SessionLocal(), contact.email)
    if contact.amo:
        create_amo(context.SessionLocal(), contact.amo)
    if contact.fxa:
        create_fxa(context.SessionLocal(), contact.fxa)
    if contact.newsletters:
        for newsletter in contact.newsletters:
            create_newsletter(context.SessionLocal(), newsletter)
    if contact.vpn_waitlist:
        create_vpn_waitlist(context.SessionLocal(), contact.vpn_waitlist)
    context.email_id = email_id


@given("the email_id {email_id}")
def set_email_id(context, email_id):
    context.email_id = email_id


@given("the desired endpoint {endpoint}")
def endpoint_setup(context, endpoint):
    if "(email_id)" in endpoint:
        assert context.email_id
        endpoint = endpoint.replace("(email_id)", context.email_id)
    context.test_endpoint = endpoint


@when("the user invokes the client via {http_method}")
def invokes_http_method(context, http_method):
    method = http_method.lower()
    assert method == "get"
    context.response = context.test_client.get(context.test_endpoint)


@then("the user expects the response to have a status of {status_code}")
def response_status(context, status_code):
    assert context.response.status_code == int(
        status_code
    ), f"Expected status code was {status_code}, got {context.response.status_code}"


@then("the response JSON is")
def response_json(context):
    text = context.text
    assert text
    expected_json = json.dumps(json.loads(text), sort_keys=True, indent=2) + "\n"
    actual_json = json.dumps(context.response.json(), sort_keys=True, indent=2) + "\n"
    diff = ndiff(
        expected_json.splitlines(keepends=True), actual_json.splitlines(keepends=True)
    )
    assert expected_json == actual_json, f"JSON mismatch: \n{''.join(diff)}"
