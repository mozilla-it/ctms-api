from datetime import UTC, datetime
from uuid import uuid4

import factory
from factory.alchemy import SQLAlchemyModelFactory

from ctms import models
from ctms.database import ScopedSessionLocal


class RelatedFactoryVariableList(factory.RelatedFactoryList):
    """allows overriding ``size`` during factory usage, e.g. ParentFactory(list_factory__size=4)

    Adapted from: https://github.com/FactoryBoy/factory_boy/issues/767#issuecomment-1139185137
    """

    def call(self, instance, step, context):
        size = context.extra.pop("size", self.size)
        assert isinstance(size, int)
        return [super(factory.RelatedFactoryList, self).call(instance, step, context) for _ in range(size)]


class BaseSQLAlchemyModelFactory(SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session = ScopedSessionLocal
        sqlalchemy_session_persistence = "commit"


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
    subscribed = True

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
        lambda obj: f"https://ex.com/{obj.display_name}",
    )
    user = True
    user_id = factory.Faker("pystr", max_chars=40)
    username = factory.SelfAttribute("display_name")

    email = factory.SubFactory(factory="tests.factories.models.EmailFactory")


class EmailFactory(BaseSQLAlchemyModelFactory):
    class Meta:
        model = models.Email

    primary_email = factory.Faker("email")
    # though this column is full of UUIDs, they're stored as strings, which is
    # what Faker generates
    basket_token = factory.Faker("uuid4")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    mailing_country = factory.Faker("country_code")
    email_format = "H"
    email_lang = factory.Faker("language_code")
    double_opt_in = False
    has_opted_out_of_email = False

    create_timestamp = factory.LazyFunction(lambda: datetime.now(UTC))
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

    class Params:
        with_fxa = factory.Trait(
            fxa=factory.RelatedFactory(
                FirefoxAccountFactory,
                factory_related_name="email",
            )
        )
        with_amo = factory.Trait(
            amo=factory.RelatedFactory(
                AmoAccountFactory,
                factory_related_name="email",
            )
        )
        with_mofo = factory.Trait(
            mofo=factory.RelatedFactory(
                MozillaFoundationContactFactory,
                factory_related_name="email",
            )
        )


__all__ = (
    "EmailFactory",
    "FirefoxAccountFactory",
    "NewsletterFactory",
    "WaitlistFactory",
)
