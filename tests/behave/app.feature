Feature: FastAPI HTTP Application Behave Tests

  Background:
    Given the TestClient is setup


  Scenario: User wants to GET /
    Given the desired endpoint /
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200

  Scenario: User wants to GET /identity/{contact_id}
    Given the desired endpoint /identity/93db83d4-4119-4e0c-af87-a713786fa81d
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200

  Scenario: User wants to GET /contact/main/{contact_id}
    Given the desired endpoint /contact/main/93db83d4-4119-4e0c-af87-a713786fa81d
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200

  Scenario: Platform wants to GET /health
    Given the desired endpoint /health
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
