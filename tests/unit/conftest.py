"""pytest fixtures for the CTMS app"""
import json
import os.path
from glob import glob
from typing import Callable, Optional
from unittest import mock
from uuid import UUID

import pytest
from alembic import command as alembic_command
from alembic import config as alembic_config
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry
from pydantic import PostgresDsn
from pytest_factoryboy import register
from sqlalchemy import create_engine, event
from sqlalchemy_utils.functions import create_database, database_exists, drop_database

from ctms.app import app, get_api_client, get_db, get_metrics
from ctms.background_metrics import BackgroundMetricService
from ctms.config import Settings
from ctms.crud import (
    create_api_client,
    create_contact,
    create_stripe_customer,
    create_stripe_price,
    create_stripe_subscription,
    create_stripe_subscription_item,
    get_all_acoustic_fields,
    get_all_acoustic_newsletters_mapping,
    get_amo_by_email_id,
    get_contacts_by_any_id,
    get_email,
    get_fxa_by_email_id,
    get_mofo_by_email_id,
    get_newsletters_by_email_id,
    get_stripe_products,
    get_waitlists_by_email_id,
)
from ctms.database import ScopedSessionLocal, SessionLocal
from ctms.schemas import (
    ApiClientSchema,
    ContactSchema,
    CTMSSingleResponse,
    StripeCustomerCreateSchema,
    StripePriceCreateSchema,
    StripeSubscriptionCreateSchema,
    StripeSubscriptionItemCreateSchema,
)
from tests.unit.sample_data import (
    MAXIMAL_BASKET_TOKEN,
    MAXIMAL_CONTACT_EMAIL_ID,
    MAXIMAL_FXA_ID,
    MAXIMAL_MOFO_CONTACT_ID,
    MAXIMAL_MOFO_EMAIL_ID,
    SAMPLE_CONTACTS,
    SAMPLE_MOST_MINIMAL,
    SAMPLE_STRIPE_DATA,
)

from . import factories

MY_FOLDER = os.path.dirname(__file__)
TEST_FOLDER = os.path.dirname(MY_FOLDER)
APP_FOLDER = os.path.dirname(TEST_FOLDER)


@pytest.fixture(scope="session")
def engine(pytestconfig):
    """Return a SQLAlchemy engine for a fresh test database."""

    orig_db_url = Settings().db_url
    if orig_db_url.path.endswith("test"):
        # The database ends with test, assume the caller wanted us to use it
        test_db_url = orig_db_url
        drop_db = False
        assert database_exists(test_db_url)
    else:
        # Assume the regular database was passed, create a new test database
        test_db_url = PostgresDsn.build(
            scheme=orig_db_url.scheme,
            user=orig_db_url.user,
            password=orig_db_url.password,
            host=orig_db_url.host,
            port=orig_db_url.port,
            path=orig_db_url.path + "_test",
            query=orig_db_url.query,
            fragment=orig_db_url.fragment,
        )
        drop_db = True
        # (Re)create the test database
        test_db_exists = database_exists(test_db_url)
        if test_db_exists:
            drop_database(test_db_url)
        create_database(test_db_url)

    echo = Settings().log_sqlalchemy or pytestconfig.getoption("verbose") > 2
    test_engine = create_engine(
        test_db_url,
        echo=echo,
        connect_args={"options": "-c timezone=utc"},
    )

    cfg = alembic_config.Config(os.path.join(APP_FOLDER, "alembic.ini"))

    # pylint: disable-next=unsupported-assignment-operation
    cfg.attributes["connection"] = test_engine
    alembic_command.upgrade(cfg, "head")

    yield test_engine
    test_engine.dispose()
    if drop_db:
        drop_database(test_db_url)


@pytest.fixture(scope="session")
def connection(engine):
    """Return a connection to the database that rolls back automatically."""
    conn = engine.connect()
    SessionLocal.configure(bind=conn)
    yield conn
    conn.close()


