Feature: FastAPI HTTP Application Behave Tests

  Background:
    Given the TestClient is setup


  Scenario: User wants to GET /
    Given the desired endpoint /
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200

  Scenario: User wants to GET /ctms/{contact_id}
    Given the desired endpoint /ctms/93db83d4-4119-4e0c-af87-a713786fa81d
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200

  Scenario: User fails to GET /ctms/{unknown contact_id}
    Given the desired endpoint /ctms/cad092ec-a71a-4df5-aa92-517959caeecb
    When the user invokes the client via GET
    Then the user expects the response to have a status of 404

  Scenario: User wants to GET /identity/{contact_id}
    Given the desired endpoint /identity/93db83d4-4119-4e0c-af87-a713786fa81d
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200

  Scenario: User fails to GET /identity/{unknown contact_id}
    Given the desired endpoint /identity/cad092ec-a71a-4df5-aa92-517959caeecb
    When the user invokes the client via GET
    Then the user expects the response to have a status of 404

  Scenario: User wants to GET /contact/main/{contact_id}
    Given the desired endpoint /contact/main/93db83d4-4119-4e0c-af87-a713786fa81d
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200

  Scenario: User fails to GET /contact/main/{unknown contact_id}
    Given the desired endpoint /contact/main/cad092ec-a71a-4df5-aa92-517959caeecb
    When the user invokes the client via GET
    Then the user expects the response to have a status of 404

  Scenario: User wants to GET /contact/amo/{contact_id}
    Given the desired endpoint /contact/amo/93db83d4-4119-4e0c-af87-a713786fa81d
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200

  Scenario: User fails to GET /contact/amo/{unknown contact_id}
    Given the desired endpoint /contact/amo/cad092ec-a71a-4df5-aa92-517959caeecb
    When the user invokes the client via GET
    Then the user expects the response to have a status of 404

  Scenario: User wants to GET /contact/cv/{contact_id}
    Given the desired endpoint /contact/cv/93db83d4-4119-4e0c-af87-a713786fa81d
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200

  Scenario: User fails to GET /contact/cv/{unknown contact_id}
    Given the desired endpoint /contact/cv/cad092ec-a71a-4df5-aa92-517959caeecb
    When the user invokes the client via GET
    Then the user expects the response to have a status of 404

  Scenario: User wants to GET /contact/fpn/{contact_id}
    Given the desired endpoint /contact/fpn/93db83d4-4119-4e0c-af87-a713786fa81d
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200

  Scenario: User fails to GET /contact/fpn/{unknown contact_id}
    Given the desired endpoint /contact/fpn/cad092ec-a71a-4df5-aa92-517959caeecb
    When the user invokes the client via GET
    Then the user expects the response to have a status of 404

  Scenario: User wants to GET /contact/fsa/{contact_id}
    Given the desired endpoint /contact/fsa/93db83d4-4119-4e0c-af87-a713786fa81d
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200

  Scenario: User fails to GET /contact/fsa/{unknown contact_id}
    Given the desired endpoint /contact/fsa/cad092ec-a71a-4df5-aa92-517959caeecb
    When the user invokes the client via GET
    Then the user expects the response to have a status of 404

  Scenario: User wants to GET /contact/fxa/{contact_id}
    Given the desired endpoint /contact/fxa/93db83d4-4119-4e0c-af87-a713786fa81d
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200

  Scenario: User fails to GET /contact/fxa/{unknown contact_id}
    Given the desired endpoint /contact/fxa/cad092ec-a71a-4df5-aa92-517959caeecb
    When the user invokes the client via GET
    Then the user expects the response to have a status of 404

  Scenario: Platform wants to GET /health
    Given the desired endpoint /health
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
