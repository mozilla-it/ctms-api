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
          "create_timestamp": "2014-01-22T15:24:00+00:00",
          "email_format": "H",
          "email_id": "93db83d4-4119-4e0c-af87-a713786fa81d",
          "email_lang": "en",
          "first_name": null,
          "has_opted_out_of_email": false,
          "last_name": null,
          "mailing_country": "us",
          "mofo_relevant": false,
          "pmt_cust_id": null,
          "primary_email": "ctms-user@example.com",
          "sfdc_id": "001A000001aABcDEFG",
          "signup_source": null,
          "subscriber": false,
          "unsubscribe_reason": null,
          "update_timestamp": "2020-01-22T15:24:00+00:00"
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
          {
            "format": "H",
            "lang": "en",
            "name": "app-dev",
            "source": null,
            "subscribed": true,
            "unsub_reason": null
          },
          {
            "format": "H",
            "lang": "en",
            "name": "maker-party",
            "source": null,
            "subscribed": true,
            "unsub_reason": null
          },
          {
            "format": "H",
            "lang": "en",
            "name": "mozilla-foundation",
            "source": null,
            "subscribed": true,
            "unsub_reason": null
          },
          {
            "format": "H",
            "lang": "en",
            "name": "mozilla-learning-network",
            "source": null,
            "subscribed": true,
            "unsub_reason": null
          }
        ],
        "status": "ok",
        "vpn_waitlist": {
          "geo": null,
          "platform": null
        }
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
          "create_timestamp": "2010-01-01T08:04:00+00:00",
          "email_format": "H",
          "email_id": "67e52c77-950f-4f28-accb-bb3ea1a2c51a",
          "email_lang": "fr",
          "first_name": "Fan",
          "has_opted_out_of_email": false,
          "last_name": "of Mozilla",
          "mailing_country": "ca",
          "mofo_relevant": true,
          "pmt_cust_id": "cust_012345",
          "primary_email": "mozilla-fan@example.com",
          "sfdc_id": "001A000001aMozFan",
          "signup_source": "https://developer.mozilla.org/fr/",
          "subscriber": true,
          "unsubscribe_reason": "done with this mailing list",
          "update_timestamp": "2020-01-28T14:50:00+00:00"
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
            {
              "format": "H",
              "lang": "en",
              "name": "ambassadors",
              "source": "https://www.mozilla.org/en-US/contribute/studentambassadors/",
              "subscribed": false,
              "unsub_reason": "Graduated, don't have time for FSA"
            },
            {
              "format": "T",
              "lang": "fr",
              "name": "common-voice",
              "source": "https://commonvoice.mozilla.org/fr",
              "subscribed": true,
              "unsub_reason": null
            },
            {
              "format": "H",
              "lang": "fr",
              "name": "firefox-accounts-journey",
              "source": "https://www.mozilla.org/fr/firefox/accounts/",
              "subscribed": false,
              "unsub_reason": "done with this mailing list"
            },
            {
              "format": "H",
              "lang": "en",
              "name": "firefox-os",
              "source": null,
              "subscribed": true,
              "unsub_reason": null
            },
            {
              "format": "H",
              "lang": "fr",
              "name": "hubs",
              "source": null,
              "subscribed": true,
              "unsub_reason": null
            },
            {
              "format": "H",
              "lang": "en",
              "name": "mozilla-festival",
              "source": null,
              "subscribed": true,
              "unsub_reason": null
            },
            {
              "format": "H",
              "lang": "fr",
              "name": "mozilla-foundation",
              "source": null,
              "subscribed": true,
              "unsub_reason": null
            }
        ],
        "status": "ok",
        "vpn_waitlist": {
          "geo": "ca",
          "platform": "windows,android"
        }
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
          "create_timestamp": "2020-03-28T15:41:00+00:00",
          "email_format": "H",
          "email_id": "332de237-cab7-4461-bcc3-48e68f42bd5c",
          "email_lang": "en",
          "first_name": "Jane",
          "has_opted_out_of_email": false,
          "last_name": "Doe",
          "mailing_country": "us",
          "mofo_relevant": false,
          "pmt_cust_id": null,
          "primary_email": "contact@example.com",
          "sfdc_id": "001A000023aABcDEFG",
          "signup_source": "https://www.mozilla.org/en-US/",
          "subscriber": false,
          "unsubscribe_reason": null,
          "update_timestamp": "2021-01-28T21:26:57.511000+00:00"
        },
        "fxa": {
          "created_date": "2021-01-29T18:43:49.082375+00:00",
          "deleted": false,
          "first_service": "sync",
          "fxa_id": "6eb6ed6a-c3b6-4259-968a-a490c6c0b9df",
          "lang": "en,en-US",
          "primary_email": "my-fxa-acct@example.com"
        },
        "newsletters": [
          {
            "format": "H",
            "lang": "en",
            "name": "firefox-welcome",
            "source": null,
            "subscribed": true,
            "unsub_reason": null
          },
          {
            "format": "H",
            "lang": "en",
            "name": "mozilla-welcome",
            "source": null,
            "subscribed": true,
            "unsub_reason": null
          }
        ],
        "status": "ok",
        "vpn_waitlist": {
          "geo": "fr",
          "platform": "ios,mac"
        }
      }
      """

  Scenario: User wants to get contact data by alternate ID Firefox Accounts email
    Given the desired endpoint /ctms?fxa_primary_email=my-fxa-acct@example.com
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
    """
    [
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
          "create_timestamp": "2020-03-28T15:41:00+00:00",
          "email_format": "H",
          "email_id": "332de237-cab7-4461-bcc3-48e68f42bd5c",
          "email_lang": "en",
          "first_name": "Jane",
          "has_opted_out_of_email": false,
          "last_name": "Doe",
          "mailing_country": "us",
          "mofo_relevant": false,
          "pmt_cust_id": null,
          "primary_email": "contact@example.com",
          "sfdc_id": "001A000023aABcDEFG",
          "signup_source": "https://www.mozilla.org/en-US/",
          "subscriber": false,
          "unsubscribe_reason": null,
          "update_timestamp": "2021-01-28T21:26:57.511000+00:00"
        },
        "fxa": {
          "created_date": "2021-01-29T18:43:49.082375+00:00",
          "deleted": false,
          "first_service": "sync",
          "fxa_id": "6eb6ed6a-c3b6-4259-968a-a490c6c0b9df",
          "lang": "en,en-US",
          "primary_email": "my-fxa-acct@example.com"
        },
        "newsletters": [
          {
            "format": "H",
            "lang": "en",
            "name": "firefox-welcome",
            "source": null,
            "subscribed": true,
            "unsub_reason": null
          },
          {
            "format": "H",
            "lang": "en",
            "name": "mozilla-welcome",
            "source": null,
            "subscribed": true,
            "unsub_reason": null
          }
        ],
        "vpn_waitlist": {
          "geo": "fr",
          "platform": "ios,mac"
        }
      }
    ]
    """

  Scenario: User receives a bad request error when finding contacts with no alternate IDs
    Given the desired endpoint /ctms
    When the user invokes the client via GET
    Then the user expects the response to have a status of 400
    And the response JSON is
    """
    {
      "detail": "No identifiers provided, at least one is needed: email_id, primary_email, basket_token, sfdc_id, amo_user_id, fxa_id, fxa_primary_email"
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
        "sfdc_id": "001A000001aABcDEFG",
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
        "fxa_primary_email": "fxa-firefox-fan@example.com",
        "sfdc_id": "001A000001aMozFan"
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
        "fxa_primary_email": "my-fxa-acct@example.com",
        "sfdc_id": "001A000023aABcDEFG"
      }
      """

  Scenario: User wants to find an identity by email_id
        Given the desired endpoint /identities?email_id=332de237-cab7-4461-bcc3-48e68f42bd5c
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      [
        {
          "email_id": "332de237-cab7-4461-bcc3-48e68f42bd5c",
          "primary_email": "contact@example.com",
          "amo_user_id": "98765",
          "basket_token": "c4a7d759-bb52-457b-896b-90f1d3ef8433",
          "fxa_id": "6eb6ed6a-c3b6-4259-968a-a490c6c0b9df",
          "fxa_primary_email": "my-fxa-acct@example.com",
          "sfdc_id": "001A000023aABcDEFG"
        }
      ]
      """

  Scenario: User wants to find an identity by primary email
    Given the desired endpoint /identities?primary_email=ctms-user@example.com
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      [
        {
          "email_id": "93db83d4-4119-4e0c-af87-a713786fa81d",
          "primary_email": "ctms-user@example.com",
          "basket_token": "142e20b6-1ef5-43d8-b5f4-597430e956d7",
          "sfdc_id": "001A000001aABcDEFG",
          "amo_user_id": null,
          "fxa_id": null,
          "fxa_primary_email": null
        }
      ]
      """

  Scenario: User wants to find an identity by basket token
    Given the desired endpoint /identities?basket_token=d9ba6182-f5dd-4728-a477-2cc11bf62b69
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      [
        {
          "email_id": "67e52c77-950f-4f28-accb-bb3ea1a2c51a",
          "primary_email": "mozilla-fan@example.com",
          "amo_user_id": "123",
          "basket_token": "d9ba6182-f5dd-4728-a477-2cc11bf62b69",
          "fxa_id": "611b6788-2bba-42a6-98c9-9ce6eb9cbd34",
          "fxa_primary_email": "fxa-firefox-fan@example.com",
          "sfdc_id": "001A000001aMozFan"
        }
      ]
      """

  Scenario: User wants to find an identity by legacy Salesforce ID
    Given the desired endpoint /identities?sfdc_id=001A000001aABcDEFG
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      [
        {
          "email_id": "93db83d4-4119-4e0c-af87-a713786fa81d",
          "primary_email": "ctms-user@example.com",
          "basket_token": "142e20b6-1ef5-43d8-b5f4-597430e956d7",
          "sfdc_id": "001A000001aABcDEFG",
          "amo_user_id": null,
          "fxa_id": null,
          "fxa_primary_email": null
        }
      ]
      """
  Scenario: User wants to find an identity by ID on addons.mozilla.org
    Given the desired endpoint /identities?amo_user_id=123
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      [
        {
          "email_id": "67e52c77-950f-4f28-accb-bb3ea1a2c51a",
          "primary_email": "mozilla-fan@example.com",
          "amo_user_id": "123",
          "basket_token": "d9ba6182-f5dd-4728-a477-2cc11bf62b69",
          "fxa_id": "611b6788-2bba-42a6-98c9-9ce6eb9cbd34",
          "fxa_primary_email": "fxa-firefox-fan@example.com",
          "sfdc_id": "001A000001aMozFan"
        }
      ]
      """

  Scenario: User wants to find an identity by Firefox Accounts ID
    Given the desired endpoint /identities?fxa_id=611b6788-2bba-42a6-98c9-9ce6eb9cbd34
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      [
        {
          "email_id": "67e52c77-950f-4f28-accb-bb3ea1a2c51a",
          "primary_email": "mozilla-fan@example.com",
          "amo_user_id": "123",
          "basket_token": "d9ba6182-f5dd-4728-a477-2cc11bf62b69",
          "fxa_id": "611b6788-2bba-42a6-98c9-9ce6eb9cbd34",
          "fxa_primary_email": "fxa-firefox-fan@example.com",
          "sfdc_id": "001A000001aMozFan"
        }
      ]
      """

  Scenario: User wants to find an identity by Firefox Accounts primary email
    Given the desired endpoint /identities?fxa_primary_email=fxa-firefox-fan@example.com
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      [
        {
          "email_id": "67e52c77-950f-4f28-accb-bb3ea1a2c51a",
          "primary_email": "mozilla-fan@example.com",
          "amo_user_id": "123",
          "basket_token": "d9ba6182-f5dd-4728-a477-2cc11bf62b69",
          "fxa_id": "611b6788-2bba-42a6-98c9-9ce6eb9cbd34",
          "fxa_primary_email": "fxa-firefox-fan@example.com",
          "sfdc_id": "001A000001aMozFan"
        }
      ]
      """

  Scenario: User wants to find an identity by two alternate IDs
    Given the desired endpoint /identities?sfdc_id=001A000001aMozFan&fxa_primary_email=fxa-firefox-fan@example.com
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      [
        {
          "email_id": "67e52c77-950f-4f28-accb-bb3ea1a2c51a",
          "primary_email": "mozilla-fan@example.com",
          "amo_user_id": "123",
          "basket_token": "d9ba6182-f5dd-4728-a477-2cc11bf62b69",
          "fxa_id": "611b6788-2bba-42a6-98c9-9ce6eb9cbd34",
          "fxa_primary_email": "fxa-firefox-fan@example.com",
          "sfdc_id": "001A000001aMozFan"
        }
      ]
      """

  Scenario: User wants to find an identity by two alternate IDs, but one does not match
    Given the desired endpoint /identities?primary_email=ctms-user@example.com&amo_user_id=404
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      []
      """

  Scenario: User wants to find an identity by two alternate IDs, but one is empty
    Given the desired endpoint /identities?primary_email=ctms-user@example.com&fxa_id=
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      []
      """

  Scenario: User receives a bad request error when finding identities with no alternate IDs
    Given the desired endpoint /identities
    When the user invokes the client via GET
    Then the user expects the response to have a status of 400
    And the response JSON is
      """
      {
        "detail": "No identifiers provided, at least one is needed: email_id, primary_email, basket_token, sfdc_id, amo_user_id, fxa_id, fxa_primary_email"
      }
      """

  Scenario Outline: Unknown alternate IDs are not found
    Given the email_id cad092ec-a71a-4df5-aa92-517959caeecb
    And the desired endpoint /identities?<alt_id>=<alt_value>
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
    """
    []
    """

    Examples: Alternate IDs
      | alt_id            | alt_value                            |
      | email_id          | cad092ec-a71a-4df5-aa92-517959caeecb |
      | primary_email     | unknown-user@example.com             |
      | amo_user_id       | 404                                  |
      | basket_token      | cad092ec-a71a-4df5-aa92-517959caeecb |
      | fxa_id            | cad092ec-a71a-4df5-aa92-517959caeecb |
      | fxa_primary_email | unknown-user@example.com             |
      | sfdc_id           | 001A000404aUnknown                   |

  Scenario: User wants to read the main email data for the minimal contact
    Given the email_id 93db83d4-4119-4e0c-af87-a713786fa81d
    And the desired endpoint /contact/email/(email_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "basket_token": "142e20b6-1ef5-43d8-b5f4-597430e956d7",
        "create_timestamp": "2014-01-22T15:24:00+00:00",
        "email_format": "H",
        "email_id": "93db83d4-4119-4e0c-af87-a713786fa81d",
        "email_lang": "en",
        "first_name": null,
        "has_opted_out_of_email": false,
        "last_name": null,
        "mailing_country": "us",
        "mofo_relevant": false,
        "pmt_cust_id": null,
        "primary_email": "ctms-user@example.com",
        "sfdc_id": "001A000001aABcDEFG",
        "signup_source": null,
        "subscriber": false,
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

  Scenario: User wants to read the VPN waitlist data for the minimal contact
    Given the email_id 93db83d4-4119-4e0c-af87-a713786fa81d
    And the desired endpoint /contact/vpn_waitlist/(email_id)
    When the user invokes the client via GET
    Then the user expects the response to have a status of 200
    And the response JSON is
      """
      {
        "geo": null,
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
      | contact/fxa     |
      | contact/vpn_waitlist |