@pytest.fixture
def dbsession(connection):
    """Return a database session that rolls back.

    Adapted from https://docs.sqlalchemy.org/en/14/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites
    """
    transaction = connection.begin()
    session = ScopedSessionLocal()
    nested = connection.begin_nested()

    # If the application code calls session.commit, it will end the nested
    # transaction. Need to start a new one when that happens.
    @event.listens_for(session, "after_transaction_end")
    def end_savepoint(*args):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    yield session
    # a nescessary addition to the example in the documentation linked above.
    # Without this, the listener is not removed after each test ends and
    # SQLAlchemy emits warnings:
    #     `SAWarning: nested transaction already deassociated from connection`
    event.remove(session, "after_transaction_end", end_savepoint)
    session.close()
    transaction.rollback()


@pytest.fixture
def most_minimal_contact(dbsession):
    email_id = UUID("62d8d3c6-95f3-4ed6-b176-7f69acff22f6")
    contact = SAMPLE_MOST_MINIMAL
    assert contact.amo is None
    assert contact.fxa is None
    assert contact.mofo is None
    assert len(contact.waitlists) == 0
    assert contact.email.basket_token is None
    create_contact(dbsession, email_id, contact, get_metrics())
    dbsession.commit()
    return contact


@pytest.fixture
def minimal_contact(dbsession):
    email_id = UUID("93db83d4-4119-4e0c-af87-a713786fa81d")
    contact = SAMPLE_CONTACTS[email_id]
    assert contact.amo is None
    assert contact.fxa is None
    assert contact.mofo is None
    assert len(contact.waitlists) == 0
    create_contact(dbsession, email_id, contact, get_metrics())
    dbsession.commit()
    return contact


register(factories.EmailFactory)
register(factories.NewsletterFactory)
register(factories.WaitlistFactory)


@pytest.fixture
def _maximal_contact_email(
    dbsession, email_factory, waitlist_factory, newsletter_factory
):
    email = email_factory(
        basket_token=MAXIMAL_BASKET_TOKEN,
        create_timestamp="2010-01-01T08:04:00+00:00",
        double_opt_in=True,
        email_format="H",
        email_id=MAXIMAL_CONTACT_EMAIL_ID,
        email_lang="fr",
        first_name="Fan",
        has_opted_out_of_email=False,
        last_name="of Mozilla",
        mailing_country="ca",
        primary_email="mozilla-fan@example.com",
        sfdc_id="001A000001aMozFan",
        unsubscribe_reason="done with this mailing list",
        update_timestamp="2020-01-28T14:50:00+00:00",
        amo=True,
        amo__add_on_ids="fanfox,foxfan",
        amo__create_timestamp="2017-05-12T15:16:00+00:00",
        amo__display_name="#1 Mozilla Fan",
        amo__email_opt_in=True,
        amo__language="fr,en",
        amo__last_login="2020-01-27",
        amo__location="The Inter",
        amo__profile_url="firefox/user/14508209",
        amo__update_timestamp="2020-01-27T14:25:43+00:00",
        amo__user=True,
        amo__user_id="123",
        amo__username="Mozilla1Fan",
        fxa=True,
        fxa__created_date="2019-05-22T08:29:31.906094+00:00",
        fxa__account_deleted=False,
        fxa__first_service="monitor",
        fxa__fxa_id=MAXIMAL_FXA_ID,
        fxa__lang="fr,fr-CA",
        fxa__primary_email="fxa-firefox-fan@example.com",
        mofo=True,
        mofo__mofo_contact_id=MAXIMAL_MOFO_CONTACT_ID,
        mofo__mofo_email_id=MAXIMAL_MOFO_EMAIL_ID,
        mofo__mofo_relevant=True,
        newsletters=[
            newsletter_factory.build(
                format="H",
                lang="en",
                name="ambassadors",
                source="https://www.mozilla.org/en-US/contribute/studentambassadors/",
                subscribed=False,
                unsub_reason="Graduated, don't have time for FSA",
            ),
            newsletter_factory.build(
                format="T",
                lang="fr",
                name="common-voice",
                source="https://commonvoice.mozilla.org/fr",
                subscribed=True,
                unsub_reason=None,
            ),
            newsletter_factory.build(
                format="H",
                lang="fr",
                name="firefox-accounts-journey",
                source="https://www.mozilla.org/fr/firefox/accounts/",
                subscribed=False,
                unsub_reason="done with this mailing list",
            ),
            newsletter_factory.build(
                format="H",
                lang="en",
                name="firefox-os",
                source=None,
                subscribed=True,
                unsub_reason=None,
            ),
            newsletter_factory.build(
                format="H",
                lang="fr",
                name="hubs",
                source=None,
                subscribed=True,
                unsub_reason=None,
            ),
            newsletter_factory.build(
                format="H",
                lang="en",
                name="mozilla-festival",
                source=None,
                subscribed=True,
                unsub_reason=None,
            ),
            newsletter_factory.build(
                format="H",
                lang="fr",
                name="mozilla-foundation",
                source=None,
                subscribed=True,
                unsub_reason=None,
            ),
        ],
        waitlists=[
            waitlist_factory.build(name="relay", fields={"geo": "cn"}, source=None),
            waitlist_factory.build(
                name="vpn",
                fields={"geo": "ca", "platform": "windows,android"},
                source=None,
            ),
            waitlist_factory.build(
                name="a-software",
                fields={"geo": "fr"},
                source="https://a-software.mozilla.org/",
            ),
            waitlist_factory.build(
                fields={"geo": "fr", "platform": "win64"},
                name="super-product",
                source="https://super-product.mozilla.org/",
            ),
        ],
    )

    dbsession.commit()
    return email


