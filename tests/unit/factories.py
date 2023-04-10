import factory
from factory.alchemy import SQLAlchemyModelFactory
from faker import Faker

from ctms import models
from ctms.database import ScopedSessionLocal


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

    email = factory.SubFactory(factory="tests.unit.factories.EmailFactory")


class WaitlistFactory(BaseSQLAlchemyModelFactory):
    class Meta:
        model = models.Waitlist

    name = factory.Sequence(lambda n: f"waitlist-{n}")
    source = factory.Faker("url")
    fields = {}

    email = factory.SubFactory(factory="tests.unit.factories.EmailFactory")


class FirefoxAccountFactory(BaseSQLAlchemyModelFactory):
    class Meta:
        model = models.FirefoxAccount

    fxa_id = factory.Faker("uuid4")
    primary_email = factory.Faker("email")
    created_date = factory.Faker("date")
    lang = factory.Faker("language_code")
    first_service = factory.Faker("word")
    account_deleted = False

    email = factory.SubFactory(factory="tests.unit.factories.EmailFactory")


class AmoAccountFactory(BaseSQLAlchemyModelFactory):
    class Meta:
        model = models.AmoAccount

    add_on_ids = factory.LazyAttribute(
        lambda _: ",".join([Faker().word() for _ in range(2)])
    )
    display_name = factory.Faker("name")
    email_opt_in = True
    language = factory.Faker("language_code")
    last_login = factory.Faker("date")
    location = factory.Faker("city")
    profile_url = factory.Faker("url")
    user = True
    user_id = factory.Faker("uuid4")
    username = factory.Faker("user_name")

    email = factory.SubFactory(factory="tests.unit.factories.EmailFactory")


class MozillaFoundationContactFactory(BaseSQLAlchemyModelFactory):
    class Meta:
        model = models.MozillaFoundationContact

    mofo_email_id = factory.Faker("email")
    mofo_contact_id = factory.Faker("uuid4")
    mofo_relevant = True

    email = factory.SubFactory(factory="tests.unit.factories.EmailFactory")


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
    def fxa(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            FirefoxAccountFactory(email=self, **kwargs)

    @factory.post_generation
    def amo(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            AmoAccountFactory(email=self, **kwargs)

    @factory.post_generation
    def mofo(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            MozillaFoundationContactFactory(email=self, **kwargs)

    @factory.post_generation
    def newsletters(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            if isinstance(extracted, list):
                self.newsletters.extend(extracted)
            elif isinstance(extracted, int):
                for _ in range(extracted):
                    NewsletterFactory(email=self, **kwargs)
            else:
                raise ValueError(
                    "newsletters should be number of newsletters to be created (int) or list of Newsletter objects"
                )

    @factory.post_generation
    def waitlists(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            if isinstance(extracted, list):
                self.waitlists.extend(extracted)
            elif isinstance(extracted, int):
                for _ in range(extracted):
                    WaitlistFactory(email=self, **kwargs)
            else:
                raise ValueError(
                    "waitlists should be number of waitlists to be created (int) or list of Waitlist objects"
                )


__all__ = (
    "NewsletterFactory",
    "WaitlistFactory",
    "AmoAccountFactory",
    "FirefoxAccountFactory",
    "MozillaFoundationContactFactory",
    "EmailFactory",
)
