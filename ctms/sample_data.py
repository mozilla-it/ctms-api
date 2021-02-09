from typing import Dict
from uuid import UUID

from .schemas import (
    AddOnsSchema,
    ContactSchema,
    EmailSchema,
    FirefoxAccountsSchema,
    NewsletterSchema,
    VpnWaitlistSchema,
)

# A contact that has just some of the fields entered
SAMPLE_MINIMAL = ContactSchema(
    email=EmailSchema(
        basket_token="142e20b6-1ef5-43d8-b5f4-597430e956d7",
        create_timestamp="2014-01-22T15:24:00+00:00",
        email_id=UUID("93db83d4-4119-4e0c-af87-a713786fa81d"),
        mailing_country="us",
        primary_email="ctms-user@example.com",
        sfdc_id="001A000001aABcDEFG",
        update_timestamp="2020-01-22T15:24:00.000+0000",
    ),
    newsletters=[
        {"name": "app-dev"},
        {"name": "maker-party"},
        {"name": "mozilla-foundation"},
        {"name": "mozilla-learning-network"},
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
        sfdc_id="001A000001aMozFan",
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
        mofo_relevant=True,
        pmt_cust_id="cust_012345",
        sfdc_id="001A000001aMozFan",
        signup_source="https://developer.mozilla.org/fr/",
        subscriber=True,
        unsubscribe_reason="done with this mailing list",
        create_timestamp="2010-01-01T08:04:00+00:00",
        update_timestamp="2020-01-28T14:50:00.000+0000",
    ),
    fxa=FirefoxAccountsSchema(
        created_date="2019-05-22T08:29:31.906094+00:00",
        fxa_id="611b6788-2bba-42a6-98c9-9ce6eb9cbd34",
        lang="fr,fr-CA",
        primary_email="fxa-firefox-fan@example.com",
        first_service="monitor",
    ),
    newsletters=[
        NewsletterSchema(
            name="ambassadors",
            source="https://www.mozilla.org/en-US/contribute/studentambassadors/",
            subscribed=False,
            unsub_reason="Graduated, don't have time for FSA",
        ),
        NewsletterSchema(
            name="common-voice",
            format="T",
            lang="fr",
            source="https://commonvoice.mozilla.org/fr",
        ),
        NewsletterSchema(
            name="firefox-accounts-journey",
            source="https://www.mozilla.org/fr/firefox/accounts/",
            lang="fr",
            subscribed=False,
            unsub_reason="done with this mailing list",
        ),
        NewsletterSchema(name="firefox-os"),
        NewsletterSchema(name="hubs", lang="fr"),
        NewsletterSchema(name="mozilla-festival"),
        NewsletterSchema(name="mozilla-foundation", lang="fr"),
    ],
    vpn_waitlist=VpnWaitlistSchema(
        geo="ca",
        platform="windows,android",
    ),
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
    fxa=FirefoxAccountsSchema(**_gather_examples(FirefoxAccountsSchema)),
    vpn_waitlist=VpnWaitlistSchema(**_gather_examples(VpnWaitlistSchema)),
)


SAMPLE_CONTACTS = {
    SAMPLE_MINIMAL.email.email_id: SAMPLE_MINIMAL,
    SAMPLE_MAXIMAL.email.email_id: SAMPLE_MAXIMAL,
    SAMPLE_EXAMPLE.email.email_id: SAMPLE_EXAMPLE,
}
