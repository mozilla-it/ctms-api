from behave import given, step, then, when
from fastapi.testclient import TestClient
from pytest import fail

from containerized_microservice_template.app import app
from containerized_microservice_template.models import APIRequest, ExampleAPIRequest


@given("the TestClient is setup")
def setup_test_client(context):
    context.test_client = TestClient(app=app)
    context.post_body = None


@given("the desired endpoint {endpoint}")
def endpoint_setup(context, endpoint):
    context.test_endpoint = endpoint


@step("the request body is a {request_model} model")
def request_body_provided(context, request_model):
    if "apirequest" == request_model.lower():
        context.post_body = APIRequest().dict()
    elif "exampleapirequest" == request_model.lower():
        context.post_body = ExampleAPIRequest(name="test", type="example").dict()
    elif "json" == request_model.lower():
        context.post_body = "{}"


@when("the user invokes the client via {http_method}")
def invokes_http_method(context, http_method):
    if "get" == http_method.lower():
        context.response = context.test_client.get(context.test_endpoint)
    elif "post" == http_method.lower():
        context.response = context.test_client.post(
            context.test_endpoint, json=context.post_body
        )


@then("the user expects the response to have a status of {status_code}")
def response_status(context, status_code):
    if context.response is None:
        fail()

    assert context.response.status_code == int(
        status_code
    ), "Expected status code not found"
