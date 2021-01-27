Feature: Getting the test user's information works

  Background:
    Given the TestClient is setup
    And the test contact 93db83d4-4119-4e0c-af87-a713786fa81d is setup

  Scenario: User wants to GET /ctms/(contact_id)
    Given the desired endpoint /ctms/(contact_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "id": "93db83d4-4119-4e0c-af87-a713786fa81d",
        "amo": {
          "display_name": null,
          "homepage": null,
          "id": null,
          "last_login": null,
          "location": null,
          "user": false
        },
        "contact": {
          "country": "us",
          "created_date": "2014-01-22T15:24:00+00:00",
          "email": "ctms-user@example.com",
          "first_name": null,
          "format": "H",
          "id": "001A000001aABcDEFG",
          "lang": "en",
          "last_modified_date": "2020-01-22T15:24:00+00:00",
          "last_name": "_",
          "optin": true,
          "optout": false,
          "payee_id": null,
          "postal_code": "666",
          "reason": null,
          "record_type": "0124A0000001aABCDE",
          "token": "142e20b6-1ef5-43d8-b5f4-597430e956d7",
          "source_url": null
        },
        "cv": {
          "created_at": null,
          "days_interval": null,
          "first_contribution_date": null,
          "goal_reached_at": null,
          "last_active_date": null,
          "two_day_streak": null
        },
        "fpn": {
          "country": null,
          "platform": null
        },
        "fsa": {
          "allow_share": null,
          "city": null,
          "current_status": null,
          "grad_year": null,
          "major": null,
          "school": null
        },
        "fxa": {
          "create_date": null,
          "deleted": null,
          "id": null,
          "lang": null,
          "primary_email": null,
          "service": null
        },
        "newsletters": [
            "app-dev",
            "maker-party",
            "mozilla-foundation",
            "mozilla-learning-network"
        ],
        "status": "ok"
      }
      """

  Scenario: User wants to GET /identity/(contact_id)
    Given the desired endpoint /identity/(contact_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "id": "001A000001aABcDEFG",
        "amo_id": null,
        "fxa_id": null,
        "fxa_primary_email": null,
        "token": "142e20b6-1ef5-43d8-b5f4-597430e956d7"
      }
      """

  Scenario: User wants to GET /contact/main/(contact_id)
    Given the desired endpoint /contact/main/(contact_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "country": "us",
        "created_date": "2014-01-22T15:24:00+00:00",
        "email": "ctms-user@example.com",
        "first_name": null,
        "format": "H",
        "id": "001A000001aABcDEFG",
        "lang": "en",
        "last_modified_date": "2020-01-22T15:24:00+00:00",
        "last_name": "_",
        "optin": true,
        "optout": false,
        "payee_id": null,
        "postal_code": "666",
        "reason": null,
        "record_type": "0124A0000001aABCDE",
        "source_url": null,
        "token": "142e20b6-1ef5-43d8-b5f4-597430e956d7"
      }
      """

  Scenario: User wants to GET /contact/amo/(contact_id)
    Given the desired endpoint /contact/amo/(contact_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "display_name": null,
        "homepage": null,
        "id": null,
        "last_login": null,
        "location": null,
        "user": false
      }
      """

  Scenario: User wants to GET /contact/cv/(contact_id)
    Given the desired endpoint /contact/cv/(contact_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "created_at": null,
        "days_interval": null,
        "first_contribution_date": null,
        "goal_reached_at": null,
        "last_active_date": null,
        "two_day_streak": null
      }
      """

  Scenario: User wants to GET /contact/fpn/(contact_id)
    Given the desired endpoint /contact/fpn/(contact_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "country": null,
        "platform": null
      }
      """

  Scenario: User wants to GET /contact/fsa/(contact_id)
    Given the desired endpoint /contact/fsa/(contact_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "allow_share": null,
        "city": null,
        "current_status": null,
        "grad_year": null,
        "major": null,
        "school": null
      }
      """

  Scenario: User wants to GET /contact/fxa/(contact_id)
    Given the desired endpoint /contact/fxa/(contact_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "create_date": null,
        "deleted": null,
        "id": null,
        "lang": null,
        "primary_email": null,
        "service": null
      }
      """

  Scenario Outline: Unknown contacts IDs are not found
    Given the contact_id cad092ec-a71a-4df5-aa92-517959caeecb
    And the desired endpoint /<endpoint_prefix>/(contact_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 404
    And the response JSON is
    """
    {
      "detail": "Contact not found"
    }
    """

    Examples: Endpoints
      | endpoint_prefix |
      | ctms            |
      | identity        |
      | contact/main    |
      | contact/amo     |
      | contact/cv      |
      | contact/fpn     |
      | contact/fsa     |
      | contact/fxa     |
