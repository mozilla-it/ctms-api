import pytest
from pydantic import ValidationError

from ctms.schemas import NewsletterSchema


def test_source_url_supports_localhost(newsletter_factory):
    newsletter = newsletter_factory(source="http://localhost:8888/v1")
    NewsletterSchema.from_orm(newsletter)


def test_source_url_does_not_support_arbitrary_string(newsletter_factory):
    newsletter = newsletter_factory(source="foobar")
    with pytest.raises(ValidationError):
        NewsletterSchema.from_orm(newsletter)
