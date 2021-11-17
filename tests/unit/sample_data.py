from base64 import b64encode
from datetime import datetime, timezone
from typing import Dict, Optional, Set, Tuple, Union
from uuid import UUID

from ctms.schemas import (
    AddOnsInSchema,
    AddOnsSchema,
    ContactSchema,
    EmailInSchema,
    EmailSchema,
    FirefoxAccountsSchema,
    MozillaFoundationSchema,
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
        last_login="2020-01-27",
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
        first_name="Fan",
        last_name="of Mozilla",
        mailing_country="ca",
        email_lang="fr",
        sfdc_id="001A000001aMozFan",
        double_opt_in=True,
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
    mofo=MozillaFoundationSchema(
        mofo_email_id="195207d2-63f2-4c9f-b149-80e9c408477a",
        mofo_contact_id="5e499cc0-eeb5-4f0e-aae6-a101721874b8",
        mofo_relevant=True,
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
    examples = {}
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
    newsletters=ContactSchema.schema()["properties"]["newsletters"]["example"],
)

SAMPLE_TO_ADD = ContactSchema(
    email=EmailInSchema(
        basket_token="21aeb466-4003-4c2b-a27e-e6651c13d231",
        email_id=UUID("d1da1c99-fe09-44db-9c68-78a75752574d"),
        mailing_country="us",
        primary_email="ctms-user-to-be-created@example.com",
        sfdc_id="002A000001aBAcDEFA",
    )
)

SAMPLE_WITH_SIMPLE_DEFAULT = ContactSchema(
    email=EmailInSchema(
        basket_token="d3a827b5-747c-41c2-8381-59ce9ad63050",
        email_id=UUID("4f98b303-8863-421f-95d3-847cd4d83c9f"),
        mailing_country="us",
        primary_email="with-defaults@example.com",
        sfdc_id="102A000001aBAcDEFA",
    ),
    amo=AddOnsInSchema(),
)

SAMPLE_WITH_DEFAULT_NEWSLETTER = ContactSchema(
    email=EmailInSchema(
        basket_token="b5487fbf-86ae-44b9-a638-bbb037ce61a6",
        email_id=UUID("dd2bc52c-49e4-4df9-95a8-197d3a7794cd"),
        mailing_country="us",
        primary_email="with-default-newsletter@example.com",
        sfdc_id="102A000001aBAcDEFA",
    ),
    newsletters=[],
)


class ContactVendor:
    # Second item of tuples is a set of keys that should _not_ be written
    # to the db when this sample is posted
    contacts: Dict[Union[UUID, str], Tuple[ContactSchema, Set[str]]] = {
        SAMPLE_MINIMAL.email.email_id: (SAMPLE_MINIMAL, set()),
        SAMPLE_MAXIMAL.email.email_id: (SAMPLE_MAXIMAL, set()),
        SAMPLE_EXAMPLE.email.email_id: (SAMPLE_EXAMPLE, set()),
        SAMPLE_TO_ADD.email.email_id: (SAMPLE_TO_ADD, set()),
        SAMPLE_WITH_SIMPLE_DEFAULT.email.email_id: (
            SAMPLE_WITH_SIMPLE_DEFAULT,
            {"amo"},
        ),
        SAMPLE_WITH_DEFAULT_NEWSLETTER.email.email_id: (
            SAMPLE_WITH_DEFAULT_NEWSLETTER,
            {"newsletters"},
        ),
    }

    def __getitem__(self, key: str) -> ContactSchema:
        contact: ContactSchema = self.contacts[key][0].copy(deep=True)
        return contact

    def get_not_written(self, key: str) -> Set[str]:
        return self.contacts[key][1]

    def keys(self):
        return list(self.contacts.keys())


SAMPLE_CONTACTS = ContactVendor()


def fake_stripe_id(prefix: str, seed: str, suffix: Optional[str] = None) -> str:
    """Create a fake Stripe ID for testing"""
    body = b64encode(seed.encode()).decode().replace("=", "")
    return f"{prefix}_{body}{suffix if suffix else ''}"


# Documentation and test Stripe IDs
FAKE_STRIPE_ID = {
    "Customer": fake_stripe_id("cus", "customer"),
    "Invoice": fake_stripe_id("in", "invoice"),
    "(Invoice) Line Item": fake_stripe_id("il", "invoice line item"),
    "Payment Method": fake_stripe_id("pm", "payment_method"),
    "Price": fake_stripe_id("price", "price"),
    "Product": fake_stripe_id("prod", "product"),
    "Subscription": fake_stripe_id("sub", "subscription"),
    "Subscription Item": fake_stripe_id("si", "subscription_item"),
}

# Sample data to pass to Stripe[Object]CreateSchema
SAMPLE_STRIPE_DATA = {
    "Customer": {
        "stripe_id": FAKE_STRIPE_ID["Customer"],
        "stripe_created": datetime(2021, 10, 25, 15, 34, tzinfo=timezone.utc),
        "fxa_id": SAMPLE_EXAMPLE.fxa.fxa_id,
        "default_source_id": None,
        "invoice_settings_default_payment_method_id": FAKE_STRIPE_ID["Payment Method"],
    },
    "Subscription": {
        "stripe_id": FAKE_STRIPE_ID["Subscription"],
        "stripe_created": datetime(2021, 9, 27, tzinfo=timezone.utc),
        "stripe_customer_id": FAKE_STRIPE_ID["Customer"],
        "default_source_id": None,
        "default_payment_method_id": None,
        "cancel_at_period_end": False,
        "canceled_at": None,
        "current_period_start": datetime(2021, 10, 27, tzinfo=timezone.utc),
        "current_period_end": datetime(2021, 11, 27, tzinfo=timezone.utc),
        "ended_at": None,
        "start_date": datetime(2021, 9, 27, tzinfo=timezone.utc),
        "status": "active",
    },
    "SubscriptionItem": {
        "stripe_id": FAKE_STRIPE_ID["Subscription Item"],
        "stripe_created": datetime(2021, 9, 27, tzinfo=timezone.utc),
        "stripe_subscription_id": FAKE_STRIPE_ID["Subscription"],
        "stripe_price_id": FAKE_STRIPE_ID["Price"],
    },
    "Price": {
        "stripe_id": FAKE_STRIPE_ID["Price"],
        "stripe_created": datetime(2020, 10, 27, 10, 45, tzinfo=timezone.utc),
        "stripe_product_id": FAKE_STRIPE_ID["Product"],
        "active": True,
        "currency": "usd",
        "recurring_interval": "month",
        "recurring_interval_count": 1,
        "unit_amount": 999,
    },
    "Invoice": {
        "stripe_id": FAKE_STRIPE_ID["Invoice"],
        "stripe_created": datetime(2021, 10, 28, tzinfo=timezone.utc),
        "stripe_customer_id": FAKE_STRIPE_ID["Customer"],
        "default_source_id": None,
        "default_payment_method_id": None,
        "currency": "usd",
        "total": 1000,
        "status": "open",
    },
    "InvoiceLineItem": {
        "stripe_id": FAKE_STRIPE_ID["(Invoice) Line Item"],
        "stripe_price_id": FAKE_STRIPE_ID["Price"],
        "stripe_invoice_id": FAKE_STRIPE_ID["Invoice"],
        "stripe_subscription_id": FAKE_STRIPE_ID["Subscription"],
        "stripe_subscription_item_id": FAKE_STRIPE_ID["Subscription Item"],
        "stripe_type": "subscription",
        "amount": 1000,
        "currency": "usd",
    },
}
