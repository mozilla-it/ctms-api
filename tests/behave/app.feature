Feature: FastAPI HTTP Application Behave Tests

  Background:
    Given the TestClient is setup


  Scenario: User wants to GET /
    Given the desired endpoint /
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200

  Scenario: User wants to POST to /api/PATH?one=1&two=true, with body
    Given the desired endpoint /api/PATH?one=1&two=true
    And the request body is a JSON model
    When the user invokes the client via POST
    Then the user expects the response to have a status of 200


  Scenario: User wants to POST /api, with body
    Given the desired endpoint /api
    And the request body is a APIRequest model
    When the user invokes the client via POST
    Then the user expects the response to have a status of 200

  Scenario: User wants to POST to /api/PATH?one=1&two=true, missing body
    Given the desired endpoint /api/PATH?one=1&two=true
    When the user invokes the client via POST
    Then the user expects the response to have a status of 422


  Scenario: User wants to POST /api, missing body
    Given the desired endpoint /api
    When the user invokes the client via POST
    Then the user expects the response to have a status of 422

# TODO: Remove the Example below ----
  Scenario: User wants to POST /example, with body
    Given the desired endpoint /example
    And the request body is a ExampleAPIRequest model
    When the user invokes the client via POST
    Then the user expects the response to have a status of 200

  Scenario: User wants to POST /example, missing body
    Given the desired endpoint /example
    When the user invokes the client via POST
    Then the user expects the response to have a status of 422
# TODO: Remove the Example above ----
