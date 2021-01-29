Feature: Getting the test user's information works

  Background:
    Given the TestClient is setup
    And the test contact 93db83d4-4119-4e0c-af87-a713786fa81d is setup
    And the test contact 67e52c77-950f-4f28-accb-bb3ea1a2c51a is setup

  Scenario: User wants to get full contact info for the minimal contact
    Given the contact_id 93db83d4-4119-4e0c-af87-a713786fa81d
    And the desired endpoint /ctms/(contact_id)
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

  Scenario: User wants to get full contact info for the maximal contact
    Given the contact_id 67e52c77-950f-4f28-accb-bb3ea1a2c51a
    And the desired endpoint /ctms/(contact_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "id": "67e52c77-950f-4f28-accb-bb3ea1a2c51a",
        "amo": {
          "display_name": "#1 Mozilla Fan",
          "homepage": "https://www.mozilla.org/en-US/firefox/new/",
          "id": 123,
          "last_login": "2020-01-27T14:21:00+00:00",
          "location": "The Internet",
          "user": true
        },
        "contact": {
          "country": "ca",
          "created_date": "2010-01-01T08:04:00+00:00",
          "email": "mozilla-fan@example.com",
          "first_name": "Fan of",
          "format": "H",
          "id": "001A000001aMozFan",
          "lang": "fr",
          "last_modified_date": "2020-01-28T14:50:00+00:00",
          "last_name": "Mozilla",
          "optin": true,
          "optout": false,
          "payee_id": "cust_012345",
          "postal_code": "H2L",
          "reason": "done with this mailing list",
          "record_type": "0124A0000001aABCDE",
          "source_url": "https://developer.mozilla.org/fr/",
          "token": "d9ba6182-f5dd-4728-a477-2cc11bf62b69"
        },
        "cv": {
          "created_at": "2020-10-14T16:05:21.423000+00:00",
          "days_interval": 12,
          "first_contribution_date": "2020-10-15T10:07:00+00:00",
          "goal_reached_at": "2020-11-02T11:15:19.008000+00:00",
          "last_active_date": "2021-01-10T11:15:19.008000+00:00",
          "two_day_streak": true
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
            "about-addons",
            "about-mozilla",
            "ambassadors",
            "app-dev",
            "common-voice",
            "connected-devices",
            "developer-events",
            "firefox-accounts-journey",
            "firefox-desktop",
            "firefox-friends",
            "firefox-ios",
            "firefox-os",
            "firefox-welcome",
            "game-developer-conference",
            "get-involved",
            "guardian-vpn-waitlist",
            "hubs",
            "inhuman",
            "internet-health-report",
            "ios-beta-test-flight",
            "knowledge-is-power",
            "maker-party",
            "member-comm",
            "member-idealo",
            "member-tech",
            "member-tk",
            "miti",
            "mixed-reality",
            "mobile",
            "mozilla-and-you",
            "mozilla-fellowship-awardee-alumni",
            "mozilla-festival",
            "mozilla-foundation",
            "mozilla-general",
            "mozilla-leadership-network",
            "mozilla-learning-network",
            "mozilla-phone",
            "mozilla-technology",
            "mozilla-welcome",
            "mozillians-nda",
            "open-innovation-challenge",
            "open-leadership",
            "shape-web",
            "take-action-for-the-internet",
            "test-pilot",
            "view-source-conference-global",
            "view-source-conference-north-america",
            "webmaker"
        ],
        "status": "ok"
      }
      """

  Scenario: User wants to read identity data for the minimal contact
    Given the contact_id 93db83d4-4119-4e0c-af87-a713786fa81d
    And the desired endpoint /identity/(contact_id)
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

  Scenario: User wants to read identity data for the maximal contact
    Given the contact_id 67e52c77-950f-4f28-accb-bb3ea1a2c51a
    And the desired endpoint /identity/(contact_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "amo_id": 123,
        "fxa_id": null,
        "fxa_primary_email": null,
        "id": "001A000001aMozFan",
        "token": "d9ba6182-f5dd-4728-a477-2cc11bf62b69"
      }
      """

  Scenario: User wants to read the main contact data for the minimal contact
    Given the contact_id 93db83d4-4119-4e0c-af87-a713786fa81d
    And the desired endpoint /contact/main/(contact_id)
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

  Scenario: User wants to read the AMO data for the minimal contact
    Given the contact_id 93db83d4-4119-4e0c-af87-a713786fa81d
    And the desired endpoint /contact/amo/(contact_id)
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

  Scenario: User wants to read the CV data for the minimal contact
    Given the contact_id 93db83d4-4119-4e0c-af87-a713786fa81d
    And the desired endpoint /contact/cv/(contact_id)
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

  Scenario: User wants to read the FPN data for the minimal contact
    Given the contact_id 93db83d4-4119-4e0c-af87-a713786fa81d
    And the desired endpoint /contact/fpn/(contact_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "country": null,
        "platform": null
      }
      """

  Scenario: User wants to read the FSA data for the minimal contact
    Given the contact_id 93db83d4-4119-4e0c-af87-a713786fa81d
    And the desired endpoint /contact/fsa/(contact_id)
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

  Scenario: User wants to read the FXA data for the minimal contact
    Given the contact_id 93db83d4-4119-4e0c-af87-a713786fa81d
    And the desired endpoint /contact/fxa/(contact_id)
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
      "detail": "Unknown contact_id"
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
