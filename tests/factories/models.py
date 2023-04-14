from datetime import datetime, timezone
from uuid import uuid4

import factory
from factory.alchemy import SQLAlchemyModelFactory

from ctms import models
from ctms.database import ScopedSessionLocal
from tests.data import fake_stripe_id


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
    first_service = factory.Faker("random_element", elements=["Firefox"])
    account_deleted = factory.Faker("boolean", chance_of_getting_true=30)

    email = factory.SubFactory(factory="tests.factories.models.EmailFactory")


class EmailFactory(BaseSQLAlchemyModelFactory):
    class Meta:
        model = models.Email

    email_id = factory.Faker("uuid4")
    primary_email = factory.Faker("email")
    basket_token = factory.Faker("uuid4")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    mailing_country = factory.Faker("country_code")
    email_format = "T"
    email_lang = factory.Faker("language_code")
    double_opt_in = False
    has_opted_out_of_email = False

    @factory.post_generation
    def newsletters(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for _ in range(extracted):
                NewsletterFactory(email=self, **kwargs)

    @factory.post_generation
    def fxa(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            FirefoxAccountFactory(email=self, **kwargs)


class StripeCustomerFactory(BaseSQLAlchemyModelFactory):
    class Meta:
        model = models.StripeCustomer

    stripe_id = factory.LazyFunction(lambda: fake_stripe_id("cus", "customer"))
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


__all__ = (
    "EmailFactory",
    "FirefoxAccountFactory",
    "NewsletterFactory",
    "StripeCustomerFactory",
    "WaitlistFactory",
)
