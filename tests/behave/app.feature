Feature: The basic FastAPI HTTP Application works

  Background:
    Given the TestClient is setup

  Scenario: User wants to GET /
    Given the desired endpoint /
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200

  Scenario: Platform wants to GET /health
    Given the desired endpoint /health
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
