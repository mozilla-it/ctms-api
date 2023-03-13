import factory
from factory.alchemy import SQLAlchemyModelFactory

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


__all__ = (
    "NewsletterFactory",
    "EmailFactory",
)
