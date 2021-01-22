from behave import given, step, then, when
from fastapi.testclient import TestClient
from pytest import fail

from ctms_spike.app import app
from ctms_spike.models import APIRequest, ExampleAPIRequest


@given("the TestClient is setup")
def setup_test_client(context):
    context.test_client = TestClient(app=app)
    context.post_body = None


@given("the desired endpoint {endpoint}")
def endpoint_setup(context, endpoint):
    context.test_endpoint = endpoint


@when("the user invokes the client via {http_method}")
def invokes_http_method(context, http_method):
    method = http_method.lower()
    assert method == "get"
    context.response = context.test_client.get(context.test_endpoint)


@then("the user expects the response to have a status of {status_code}")
def response_status(context, status_code):
    assert context.response
    assert context.response.status_code == int(
        status_code
    ), "Expected status code not found"
