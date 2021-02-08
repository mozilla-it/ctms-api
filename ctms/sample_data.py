from typing import Dict
from uuid import UUID

from .schemas import (
    AddOnsSchema,
    ContactFirefoxAccountsSchema,
    ContactFirefoxPrivateNetworkSchema,
    ContactSchema,
    EmailSchema,
)

# A contact that has just some of the fields entered
SAMPLE_MINIMAL = ContactSchema(
    email=EmailSchema(
        basket_token="142e20b6-1ef5-43d8-b5f4-597430e956d7",
        create_timestamp="2014-01-22T15:24:00+00:00",
        email_id=UUID("93db83d4-4119-4e0c-af87-a713786fa81d"),
        mailing_country="us",
        primary_email="ctms-user@example.com",
        update_timestamp="2020-01-22T15:24:00.000+0000",
    ),
    newsletters=[
        "app-dev",
        "maker-party",
        "mozilla-foundation",
        "mozilla-learning-network",
    ],
)

# A contact that has all of the fields set
SAMPLE_MAXIMAL = ContactSchema(
    amo=AddOnsSchema(
        add_on_ids="fanfox,foxfan",
        display_name="#1 Mozilla Fan",
        email_opt_in=True,
        language="fr,en",
        last_login="2020-01-27T14:21:00.000+0000",
        location="The Inter",
        profile_url="firefox/user/14508209",
        user=True,
        user_id="123",
        username="Mozilla1Fan",
        create_timestamp="2017-05-12T15:16:00+00:00",
        update_timestamp="2020-01-27T14:25:43+00:00",
    ),
    email=EmailSchema(
        email_id=UUID("67e52c77-950f-4f28-accb-bb3ea1a2c51a"),
        primary_email="mozilla-fan@example.com",
        basket_token="d9ba6182-f5dd-4728-a477-2cc11bf62b69",
        name="Fan of Mozilla",
        mailing_country="ca",
        email_lang="fr",
        browser_locale="fr-CA",
        mofo_relevant=True,
        signup_source="https://developer.mozilla.org/fr/",
        pmt_cust_id="cust_012345",
        subscriber=True,
        unsubscribe_reason="done with this mailing list",
        create_timestamp="2010-01-01T08:04:00+00:00",
        update_timestamp="2020-01-28T14:50:00.000+0000",
    ),
    fpn=ContactFirefoxPrivateNetworkSchema(
        country="Canada",
        platform="Windows",
    ),
    fxa=ContactFirefoxAccountsSchema(
        create_date="2019-05-22T08:29:31.906094+00:00",
        id="611b6788-2bba-42a6-98c9-9ce6eb9cbd34",
        lang="fr,fr-CA",
        primary_email="fxa-firefox-fan@example.com",
        service="monitor",
    ),
    newsletters=[
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
        "webmaker",
    ],
)


def _gather_examples(schema_class) -> Dict[str, str]:
    """Gather the examples from a schema definition"""
    examples = dict()
    for key, props in schema_class.schema()["properties"].items():
        if "example" in props:
            examples[key] = props["example"]
    return examples


# A sample user that has the OpenAPI schema examples
SAMPLE_EXAMPLE = ContactSchema(
    amo=AddOnsSchema(**_gather_examples(AddOnsSchema)),
    email=EmailSchema(**_gather_examples(EmailSchema)),
    fpn=ContactFirefoxPrivateNetworkSchema(
        **ContactFirefoxPrivateNetworkSchema.Config.schema_extra["example"]
    ),
    fxa=ContactFirefoxAccountsSchema(
        **ContactFirefoxAccountsSchema.Config.schema_extra["example"]
    ),
)


SAMPLE_CONTACTS = {
    SAMPLE_MINIMAL.email.email_id: SAMPLE_MINIMAL,
    SAMPLE_MAXIMAL.email.email_id: SAMPLE_MAXIMAL,
    SAMPLE_EXAMPLE.email.email_id: SAMPLE_EXAMPLE,
}
