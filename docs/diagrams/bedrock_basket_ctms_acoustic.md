# Bedrock Basket CTMS

* [Bedrock](https://github.com/mozilla/bedrock/) powers https://www.mozilla.org
* [Basket](https://github.com/mozmeao/basket/) receives form POSTs and stores contacts in CTMS

## VPN Waiting List

```mermaid
sequenceDiagram
    autonumber
    actor Visitor
    Visitor->>+Bedrock: Visits mozilla.org
    activate Bedrock
    Bedrock-->>-Visitor: Renders `VPNWaitlistForm` [token]
    deactivate Bedrock

    Visitor->>Bedrock: Submit form [newsletter=guardian-vpn-waitlist,<br> email, platform, country, token]
    %% https://github.com/mozilla/bedrock/blob/ecba76406ed35c04d35532c3ed7562b09d65fabe/bedrock/products/forms.py#L10
    %% https://github.com/mozilla/bedrock/blob/ef4d73603bdd914e327232f2c66e3e93be32f2a4/bedrock/products/templates/products/vpn/invite.html#L31

    Bedrock->>Basket: subscribe(email, lang, newsletter, fpn_platform, <br> fpn_country, source_url, api_key, token)
    %% https://github.com/mozilla/bedrock/blob/ecba76406ed35c04d35532c3ed7562b09d65fabe/bedrock/products/views.py#L68-L87

    Basket->>Basket Task: Spawn task
    %% https://github.com/mozmeao/basket/blob/2023-07-06/basket/news/views.py#L681

    Basket-->>Bedrock: [status]
    Bedrock-->>Visitor: .

    rect rgb(240,240,240)
    Basket Task->>Basket Task: Process data
    %% https://github.com/mozmeao/basket/blob/2023-07-06/basket/news/backends/ctms.py#L263

    Basket Task->>CTMS: update(token, email_id, newsletters, fpn_platform, fpn_country)
    %% https://github.com/mozmeao/basket/blob/2023-07-06/basket/news/tasks.py#L401
    %% https://github.com/mozilla-it/ctms-api/blob/v2.1.0/ctms/crud.py#L579

    CTMS-->>Basket Task: .
    end
```

### Payload Examples

Bedrock POST form data:

```
 {
    "form-MAX_NUM_FORMS": 4,
    "form-INITIAL_FORMS": 4,
    "form-TOTAL_FORMS": 4,
    "email": "you@example.com",
    "lang": "fr",
    "country": "fr",
    "format": "T",
    "privacy": "on",
    "form-0-newsletter": "mozilla-and-you",
    "form-0-subscribed_radio": "true",
    "form-1-newsletter": "mozilla-welcome",
    "form-1-subscribed_radio": "true",
    "form-2-newsletter": "firefox-tips",
    "form-2-subscribed_check": "false",
    "form-3-newsletter": "join-mozilla",
    "form-3-subscribed_check": "false",
    "submit": "Save Preferences",
}
```

Basket update user ([`POST /news/subscribe`](https://github.com/mozmeao/basket/blob/ba2abdecbddd0a186a716398b33b4dff0a775d73/docs/newsletter_api.rst#newssubscribe)):

```
{
    "email": "you@example.com",
    "format": "T",
    "country": "fr",
    "lang": "fr",
    "newsletters": "mozilla-and-you,mozilla-welcome",
    "source_url": "https://vpn.mozilla.org/fr",
    "fpn_country": "fr",
    "fpn_platform": "ios,mac"
}
```

CTMS create contact ([`POST /ctms`](https://github.com/mozilla-it/ctms-api/blob/6f903aeb90b65c170f34485e1cc4b3755839daaf/ctms/app.py#L545-L552)):

```
{
    "email": {
        "basket_token": "c4a7d759-bb52-457b-896b-90f1d3ef8433",
        "create_timestamp": "2020-03-28T15:41:00.000Z",
        "double_opt_in": True,
        "email_format": "T",
        "email_id": "332de237-cab7-4461-bcc3-48e68f42bd5c",
        "email_lang": "fr",
        "first_name": "Jane",
        "has_opted_out_of_email": False,
        "last_name": "Doe",
        "mailing_country": "fr",
        "primary_email": "you@example.com",
        "sfdc_id": "001A000023aABcDEFG",
        "unsubscribe_reason": "",
        "update_timestamp": "2021-01-28T21:26:57.511Z",
    },
    "newsletters": [
        {
            "name": "mozilla-and-you",
            "subscribed": True,
            "format": "T",
            "lang": "fr",
        },
        {
            "name": "mozilla-welcome",
            "subscribed": True,
            "format": "T",
            "lang": "fr",
        }
    ],
    "waitlist": [
        {
            "name": "vpn",
            "subscribed": True,
            "source": "https://vpn.mozilla.org/fr",
            "fields": {
                "geo": "fr",
                "platform": "ios,mac"
            }
        }
    ]
}
```
