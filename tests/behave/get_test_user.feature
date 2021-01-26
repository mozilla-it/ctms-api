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
        "amo_id": null,
        "amo_display_name": null,
        "amo_homepage": null,
        "amo_last_login": null,
        "amo_location": null,
        "amo_user": false,
        "country": "us",
        "created_date": "2014-01-22T15:24:00.000+0000",
        "cv_created_at": null,
        "cv_days_interval": null,
        "cv_first_contribution_date": null,
        "cv_goal_reached_at": null,
        "cv_last_active_date": null,
        "cv_two_day_streak": null,
        "email": "ctms-user@example.com",
        "fxa_id": null,
        "fxa_primary_email": null,
        "fxa_create_date": null,
        "fxa_deleted": null,
        "fxa_lang": null,
        "fxa_service": null,
        "id": "001A000001aABcDEFG",
        "lang": "en",
        "last_modified_date": "2020-01-22T15:24:00.000+0000",
        "optin": true,
        "optout": false,
        "payee_id": null,
        "postal_code": "666",
        "reason": null,
        "record_type": "0124A0000001aABCDE",
        "token": "142e20b6-1ef5-43d8-b5f4-597430e956d7",
        "source_url": null,
        "format": null,
        "payee_id": null,
        "first_name": null,
        "last_name": null,
        "fpn_country": null,
        "fpn_platform": null,
        "fsa_allow_share": null,
        "fsa_city": null,
        "fsa_current_status": null,
        "fsa_grad_year": null,
        "fsa_major": null,
        "fsa_school": null,
        "status": "ok",
        "newsletters": [
            "app-dev",
            "maker-party",
            "mozilla-foundation",
            "mozilla-learning-network"
        ]
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
        "postal_code": "666",
        "cv_created_at": null,
        "cv_days_interval": null,
        "cv_first_contribution_date": null,
        "cv_goal_reached_at": null,
        "cv_last_active_date": null,
        "cv_two_day_streak": null,
        "email": "ctms-user@example.com",
        "token": "142e20b6-1ef5-43d8-b5f4-597430e956d7",
        "country": "us",
        "created_date": "2014-01-22T15:24:00.000+0000",
        "lang": "en",
        "last_modified_date": "2020-01-22T15:24:00.000+0000",
        "optin": true,
        "optout": false,
        "reason": null,
        "record_type": "0124A0000001aABCDE",
        "id": "001A000001aABcDEFG"
      }
      """

  Scenario: User wants to GET /contact/amo/(contact_id)
    Given the desired endpoint /contact/amo/(contact_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "amo_display_name": null,
        "amo_homepage": null,
        "amo_last_login": null,
        "amo_location": null,
        "amo_user": false
      }
      """

  Scenario: User wants to GET /contact/cv/(contact_id)
    Given the desired endpoint /contact/cv/(contact_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "source_url": null,
        "id": "001A000001aABcDEFG",
        "format": null,
        "payee_id": null,
        "first_name": null,
        "last_name": null
      }
      """

  Scenario: User wants to GET /contact/fpn/(contact_id)
    Given the desired endpoint /contact/fpn/(contact_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "fpn_country": null,
        "fpn_platform": null
      }
      """

  Scenario: User wants to GET /contact/fsa/(contact_id)
    Given the desired endpoint /contact/fsa/(contact_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "fsa_allow_share": null,
        "fsa_city": null,
        "fsa_current_status": null,
        "fsa_grad_year": null,
        "fsa_major": null,
        "fsa_school": null
      }
      """

  Scenario: User wants to GET /contact/fxa/(contact_id)
    Given the desired endpoint /contact/fxa/(contact_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "fxa_id": null,
        "fxa_primary_email": null,
        "fxa_create_date": null,
        "fxa_deleted": null,
        "fxa_lang": null,
        "fxa_service": null
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