@pytest.fixture
def maximal_contact(_maximal_contact_email):
    return ContactSchema(
        amo=_maximal_contact_email.amo,
        email=_maximal_contact_email,
        fxa=_maximal_contact_email.fxa,
        mofo=_maximal_contact_email.mofo,
        newsletters=_maximal_contact_email.newsletters,
        waitlists=_maximal_contact_email.waitlists,
    )


@pytest.fixture
def maximal_contact_single_response(_maximal_contact_email):
    return CTMSSingleResponse(
        amo=_maximal_contact_email.amo,
        email=_maximal_contact_email,
        fxa=_maximal_contact_email.fxa,
        mofo=_maximal_contact_email.mofo,
        newsletters=_maximal_contact_email.newsletters,
        waitlists=_maximal_contact_email.waitlists,
    )


@pytest.fixture
def example_contact(dbsession):
    email_id = UUID("332de237-cab7-4461-bcc3-48e68f42bd5c")
    contact = SAMPLE_CONTACTS[email_id]
    create_contact(dbsession, email_id, contact, get_metrics())
    dbsession.commit()
    return contact


@pytest.fixture
def sample_contacts(minimal_contact, maximal_contact, example_contact):
    return {
        "minimal": (minimal_contact.email.email_id, minimal_contact),
        "maximal": (maximal_contact.email.email_id, maximal_contact),
        "example": (example_contact.email.email_id, example_contact),
    }


@pytest.fixture
def main_acoustic_fields(dbsession):
    records = get_all_acoustic_fields(dbsession, tablename="main")
    return {r.field for r in records}


@pytest.fixture
def acoustic_newsletters_mapping(dbsession):
    records = get_all_acoustic_newsletters_mapping(dbsession)
    return {r.source: r.destination for r in records}


@pytest.fixture
def anon_client(dbsession):
    """A test client with no authorization."""

    def override_get_db():
        yield dbsession

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client(anon_client):
    """A test client that passed a valid OAuth2 token."""

    def test_api_client():
        return ApiClientSchema(
            client_id="test_client", email="test_client@example.com", enabled=True
        )

    app.dependency_overrides[get_api_client] = test_api_client
    yield anon_client
    del app.dependency_overrides[get_api_client]


@pytest.fixture
def settings():
    return Settings()


@pytest.fixture
def client_id_and_secret(dbsession):
    """Return valid OAuth2 client_id and client_secret."""
    api_client = ApiClientSchema(
        client_id="id_db_api_client", email="db_api_client@example.com", enabled=True
    )
    secret = "secret_what_a_weird_random_string"  # pragma: allowlist secret
    create_api_client(dbsession, api_client, secret)
    dbsession.flush()
    return (api_client.client_id, secret)


