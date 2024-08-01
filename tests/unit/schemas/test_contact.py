import pytest

from ctms.schemas.contact import ContactInSchema


@pytest.fixture
def example_contact_in(dbsession, email_factory):
    email = email_factory(
        email_format="H",
        amo=True,
        amo__display_name="foo",
        fxa=True,
        fxa__lang="en",
        mofo=True,
        newsletters=1,
        waitlists=1,
    )
    dbsession.commit()

    return ContactInSchema(
        amo=email.amo,
        email=email,
        mofo=email.mofo,
        fxa=email.fxa,
        newsletters=email.newsletters,
        waitlists=email.waitlists,
    )


def test_idempotent_equal(example_contact_in):
    contact_copy = example_contact_in.model_copy(deep=True)
    assert example_contact_in.idempotent_equal(contact_copy)
    assert contact_copy.idempotent_equal(example_contact_in)


@pytest.mark.parametrize(
    "group,field,value",
    (
        ("amo", "display_name", "bar"),
        ("email", "email_format", "T"),
        ("fxa", "lang", "es"),
        ("mofo", "mofo_relevant", False),
    ),
)
def test_change_field_not_idempotent_equal(example_contact_in, group, field, value):
    data = example_contact_in.model_dump()
    original = ContactInSchema(**data)
    assert data[group][field] != value
    data[group][field] = value
    modified = ContactInSchema(**data)
    assert not original.idempotent_equal(modified)


def test_unsubscribe_not_idempotent_equal(example_contact_in):
    data = example_contact_in.model_dump()
    original = ContactInSchema(**data)
    assert data["newsletters"][0]["subscribed"]
    data["newsletters"][0]["subscribed"] = False
    modified = ContactInSchema(**data)
    assert not original.idempotent_equal(modified)
