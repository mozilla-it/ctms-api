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
          "add_on_ids": null,
          "create_timestamp": null,
          "display_name": null,
          "email_opt_in": false,
          "language": null,
          "last_login": null,
          "location": null,
          "profile_url": null,
          "update_timestamp": null,
          "user": false,
          "user_id": null,
          "username": null
        },
        "email": {
          "basket_token": "142e20b6-1ef5-43d8-b5f4-597430e956d7",
          "browser_locale": null,
          "create_timestamp": "2014-01-22T15:24:00+00:00",
          "email_format": "H",
          "email_id": "93db83d4-4119-4e0c-af87-a713786fa81d",
          "email_lang": "en",
          "has_opted_out_of_email": false,
          "mailing_country": "us",
          "mofo_relevant": false,
          "name": null,
          "pmt_cust_id": null,
          "primary_email": "ctms-user@example.com",
          "signup_source": null,
          "subscriber": false,
          "unengaged": false,
          "unsubscribe_reason": null,
          "update_timestamp": "2020-01-22T15:24:00+00:00"
        },
        "fpn": {
          "country": null,
          "platform": null
        },
        "fxa": {
          "created_date": null,
          "deleted": false,
          "first_service": null,
          "fxa_id": null,
          "lang": null,
          "primary_email": null
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
          "add_on_ids": "fanfox,foxfan",
          "create_timestamp": "2017-05-12T15:16:00+00:00",
          "display_name": "#1 Mozilla Fan",
          "email_opt_in": true,
          "language": "fr,en",
          "last_login": "2020-01-27T14:21:00.000+0000",
          "location": "The Inter",
          "profile_url": "firefox/user/14508209",
          "update_timestamp": "2020-01-27T14:25:43+00:00",
          "user": true,
          "user_id": "123",
          "username": "Mozilla1Fan"
        },
        "email": {
          "basket_token": "d9ba6182-f5dd-4728-a477-2cc11bf62b69",
          "browser_locale": "fr-CA",
          "create_timestamp": "2010-01-01T08:04:00+00:00",
          "email_format": "H",
          "email_id": "67e52c77-950f-4f28-accb-bb3ea1a2c51a",
          "email_lang": "fr",
          "has_opted_out_of_email": false,
          "mailing_country": "ca",
          "mofo_relevant": true,
          "name": "Fan of Mozilla",
          "pmt_cust_id": "cust_012345",
          "primary_email": "mozilla-fan@example.com",
          "signup_source": "https://developer.mozilla.org/fr/",
          "subscriber": true,
          "unengaged": false,
          "unsubscribe_reason": "done with this mailing list",
          "update_timestamp": "2020-01-28T14:50:00+00:00"
        },
        "fpn": {
          "country": "Canada",
          "platform": "Windows"
        },
        "fxa": {
          "created_date": "2019-05-22T08:29:31.906094+00:00",
          "deleted": false,
          "first_service": "monitor",
          "fxa_id": "611b6788-2bba-42a6-98c9-9ce6eb9cbd34",
          "lang": "fr,fr-CA",
          "primary_email": "fxa-firefox-fan@example.com"
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
          "add_on_ids": "add-on-1,add-on-2",
          "create_timestamp": "2020-12-05T19:21:50.908000+00:00",
          "display_name": "Add-ons Author",
          "email_opt_in": false,
          "language": "en",
          "last_login": "2021-01-28T19:21:50.908Z",
          "location": "California",
          "profile_url": "firefox/user/98765",
          "update_timestamp": "2021-02-04T15:36:57.511000+00:00",
          "user": true,
          "user_id": "98765",
          "username": "AddOnAuthor"
        },
        "email": {
          "basket_token": "c4a7d759-bb52-457b-896b-90f1d3ef8433",
          "browser_locale": null,
          "create_timestamp": "2020-03-28T15:41:00+00:00",
          "email_format": "H",
          "email_id": "332de237-cab7-4461-bcc3-48e68f42bd5c",
          "email_lang": "en",
          "has_opted_out_of_email": false,
          "mailing_country": "us",
          "mofo_relevant": false,
          "name": "Mozilla Subscriber",
          "pmt_cust_id": null,
          "primary_email": "contact@example.com",
          "signup_source": "https://www.mozilla.org/en-US/",
          "subscriber": false,
          "unengaged": false,
          "unsubscribe_reason": null,
          "update_timestamp": "2021-01-28T21:26:57.511000+00:00"
        },
        "fpn": {
          "country": "France",
          "platform": "Chrome"
        },
        "fxa": {
          "created_date": "2021-01-29T18:43:49.082375+00:00",
          "deleted": false,
          "first_service": "sync",
          "fxa_id": "6eb6ed6a-c3b6-4259-968a-a490c6c0b9df",
          "lang": "en,en-US",
          "primary_email": "my-fxa-acct@example.com"
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
        "email_id": "93db83d4-4119-4e0c-af87-a713786fa81d",
        "primary_email": "ctms-user@example.com",
        "basket_token": "142e20b6-1ef5-43d8-b5f4-597430e956d7",
        "amo_user_id": null,
        "fxa_id": null,
        "fxa_primary_email": null
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
        "email_id": "67e52c77-950f-4f28-accb-bb3ea1a2c51a",
        "primary_email": "mozilla-fan@example.com",
        "amo_user_id": "123",
        "basket_token": "d9ba6182-f5dd-4728-a477-2cc11bf62b69",
        "fxa_id": "611b6788-2bba-42a6-98c9-9ce6eb9cbd34",
        "fxa_primary_email": "fxa-firefox-fan@example.com"
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
        "email_id": "332de237-cab7-4461-bcc3-48e68f42bd5c",
        "primary_email": "contact@example.com",
        "amo_user_id": "98765",
        "basket_token": "c4a7d759-bb52-457b-896b-90f1d3ef8433",
        "fxa_id": "6eb6ed6a-c3b6-4259-968a-a490c6c0b9df",
        "fxa_primary_email": "my-fxa-acct@example.com"
      }
      """

  Scenario: User wants to read the main email data for the minimal contact
    Given the email_id 93db83d4-4119-4e0c-af87-a713786fa81d
    And the desired endpoint /contact/email/(email_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "basket_token": "142e20b6-1ef5-43d8-b5f4-597430e956d7",
        "browser_locale": null,
        "create_timestamp": "2014-01-22T15:24:00+00:00",
        "email_format": "H",
        "email_id": "93db83d4-4119-4e0c-af87-a713786fa81d",
        "email_lang": "en",
        "has_opted_out_of_email": false,
        "mailing_country": "us",
        "mofo_relevant": false,
        "name": null,
        "pmt_cust_id": null,
        "primary_email": "ctms-user@example.com",
        "signup_source": null,
        "subscriber": false,
        "unengaged": false,
        "unsubscribe_reason": null,
        "update_timestamp": "2020-01-22T15:24:00+00:00"
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
        "add_on_ids": null,
        "create_timestamp": null,
        "display_name": null,
        "email_opt_in": false,
        "language": null,
        "last_login": null,
        "location": null,
        "profile_url": null,
        "update_timestamp": null,
        "user": false,
        "user_id": null,
        "username": null
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

  Scenario: User wants to read the FXA data for the minimal contact
    Given the email_id 93db83d4-4119-4e0c-af87-a713786fa81d
    And the desired endpoint /contact/fxa/(email_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "created_date": null,
        "deleted": false,
        "first_service": null,
        "fxa_id": null,
        "lang": null,
        "primary_email": null
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
      | contact/amo     |
      | contact/email   |
      | contact/fpn     |
      | contact/fxa     |
