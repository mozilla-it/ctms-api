import pytest
from pydantic import ValidationError

from ctms.schemas import NewsletterSchema


def test_source_url_supports_localhost(newsletter_factory):
    newsletter = newsletter_factory.build(source="http://localhost:8888/v1")
    NewsletterSchema.model_validate(newsletter)


def test_source_url_does_not_support_arbitrary_string(newsletter_factory):
    newsletter = newsletter_factory.build(source="foobar")
    with pytest.raises(ValidationError):
        NewsletterSchema.model_validate(newsletter)
