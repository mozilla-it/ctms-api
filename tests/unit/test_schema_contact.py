import pytest

from ctms.schemas.contact import ContactInSchema
from tests.unit.sample_data import SAMPLE_MAXIMAL


def test_idempotent_equal():
    data = SAMPLE_MAXIMAL.dict()
    original = ContactInSchema(**data)
    modified = ContactInSchema(**data)
    assert original.idempotent_equal(modified)
    assert modified.idempotent_equal(original)


@pytest.mark.parametrize(
    "group,field,value",
    (
        ("amo", "display_name", "changed"),
        ("email", "email_format", "T"),
        ("fxa", "lang", "es"),
        ("mofo", "mofo_relevant", False),
    ),
)
def test_change_field_not_idempotent_equal(group, field, value):
    data = SAMPLE_MAXIMAL.dict()
    original = ContactInSchema(**data)
    assert data[group][field] != value
    data[group][field] = value
    modified = ContactInSchema(**data)
    assert not original.idempotent_equal(modified)


def test_unsubscribe_not_idempotent_equal():
    data = SAMPLE_MAXIMAL.dict()
    original = ContactInSchema(**data)
    assert not data["newsletters"][0]["subscribed"]
    data["newsletters"][0]["subscribed"] = True
    modified = ContactInSchema(**data)
    assert not original.idempotent_equal(modified)
