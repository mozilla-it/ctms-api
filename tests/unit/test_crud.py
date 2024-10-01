"""Test database operations"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import sqlalchemy

from ctms.crud import (
    count_total_contacts,
    create_amo,
    create_email,
    create_fxa,
    create_mofo,
    create_newsletter,
    create_or_update_contact,
    get_bulk_contacts,
    get_contact_by_email_id,
    get_contacts_by_any_id,
    get_contacts_from_newsletter,
    get_contacts_from_waitlist,
    get_email,
)
from ctms.database import ScopedSessionLocal
from ctms.models import Email
from ctms.schemas import (
    AddOnsInSchema,
    EmailInSchema,
    FirefoxAccountsInSchema,
    MozillaFoundationInSchema,
    NewsletterInSchema,
)
from ctms.schemas.contact import ContactPutSchema
from ctms.schemas.waitlist import WaitlistInSchema

# Treat all SQLAlchemy warnings as errors
pytestmark = pytest.mark.filterwarnings("error::sqlalchemy.exc.SAWarning")


@pytest.mark.disable_autouse
def test_email_count(connection, email_factory):
    # In this test, we manipulate raw connections and transactions because
    # we need to force a VACUUM operation outside a running transaction.
    # To do so, we mark the tests with `disable_autouse` since the `dbsession`
    # fixture is configured with `autouse=True`

    # Insert contacts in the table.
    with ScopedSessionLocal() as session:
        email_factory.create_batch(3)
        session.commit()

    # Force an analysis of the table.
    old_isolation_level = connection.connection.isolation_level
    connection.connection.set_isolation_level(0)
    session.execute(sqlalchemy.text(f"VACUUM ANALYZE {Email.__tablename__}"))
    session.close()
    connection.connection.set_isolation_level(old_isolation_level)

    # Query the count result (since last analyze)
    with ScopedSessionLocal() as session:
        count = count_total_contacts(session)
        assert count == 3

        # Delete created objects (since our transaction was not rolledback automatically)
        session.query(Email).delete()
        session.commit()


def test_get_email(dbsession, email_factory):
    email = email_factory()

    fetched_email = get_email(dbsession, email.email_id)
    assert fetched_email.email_id == email.email_id


def test_get_email_miss(dbsession):
    email = get_email(dbsession, str(uuid4()))
    assert email is None


def test_get_contact_by_email_id_found(dbsession, email_factory):
    email = email_factory()

    contact = get_contact_by_email_id(dbsession, email.email_id)

    assert contact.email.email_id == email.email_id


def test_get_contact_by_email_id_miss(dbsession):
    contact = get_contact_by_email_id(dbsession, str(uuid4()))
    assert contact is None


@pytest.mark.parametrize(
    "mofo_relevant_flag,num_contacts_returned",
    [
        (None, 3),
        (True, 1),
        (False, 2),
    ],
)
def test_get_bulk_contacts_mofo_relevant(
    dbsession, email_factory, mofo_relevant_flag, num_contacts_returned
):
    email_factory()
    email_factory(with_mofo=True, mofo__mofo_relevant=True)
    email_factory(with_mofo=True, mofo__mofo_relevant=False)

    contacts = get_bulk_contacts(
        dbsession,
        start_time=datetime.now(timezone.utc) - timedelta(minutes=1),
        end_time=datetime.now(timezone.utc) + timedelta(minutes=1),
        limit=3,
        mofo_relevant=mofo_relevant_flag,
    )
    assert len(contacts) == num_contacts_returned


def test_get_bulk_contacts_time_bounds(dbsession, email_factory):
    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(minutes=2)

    email_factory(update_timestamp=start_time - timedelta(minutes=1))
    targets = [
        email_factory(update_timestamp=start_time),
        email_factory(update_timestamp=start_time + timedelta(minutes=1)),
    ]
    email_factory(update_timestamp=end_time)
    email_factory(update_timestamp=end_time + timedelta(minutes=1))

    contacts = get_bulk_contacts(
        dbsession,
        start_time=datetime.now(timezone.utc) - timedelta(minutes=1),
        end_time=datetime.now(timezone.utc) + timedelta(minutes=1),
        limit=5,
    )

    assert len(contacts) == 2
    target_email_ids = [target.email_id for target in targets]
    contact_email_ids = [contact.email.email_id for contact in contacts]
    assert set(target_email_ids) == set(contact_email_ids)


def test_get_bulk_contacts_limited(dbsession, email_factory):
    email_factory.create_batch(10)

    contacts = get_bulk_contacts(
        dbsession,
        start_time=datetime.now(timezone.utc) - timedelta(minutes=1),
        end_time=datetime.now(timezone.utc) + timedelta(minutes=1),
        limit=5,
    )
    assert len(contacts) == 5


def test_get_bulk_contacts_after_email_id(dbsession, email_factory):
    first_email = email_factory()
    second_email = email_factory()

    [contact] = get_bulk_contacts(
        dbsession,
        start_time=datetime.now(timezone.utc) - timedelta(minutes=1),
        end_time=datetime.now(timezone.utc) + timedelta(minutes=1),
        limit=1,
        after_email_id=str(first_email.email_id),
    )
    assert contact.email.email_id != first_email.email_id
    assert contact.email.email_id == second_email.email_id


def test_get_bulk_contacts_one(dbsession, email_factory):
    email = email_factory()

    [contact] = get_bulk_contacts(
        dbsession,
        start_time=datetime.now(timezone.utc) - timedelta(minutes=1),
        end_time=datetime.now(timezone.utc) + timedelta(minutes=1),
        limit=10,
    )
    assert contact.email.email_id == email.email_id


def test_get_bulk_contacts_none(dbsession):
    bulk_contact_list = get_bulk_contacts(
        dbsession,
        start_time=datetime.now(timezone.utc) + timedelta(days=1),
        end_time=datetime.now(timezone.utc) + timedelta(days=1),
        limit=10,
    )
    assert bulk_contact_list == []


@pytest.mark.parametrize(
    "alt_id_name,alt_id_value",
    [
        ("email_id", "67e52c77-950f-4f28-accb-bb3ea1a2c51a"),
        ("primary_email", "mozilla-fan@example.com"),
        ("amo_user_id", "123"),
        ("basket_token", "d9ba6182-f5dd-4728-a477-2cc11bf62b69"),
        ("fxa_id", "611b6788-2bba-42a6-98c9-9ce6eb9cbd34"),
        ("fxa_primary_email", "fxa-firefox-fan@example.com"),
        ("sfdc_id", "001A000001aMozFan"),
        ("mofo_contact_id", "5e499cc0-eeb5-4f0e-aae6-a101721874b8"),
        ("mofo_email_id", "195207d2-63f2-4c9f-b149-80e9c408477a"),
    ],
)
def test_get_contact_by_any_id(dbsession, email_factory, alt_id_name, alt_id_value):
    email = email_factory(
        email_id="67e52c77-950f-4f28-accb-bb3ea1a2c51a",
        primary_email="mozilla-fan@example.com",
        basket_token="d9ba6182-f5dd-4728-a477-2cc11bf62b69",
        sfdc_id="001A000001aMozFan",
        with_fxa=True,
        fxa__fxa_id="611b6788-2bba-42a6-98c9-9ce6eb9cbd34",
        fxa__primary_email="fxa-firefox-fan@example.com",
        with_amo=True,
        amo__user_id="123",
        with_mofo=True,
        mofo__mofo_contact_id="5e499cc0-eeb5-4f0e-aae6-a101721874b8",
        mofo__mofo_email_id="195207d2-63f2-4c9f-b149-80e9c408477a",
    )
    email_factory.create_batch(2, with_fxa=True, with_amo=True, with_mofo=True)

    [contact] = get_contacts_by_any_id(dbsession, **{alt_id_name: alt_id_value})
    assert contact.email.email_id == email.email_id


def test_get_contact_by_any_id_missing(dbsession, email_factory):
    # create an email
    email_factory()
    # but use a different (random) UUID as the basket token
    contact = get_contacts_by_any_id(dbsession, basket_token=str(uuid4()))
    assert len(contact) == 0


@pytest.mark.parametrize(
    "alt_id_name,alt_id_value",
    [
        ("amo_user_id", "123"),
        ("fxa_primary_email", "fxa-firefox-fan@example.com"),
        ("sfdc_id", "001A000001aMozFan"),
        ("mofo_contact_id", "5e499cc0-eeb5-4f0e-aae6-a101721874b8"),
    ],
)
def test_get_multiple_contacts_by_any_id(
    dbsession, email_factory, alt_id_name, alt_id_value
):
    """Two contacts can share the same:
    - fxa primary_email
    - amo user_id
    - sfdc_id
    - mofo_contact_id

    And when we query users by these ids, we might get multiple contacts back
    """
    email_factory.create_batch(
        2,
        sfdc_id="001A000001aMozFan",
        with_amo=True,
        amo__user_id=123,
        with_fxa=True,
        fxa__primary_email="fxa-firefox-fan@example.com",
        with_mofo=True,
        mofo__mofo_contact_id="5e499cc0-eeb5-4f0e-aae6-a101721874b8",
    )
    [contact_a, contact_b] = get_contacts_by_any_id(
        dbsession, **{alt_id_name: alt_id_value}
    )
    assert contact_a.email.email_id != contact_b.email.email_id


def test_create_or_update_contact_related_objects(dbsession, email_factory):
    email = email_factory(
        newsletters=3,
        waitlists=3,
    )
    dbsession.flush()

    new_source = "http://waitlists.example.com/"
    putdata = ContactPutSchema(
        email=EmailInSchema(email_id=email.email_id, primary_email=email.primary_email),
        newsletters=[
            NewsletterInSchema(name=email.newsletters[0].name, source=new_source)
        ],
        waitlists=[WaitlistInSchema(name=email.waitlists[0].name, source=new_source)],
    )
    create_or_update_contact(dbsession, email.email_id, putdata, None)
    dbsession.commit()

    updated_email = dbsession.get(Email, email.email_id)
    # Existing related objects were deleted and replaced by the specified list.
    assert len(updated_email.newsletters) == 1
    assert len(updated_email.waitlists) == 1
    assert updated_email.newsletters[0].source == new_source
    assert updated_email.waitlists[0].source == new_source


def test_create_or_update_contact_timestamps(dbsession, email_factory):
    email = email_factory(
        newsletters=1,
        waitlists=1,
    )
    dbsession.flush()

    before_nl = email.newsletters[0].update_timestamp
    before_wl = email.waitlists[0].update_timestamp

    new_source = "http://waitlists.example.com"
    putdata = ContactPutSchema(
        email=EmailInSchema(email_id=email.email_id, primary_email=email.primary_email),
        newsletters=[
            NewsletterInSchema(name=email.newsletters[0].name, source=new_source)
        ],
        waitlists=[WaitlistInSchema(name=email.waitlists[0].name, source=new_source)],
    )
    create_or_update_contact(dbsession, email.email_id, putdata, None)
    dbsession.commit()

    updated_email = get_email(dbsession, email.email_id)
    assert updated_email.newsletters[0].update_timestamp > before_nl
    assert updated_email.waitlists[0].update_timestamp > before_wl


def test_get_contacts_from_newsletter(dbsession, newsletter_factory):
    existing_newsletter = newsletter_factory()
    dbsession.flush()
    contacts = get_contacts_from_newsletter(dbsession, existing_newsletter.name)
    assert len(contacts) == 1
    assert contacts[0].email.email_id == existing_newsletter.email.email_id


def test_get_contacts_from_waitlist(dbsession, waitlist_factory):
    existing_waitlist = waitlist_factory()
    dbsession.flush()
    contacts = get_contacts_from_waitlist(dbsession, existing_waitlist.name)
    assert len(contacts) == 1
    assert contacts[0].email.email_id == existing_waitlist.email.email_id
