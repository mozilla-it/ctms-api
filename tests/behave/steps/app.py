import json
from difflib import ndiff

from behave import given, step, then, when
from fastapi.testclient import TestClient
from pytest import fail

from ctms.app import app


@given("the TestClient is setup")
def setup_test_client(context):
    context.test_client = TestClient(app=app)
    context.post_body = None
    context.contact_id = None


@given("the test contact {contact_id} is setup")
def setup_test_contact(context, contact_id):
    """TODO: Setup the test contact with a POST to /ctms"""
    assert contact_id == "93db83d4-4119-4e0c-af87-a713786fa81d"
    context.contact_id = contact_id


@given("the contact_id {contact_id}")
def contact_id_setup(context, contact_id):
    context.contact_id = contact_id


@given("the desired endpoint {endpoint}")
def endpoint_setup(context, endpoint):
    if "(contact_id)" in endpoint:
        assert context.contact_id
        endpoint = endpoint.replace("(contact_id)", context.contact_id)
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
