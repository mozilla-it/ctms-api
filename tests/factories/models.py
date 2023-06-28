from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import factory
from factory.alchemy import SQLAlchemyModelFactory

from ctms import models
from ctms.database import ScopedSessionLocal
from tests.data import fake_stripe_id


# Pylint complains that we don't override `evaluate` in the class below, but
# neither does the class that we're subclassing from, hence the disable.
# pylint: disable-next=abstract-method
class RelatedFactoryVariableList(factory.RelatedFactoryList):
    """allows overriding ``size`` during factory usage, e.g. ParentFactory(list_factory__size=4)

    Adapted from: https://github.com/FactoryBoy/factory_boy/issues/767#issuecomment-1139185137
    """

    def call(self, instance, step, context):
        size = context.extra.pop("size", self.size)
        assert isinstance(size, int)
        return [
            super(factory.RelatedFactoryList, self).call(instance, step, context)
            for _ in range(size)
        ]


class BaseSQLAlchemyModelFactory(SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session = ScopedSessionLocal


class NewsletterFactory(BaseSQLAlchemyModelFactory):
    class Meta:
        model = models.Newsletter

    name = factory.Sequence(lambda n: f"newsletter-{n}")
    subscribed = True
    format = "T"
    lang = factory.Faker("language_code")
    source = factory.Faker("url")

    email = factory.SubFactory(factory="tests.factories.models.EmailFactory")


class WaitlistFactory(BaseSQLAlchemyModelFactory):
    class Meta:
        model = models.Waitlist

    name = factory.Sequence(lambda n: f"waitlist-{n}")
    source = factory.Faker("url")
    fields = {}

    email = factory.SubFactory(factory="tests.factories.models.EmailFactory")


class FirefoxAccountFactory(BaseSQLAlchemyModelFactory):
    class Meta:
        model = models.FirefoxAccount

    fxa_id = factory.LazyFunction(lambda: uuid4().hex)
    primary_email = factory.SelfAttribute("email.primary_email")
    created_date = factory.Faker("date")
    lang = factory.Faker("language_code")
    first_service = None
    account_deleted = False

    email = factory.SubFactory(factory="tests.factories.models.EmailFactory")


class MozillaFoundationContactFactory(BaseSQLAlchemyModelFactory):
    class Meta:
        model = models.MozillaFoundationContact

    mofo_email_id = factory.Faker("uuid4")
    mofo_contact_id = factory.Faker("uuid4")
    mofo_relevant = True

    email = factory.SubFactory(factory="tests.factories.models.EmailFactory")


class AmoAccountFactory(BaseSQLAlchemyModelFactory):
    class Meta:
        model = models.AmoAccount

    add_on_ids = "fanfox,foxfan"
    display_name = factory.Faker("user_name")
    email_opt_in = True
    language = factory.Faker("language_code")
    last_login = factory.Faker("date_object")
    location = factory.Faker("city")
    profile_url = factory.LazyAttribute(
        lambda obj: f"https://www.example.com/{obj.display_name}"
    )
    user = True
    user_id = factory.Faker("pystr", max_chars=40)
    username = factory.SelfAttribute("display_name")

    email = factory.SubFactory(factory="tests.factories.models.EmailFactory")


class EmailFactory(BaseSQLAlchemyModelFactory):
    class Meta:
        model = models.Email

    # Actual Python UUID objects, not just their string representation
    email_id = factory.LazyFunction(uuid4)
    primary_email = factory.Faker("email")
    # though this column is full of UUIDs, they're stored as strings, which is
    # what Faker generates
    basket_token = factory.Faker("uuid4")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    mailing_country = factory.Faker("country_code")
    email_format = "T"
    email_lang = factory.Faker("language_code")
    double_opt_in = False
    has_opted_out_of_email = False

    create_timestamp = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    update_timestamp = factory.LazyAttribute(lambda obj: obj.create_timestamp)

    @factory.post_generation
    def newsletters(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for _ in range(extracted):
                NewsletterFactory(email=self, **kwargs)

    @factory.post_generation
    def waitlists(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for _ in range(extracted):
                WaitlistFactory(email=self, **kwargs)

    @factory.post_generation
    def fxa(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            FirefoxAccountFactory(email=self, **kwargs)

    @factory.post_generation
    def mofo(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            MozillaFoundationContactFactory(email=self, **kwargs)

    @factory.post_generation
    def amo(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            AmoAccountFactory(email=self, **kwargs)


class PendingAcousticRecordFactory(BaseSQLAlchemyModelFactory):
    class Meta:
        model = models.PendingAcousticRecord

    retry = 0
    last_error = None
    create_timestamp = factory.LazyFunction(lambda: datetime.now(UTC))
    update_timestamp = factory.LazyAttribute(lambda obj: obj.create_timestamp)

    email = factory.SubFactory(factory=EmailFactory)


class StripeCustomerFactory(BaseSQLAlchemyModelFactory):
    class Meta:
        model = models.StripeCustomer

    stripe_id = factory.Sequence(lambda n: fake_stripe_id("cus", "customer", n))
    fxa_id = factory.SelfAttribute("fxa.fxa_id")
    default_source_id = factory.LazyFunction(
        lambda: fake_stripe_id("card", "default_payment")
    )
    invoice_settings_default_payment_method_id = factory.LazyFunction(
        lambda: fake_stripe_id("pm", "default_payment")
    )
    stripe_created = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    deleted = False

    fxa = factory.SubFactory(factory=FirefoxAccountFactory)


class StripePriceFactory(BaseSQLAlchemyModelFactory):
    class Meta:
        model = models.StripePrice

    stripe_id = factory.Sequence(lambda n: fake_stripe_id("price", "price", n))
    stripe_product_id = factory.Sequence(
        lambda n: fake_stripe_id("prod", "test_product", n)
    )
    stripe_created = factory.LazyFunction(lambda: datetime.now(UTC))
    active = True
    currency = "usd"
    recurring_interval = "month"
    recurring_interval_count = 1
    unit_amount = 1000


class StripeSubscriptionItemFactory(BaseSQLAlchemyModelFactory):
    class Meta:
        model = models.StripeSubscriptionItem

    stripe_id = factory.Sequence(lambda n: fake_stripe_id("si", "subscription_item", n))
    stripe_subscription_id = factory.SelfAttribute("subscription.stripe_id")
    stripe_created = factory.LazyFunction(lambda: datetime.now(UTC))
    stripe_price_id = factory.SelfAttribute("price.stripe_id")
    subscription = factory.SubFactory(
        factory="tests.factories.models.StripeSubscriptionFactory",
        subscription_items=None,
    )
    price = factory.SubFactory(factory=StripePriceFactory)


class StripeSubscriptionFactory(BaseSQLAlchemyModelFactory):
    class Meta:
        model = models.StripeSubscription

    stripe_id = factory.Sequence(lambda n: fake_stripe_id("sub", "subscription", n))
    stripe_customer_id = factory.LazyAttributeSequence(
        lambda obj, n: obj.customer.stripe_id
        if obj.customer
        else fake_stripe_id("cus", "customer")
    )
    default_payment_method_id = None
    default_source_id = None
    stripe_created = factory.LazyFunction(lambda: datetime.now(tz=UTC))
    cancel_at_period_end = False
    canceled_at = None
    current_period_start = factory.SelfAttribute("stripe_created")
    current_period_end = factory.LazyAttribute(
        lambda obj: obj.current_period_start + timedelta(days=30)
    )
    ended_at = None
    start_date = factory.SelfAttribute("stripe_created")
    status = "active"

    customer = factory.SubFactory(factory=StripeCustomerFactory)
    subscription_items = RelatedFactoryVariableList(
        StripeSubscriptionItemFactory,
        factory_related_name="subscription",
        size=1,
    )


class StripeInvoiceLineItemFactory(BaseSQLAlchemyModelFactory):
    class Meta:
        model = models.StripeInvoiceLineItem

    stripe_id = factory.Sequence(lambda n: fake_stripe_id("il", "invoice line item", n))
    stripe_invoice_id = factory.SelfAttribute("invoice.stripe_id")
    stripe_type = "subscription"
    stripe_price_id = factory.SelfAttribute("price.stripe_id")
    stripe_invoice_item_id = None
    stripe_subscription_id = factory.SelfAttribute(
        "subscription_item.subscription.stripe_id"
    )
    stripe_subscription_item_id = factory.SelfAttribute("subscription_item.stripe_id")
    amount = 1000
    currency = "usd"

    invoice = factory.SubFactory(
        factory="tests.factories.models.StripeInvoiceFactory", line_items=None
    )
    price = factory.SubFactory(factory=StripePriceFactory)

    # For the subscription item the subfactory below generates:
    # - set the price to the same price that's generated here.
    # - for the subscription that contains the subscription item, set the
    #   customer to the same customer that's associated with this line_item's
    #   containing invoice
    subscription_item = factory.SubFactory(
        factory=StripeSubscriptionItemFactory,
        price=factory.SelfAttribute("..price"),
        subscription__customer=factory.SelfAttribute("...invoice.customer"),
    )

    class Params:
        invoiceitem_type = factory.Trait(
            stripe_type="invoiceitem",
            invoice_item_id=factory.Sequence(
                lambda n: fake_stripe_id("ii", "invoice_item", n)
            ),
            subscription_id=None,
            subscription_item_id=None,
            subscription=None,
            subscription_item=None,
        )


class StripeInvoiceFactory(BaseSQLAlchemyModelFactory):
    class Meta:
        model = models.StripeInvoice

    stripe_id = factory.Sequence(lambda n: fake_stripe_id("inv", "invoice", n))
    stripe_customer_id = factory.SelfAttribute("customer.stripe_id")
    default_payment_method_id = None
    default_source_id = None
    stripe_created = factory.LazyFunction(lambda: datetime.now(UTC))
    currency = "usd"
    total = 1000
    status = "open"
    customer = factory.SubFactory(factory=StripeCustomerFactory)

    line_items = RelatedFactoryVariableList(
        StripeInvoiceLineItemFactory,
        factory_related_name="invoice",
        size=1,
    )


__all__ = (
    "EmailFactory",
    "FirefoxAccountFactory",
    "NewsletterFactory",
    "StripeCustomerFactory",
    "StripeInvoiceFactory",
    "StripeInvoiceLineItemFactory",
    "StripePriceFactory",
    "StripeSubscriptionFactory",
    "StripeSubscriptionItemFactory",
    "WaitlistFactory",
)