@pytest.fixture
def post_contact(request, client, dbsession):
    _id = (
        request.param
        if hasattr(request, "param")
        else "d1da1c99-fe09-44db-9c68-78a75752574d"
    )
    email_id = UUID(str(_id))
    contact = SAMPLE_CONTACTS[email_id]
    fields_not_written = SAMPLE_CONTACTS.get_not_written(email_id)

    def _add(
        modifier: Callable[[ContactSchema], ContactSchema] = lambda x: x,
        code: int = 201,
        stored_contacts: int = 1,
        check_redirect: bool = True,
        query_fields: Optional[dict] = None,
        check_written: bool = True,
    ):
        if query_fields is None:
            query_fields = {"primary_email": contact.email.primary_email}
        sample = contact.copy(deep=True)
        sample = modifier(sample)
        resp = client.post("/ctms", sample.json())
        assert resp.status_code == code, resp.text
        if check_redirect:
            assert resp.headers["location"] == f"/ctms/{sample.email.email_id}"
        saved = [
            ContactSchema(**c)
            for c in get_contacts_by_any_id(dbsession, **query_fields)
        ]
        assert len(saved) == stored_contacts

        # Now make sure that we skip writing default models
        def _check_written(field, getter, result_list=False):
            # We delete this field in one test case so we have to check
            # to see if it is even there
            if hasattr(sample.email, "email_id") and sample.email.email_id is not None:
                written_id = sample.email.email_id
            else:
                written_id = resp.headers["location"].split("/")[-1]
            results = getter(dbsession, written_id)
            if sample.dict().get(field) and code in {200, 201}:
                if field in fields_not_written:
                    if result_list:
                        assert (
                            results == []
                        ), f"{email_id} has field `{field}` but it is _default_ and it should _not_ have been written to db"
                    else:
                        assert (
                            results is None
                        ), f"{email_id} has field `{field}` but it is _default_ and it should _not_ have been written to db"
                else:
                    assert (
                        results
                    ), f"{email_id} has field `{field}` and it should have been written to db"
            else:
                if result_list:
                    assert (
                        results == []
                    ), f"{email_id} does not have field `{field}` and it should _not_ have been written to db"
                else:
                    assert (
                        results is None
                    ), f"{email_id} does not have field `{field}` and it should _not_ have been written to db"

        if check_written:
            _check_written("amo", get_amo_by_email_id)
            _check_written("fxa", get_fxa_by_email_id)
            _check_written("mofo", get_mofo_by_email_id)
            _check_written("newsletters", get_newsletters_by_email_id, result_list=True)
            _check_written("waitlists", get_waitlists_by_email_id, result_list=True)

        # Check that GET returns the same contact
        if code in {200, 201}:
            dbsession.expunge_all()
            get_resp = client.get(resp.headers["location"])
            assert resp.json() == get_resp.json()

        return saved, sample, email_id

    return _add


