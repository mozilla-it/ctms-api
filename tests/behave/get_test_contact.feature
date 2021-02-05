Feature: Getting the test user's information works

  Background:
    Given the TestClient is setup
    And the test contact 93db83d4-4119-4e0c-af87-a713786fa81d is setup
    And the test contact 67e52c77-950f-4f28-accb-bb3ea1a2c51a is setup
    And the test contact 332de237-cab7-4461-bcc3-48e68f42bd5c is setup

  Scenario: User wants to get full contact info for the minimal contact
    Given the email_id 93db83d4-4119-4e0c-af87-a713786fa81d
    And the desired endpoint /ctms/(email_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "amo": {
          "display_name": null,
          "homepage": null,
          "id": null,
          "last_login": null,
          "location": null,
          "user": false
        },
        "cv": {
          "created_at": null,
          "days_interval": null,
          "first_contribution_date": null,
          "goal_reached_at": null,
          "last_active_date": null,
          "two_day_streak": null
        },
        "email": {
          "country": "us",
          "created_date": "2014-01-22T15:24:00+00:00",
          "email": "ctms-user@example.com",
          "email_id": "93db83d4-4119-4e0c-af87-a713786fa81d",
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
    Given the email_id 67e52c77-950f-4f28-accb-bb3ea1a2c51a
    And the desired endpoint /ctms/(email_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "amo": {
          "display_name": "#1 Mozilla Fan",
          "homepage": "https://www.mozilla.org/en-US/firefox/new/",
          "id": 123,
          "last_login": "2020-01-27T14:21:00+00:00",
          "location": "The Internet",
          "user": true
        },
        "cv": {
          "created_at": "2020-10-14T16:05:21.423000+00:00",
          "days_interval": 12,
          "first_contribution_date": "2020-10-15T10:07:00+00:00",
          "goal_reached_at": "2020-11-02T11:15:19.008000+00:00",
          "last_active_date": "2021-01-10T11:15:19.008000+00:00",
          "two_day_streak": true
        },
        "email": {
          "country": "ca",
          "created_date": "2010-01-01T08:04:00+00:00",
          "email": "mozilla-fan@example.com",
          "email_id": "67e52c77-950f-4f28-accb-bb3ea1a2c51a",
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
        "fpn": {
          "country": "Canada",
          "platform": "Windows"
        },
        "fsa": {
          "allow_share": false,
          "city": "Montreal",
          "current_status": "Graduate",
          "grad_year": 2011,
          "major": "Library & Information Management",
          "school": "McGill University"
        },
        "fxa": {
          "create_date": "2019-05-22T08:29:31.906094+00:00",
          "deleted": null,
          "id": "611b6788-2bba-42a6-98c9-9ce6eb9cbd34",
          "lang": "fr,fr-CA",
          "primary_email": "fxa-firefox-fan@example.com",
          "service": "monitor"
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

  Scenario: User wants to get full contact info for the example contact
    Given the email_id 332de237-cab7-4461-bcc3-48e68f42bd5c
    And the desired endpoint /ctms/(email_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "amo": {
          "display_name": "Add-ons Author",
          "homepage": "https://my-mozilla-addon.example.org/",
          "id": 98765,
          "last_login": "2021-01-28T19:21:50.908000+00:00",
          "location": "California, USA, Earth",
          "user": true
        },
        "cv": {
          "created_at": "2019-02-14T16:05:21.423000+00:00",
          "days_interval": 10,
          "first_contribution_date": "2019-02-15T10:07:00+00:00",
          "goal_reached_at": "2019-03-15T11:15:19+00:00",
          "last_active_date": "2020-12-10T16:56:00+00:00",
          "two_day_streak": true
        },
        "email": {
          "country": "us",
          "created_date": "2020-03-28T15:41:00+00:00",
          "email": "contact@example.com",
          "email_id": "332de237-cab7-4461-bcc3-48e68f42bd5c",
          "first_name": null,
          "format": "H",
          "id": "001A000023aABcDEFG",
          "lang": "en",
          "last_modified_date": "2021-01-28T21:26:57.511000+00:00",
          "last_name": "_",
          "optin": true,
          "optout": false,
          "payee_id": null,
          "postal_code": "94041",
          "reason": null,
          "record_type": "0124A0000001aABCDE",
          "source_url": "https://www.mozilla.org/en-US/",
          "token": "c4a7d759-bb52-457b-896b-90f1d3ef8433"
        },
        "fpn": {
          "country": "France",
          "platform": "Chrome"
        },
        "fsa": {
          "allow_share": true,
          "city": "Dehradun",
          "current_status": "Student",
          "grad_year": 2012,
          "major": "Computer Science",
          "school": "DIT University, Makkawala, Salon gaon, Dehradun"
        },
        "fxa": {
          "create_date": "2021-01-29T18:43:49.082375+00:00",
          "deleted": null,
          "id": "6eb6ed6a-c3b6-4259-968a-a490c6c0b9df",
          "lang": "en,en-US",
          "primary_email": "my-fxa-acct@example.com",
          "service": "sync"
        },
        "newsletters": [],
        "status": "ok"
      }
      """

  Scenario: User wants to read identity data for the minimal contact
    Given the email_id 93db83d4-4119-4e0c-af87-a713786fa81d
    And the desired endpoint /identity/(email_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "amo_id": null,
        "email_id": "93db83d4-4119-4e0c-af87-a713786fa81d",
        "fxa_id": null,
        "fxa_primary_email": null,
        "id": "001A000001aABcDEFG",
        "token": "142e20b6-1ef5-43d8-b5f4-597430e956d7"
      }
      """

  Scenario: User wants to read identity data for the maximal contact
    Given the email_id 67e52c77-950f-4f28-accb-bb3ea1a2c51a
    And the desired endpoint /identity/(email_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "amo_id": 123,
        "email_id": "67e52c77-950f-4f28-accb-bb3ea1a2c51a",
        "fxa_id": "611b6788-2bba-42a6-98c9-9ce6eb9cbd34",
        "fxa_primary_email": "fxa-firefox-fan@example.com",
        "id": "001A000001aMozFan",
        "token": "d9ba6182-f5dd-4728-a477-2cc11bf62b69"
      }
      """

  Scenario: User wants to read identity data for the example contact
    Given the email_id 332de237-cab7-4461-bcc3-48e68f42bd5c
    And the desired endpoint /identity/(email_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "amo_id": 98765,
        "email_id": "332de237-cab7-4461-bcc3-48e68f42bd5c",
        "fxa_id": "6eb6ed6a-c3b6-4259-968a-a490c6c0b9df",
        "fxa_primary_email": "my-fxa-acct@example.com",
        "id": "001A000023aABcDEFG",
        "token": "c4a7d759-bb52-457b-896b-90f1d3ef8433"
      }
      """

  Scenario: User wants to read the main contact data for the minimal contact
    Given the email_id 93db83d4-4119-4e0c-af87-a713786fa81d
    And the desired endpoint /contact/main/(email_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "country": "us",
        "created_date": "2014-01-22T15:24:00+00:00",
        "email": "ctms-user@example.com",
        "email_id": "93db83d4-4119-4e0c-af87-a713786fa81d",
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
    Given the email_id 93db83d4-4119-4e0c-af87-a713786fa81d
    And the desired endpoint /contact/amo/(email_id)
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
    Given the email_id 93db83d4-4119-4e0c-af87-a713786fa81d
    And the desired endpoint /contact/cv/(email_id)
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
    Given the email_id 93db83d4-4119-4e0c-af87-a713786fa81d
    And the desired endpoint /contact/fpn/(email_id)
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
    Given the email_id 93db83d4-4119-4e0c-af87-a713786fa81d
    And the desired endpoint /contact/fsa/(email_id)
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
    Given the email_id 93db83d4-4119-4e0c-af87-a713786fa81d
    And the desired endpoint /contact/fxa/(email_id)
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
    Given the email_id cad092ec-a71a-4df5-aa92-517959caeecb
    And the desired endpoint /<endpoint_prefix>/(email_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 404
    And the response JSON is
    """
    {
      "detail": "Unknown email_id"
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