@pytest.fixture
def put_contact(request, client, dbsession):
    _id = (
        request.param
        if hasattr(request, "param")
        else "d1da1c99-fe09-44db-9c68-78a75752574d"  # SAMPLE_TO_ADD
    )
    sample_email_id = UUID(str(_id))
    _contact = SAMPLE_CONTACTS[sample_email_id]
    fields_not_written = SAMPLE_CONTACTS.get_not_written(sample_email_id)

    def _add(
        modifier: Callable[[ContactSchema], ContactSchema] = lambda x: x,
        code: int = 201,
        stored_contacts: int = 1,
        query_fields: Optional[dict] = None,
        check_written: bool = True,
        record: Optional[ContactSchema] = None,
        new_default_fields: Optional[set] = None,
    ):
        if record:
            contact = record
        else:
            contact = _contact
        if query_fields is None:
            query_fields = {"primary_email": contact.email.primary_email}
        new_default_fields = new_default_fields or set()
        sample = contact.copy(deep=True)
        sample = modifier(sample)
        resp = client.put(f"/ctms/{sample.email.email_id}", sample.json())
        assert resp.status_code == code, resp.text
        saved = [
            ContactSchema(**c)
            for c in get_contacts_by_any_id(dbsession, **query_fields)
        ]
        assert len(saved) == stored_contacts

        # Now make sure that we skip writing default models
        def _check_written(field, getter):
            # We delete this field in one test case so we have to check
            # to see if it is even there
            if hasattr(sample.email, "email_id") and sample.email.email_id is not None:
                written_id = sample.email.email_id
            else:
                written_id = resp.headers["location"].split("/")[-1]
            results = getter(dbsession, written_id)
            if sample.dict().get(field) and code in {200, 201}:
                if field in fields_not_written or field in new_default_fields:
                    assert results is None or (
                        isinstance(results, list) and len(results) == 0
                    ), f"{sample_email_id} has field `{field}` but it is _default_ and it should _not_ have been written to db"
                else:
                    assert (
                        results
                    ), f"{sample_email_id} has field `{field}` and it should have been written to db"
            else:
                assert results is None or (
                    isinstance(results, list) and len(results) == 0
                ), f"{sample_email_id} does not have field `{field}` and it should _not_ have been written to db"

        if check_written:
            _check_written("amo", get_amo_by_email_id)
            _check_written("fxa", get_fxa_by_email_id)
            _check_written("mofo", get_mofo_by_email_id)
            _check_written("newsletters", get_newsletters_by_email_id)
            _check_written("waitlists", get_waitlists_by_email_id)

        # Check that GET returns the same contact
        if code in {200, 201}:
            dbsession.expunge_all()
            get_resp = client.get(f"/ctms/{sample.email.email_id}")
            assert resp.json() == get_resp.json()

        return saved, sample, sample_email_id

    return _add


def pytest_generate_tests(metafunc):
    """Dynamicaly generate fixtures."""

    if "stripe_test_json" in metafunc.fixturenames:
        # Get names of Stripe test JSON files in test/data/stripe
        stripe_data_folder = os.path.join(TEST_FOLDER, "data", "stripe")
        test_paths = glob(os.path.join(stripe_data_folder, "*.json"))
        test_files = [os.path.basename(test_path) for test_path in test_paths]
        metafunc.parametrize("stripe_test_json", test_files, indirect=True)


@pytest.fixture
def stripe_test_json(request):
    """
    Return contents of Stripe test JSON file.

    The filenames are initialized by pytest_generate_tests.
    """
    filename = request.param
    stripe_data_folder = os.path.join(TEST_FOLDER, "data", "stripe")
    sample_filepath = os.path.join(stripe_data_folder, filename)
    with open(sample_filepath, "r", encoding="utf8") as the_file:
        data = json.load(the_file)
    return data


@pytest.fixture
def contact_with_stripe_customer(dbsession, example_contact):
    """Return the example contact with an associated Stripe Customer account."""
    create_stripe_customer(
        dbsession, StripeCustomerCreateSchema(**SAMPLE_STRIPE_DATA["Customer"])
    )
    dbsession.commit()
    return example_contact


@pytest.fixture
def contact_with_stripe_subscription(dbsession, contact_with_stripe_customer):
    create_stripe_price(
        dbsession, StripePriceCreateSchema(**SAMPLE_STRIPE_DATA["Price"])
    )
    create_stripe_subscription(
        dbsession, StripeSubscriptionCreateSchema(**SAMPLE_STRIPE_DATA["Subscription"])
    )
    create_stripe_subscription_item(
        dbsession,
        StripeSubscriptionItemCreateSchema(**SAMPLE_STRIPE_DATA["SubscriptionItem"]),
    )
    dbsession.commit()
    email = get_email(dbsession, contact_with_stripe_customer.email.email_id)
    contact_with_stripe_customer.products = get_stripe_products(email)
    return contact_with_stripe_customer


@pytest.fixture
def background_metric_service():
    """Return a BackgroundMetricService with push_to_gateway mocked."""
    service = BackgroundMetricService(CollectorRegistry(), "https://push.example.com")
    with mock.patch("ctms.background_metrics.BackgroundMetricService.push_to_gateway"):
        yield service
