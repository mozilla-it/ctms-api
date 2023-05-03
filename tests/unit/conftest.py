"""pytest fixtures for the CTMS app"""
import json
import os.path
from datetime import datetime, timezone
from glob import glob
from time import mktime
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

from ctms import schemas
from ctms.app import app, get_api_client, get_db, get_metrics
from ctms.background_metrics import BackgroundMetricService
from ctms.config import Settings
from ctms.crud import (
    create_api_client,
    create_contact,
    create_stripe_price,
    create_stripe_subscription,
    create_stripe_subscription_item,
    get_all_acoustic_fields,
    get_all_acoustic_newsletters_mapping,
    get_amo_by_email_id,
    get_contact_by_email_id,
    get_contacts_by_any_id,
    get_fxa_by_email_id,
    get_mofo_by_email_id,
    get_newsletters_by_email_id,
    get_waitlists_by_email_id,
)
from ctms.database import ScopedSessionLocal, SessionLocal
from ctms.schemas import (
    ApiClientSchema,
    ContactSchema,
    StripePriceCreateSchema,
    StripeSubscriptionCreateSchema,
    StripeSubscriptionItemCreateSchema,
)
from tests import factories
from tests.data import fake_stripe_id

MY_FOLDER = os.path.dirname(__file__)
TEST_FOLDER = os.path.dirname(MY_FOLDER)
APP_FOLDER = os.path.dirname(TEST_FOLDER)

# Common test cases to use in parameterized tests
# List of tuples comprised of name fixture name (defined below) and fields to
# be overwritten, if any
SAMPLE_CONTACT_PARAMS = [
    ("minimal_contact_data", set()),
    ("maximal_contact_data", set()),
    ("example_contact_data", set()),
    ("to_add_contact_data", set()),
    ("simple_default_contact_data", {"amo"}),
    ("default_newsletter_contact_data", {"newsletters"}),
]

FAKE_STRIPE_CUSTOMER_ID = fake_stripe_id("cus", "customer")
FAKE_STRIPE_INVOICE_ID = fake_stripe_id("in", "invoice")
FAKE_STRIPE_PRICE_ID = fake_stripe_id("price", "price")
FAKE_STRIPE_SUBSCRIPTION_ID = fake_stripe_id("sub", "subscription")


def _gather_examples(schema_class) -> dict[str, str]:
    """Gather the examples from a schema definition"""
    examples = {}
    for key, props in schema_class.schema()["properties"].items():
        if "example" in props:
            examples[key] = props["example"]
    return examples


def unix_timestamp(the_time: Optional[datetime] = None) -> int:
    """Create a UNIX timestamp from a datetime or now"""
    the_time = the_time or datetime.now(tz=timezone.utc)
    return int(mktime(the_time.timetuple()))


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


# Database models
register(factories.models.EmailFactory)
register(factories.models.NewsletterFactory)
register(factories.models.StripeCustomerFactory)
register(factories.models.WaitlistFactory)
# Stripe REST API payloads
register(factories.stripe.StripeCustomerDataFactory)


@pytest.fixture
def most_minimal_contact(dbsession):
    contact = ContactSchema(
        email=schemas.EmailSchema(
            email_id=UUID("62d8d3c6-95f3-4ed6-b176-7f69acff22f6"),
            primary_email="ctms-most-minimal-user@example.com",
        ),
    )
    create_contact(dbsession, contact.email.email_id, contact, get_metrics())
    dbsession.commit()
    return contact


@pytest.fixture
def minimal_contact_data():
    return ContactSchema(
        email=schemas.EmailSchema(
            basket_token="142e20b6-1ef5-43d8-b5f4-597430e956d7",
            create_timestamp="2014-01-22T15:24:00+00:00",
            email_id=UUID("93db83d4-4119-4e0c-af87-a713786fa81d"),
            mailing_country="us",
            primary_email="ctms-user@example.com",
            sfdc_id="001A000001aABcDEFG",
            update_timestamp="2020-01-22T15:24:00.000+0000",
        ),
        newsletters=[
            {"name": "app-dev"},
            {"name": "maker-party"},
            {"name": "mozilla-foundation"},
            {"name": "mozilla-learning-network"},
        ],
    )


@pytest.fixture
def minimal_contact(minimal_contact_data, dbsession):
    create_contact(
        dbsession,
        minimal_contact_data.email.email_id,
        minimal_contact_data,
        get_metrics(),
    )
    dbsession.commit()
    return minimal_contact_data


@pytest.fixture
def maximal_contact_data():
    return ContactSchema(
        amo=schemas.AddOnsSchema(
            add_on_ids="fanfox,foxfan",
            display_name="#1 Mozilla Fan",
            email_opt_in=True,
            language="fr,en",
            last_login="2020-01-27",
            location="The Inter",
            profile_url="firefox/user/14508209",
            sfdc_id="001A000001aMozFan",
            user=True,
            user_id="123",
            username="Mozilla1Fan",
            create_timestamp="2017-05-12T15:16:00+00:00",
            update_timestamp="2020-01-27T14:25:43+00:00",
        ),
        email=schemas.EmailSchema(
            email_id=UUID("67e52c77-950f-4f28-accb-bb3ea1a2c51a"),
            primary_email="mozilla-fan@example.com",
            basket_token=UUID("d9ba6182-f5dd-4728-a477-2cc11bf62b69"),
            first_name="Fan",
            last_name="of Mozilla",
            mailing_country="ca",
            email_lang="fr",
            sfdc_id="001A000001aMozFan",
            double_opt_in=True,
            unsubscribe_reason="done with this mailing list",
            create_timestamp="2010-01-01T08:04:00+00:00",
            update_timestamp="2020-01-28T14:50:00.000+0000",
        ),
        fxa=schemas.FirefoxAccountsSchema(
            created_date="2019-05-22T08:29:31.906094+00:00",
            fxa_id="611b6788-2bba-42a6-98c9-9ce6eb9cbd34",
            lang="fr,fr-CA",
            primary_email="fxa-firefox-fan@example.com",
            first_service="monitor",
        ),
        mofo=schemas.MozillaFoundationSchema(
            mofo_email_id="195207d2-63f2-4c9f-b149-80e9c408477a",
            mofo_contact_id="5e499cc0-eeb5-4f0e-aae6-a101721874b8",
            mofo_relevant=True,
        ),
        newsletters=[
            schemas.NewsletterSchema(
                name="ambassadors",
                source="https://www.mozilla.org/en-US/contribute/studentambassadors/",
                subscribed=False,
                unsub_reason="Graduated, don't have time for FSA",
            ),
            schemas.NewsletterSchema(
                name="common-voice",
                format="T",
                lang="fr",
                source="https://commonvoice.mozilla.org/fr",
            ),
            schemas.NewsletterSchema(
                name="firefox-accounts-journey",
                source="https://www.mozilla.org/fr/firefox/accounts/",
                lang="fr",
                subscribed=False,
                unsub_reason="done with this mailing list",
            ),
            schemas.NewsletterSchema(name="firefox-os"),
            schemas.NewsletterSchema(name="hubs", lang="fr"),
            schemas.NewsletterSchema(name="mozilla-festival"),
            schemas.NewsletterSchema(name="mozilla-foundation", lang="fr"),
        ],
        waitlists=[
            schemas.WaitlistSchema(
                name="a-software",
                source="https://a-software.mozilla.org/",
                fields={"geo": "fr"},
            ),
            schemas.WaitlistSchema(
                name="relay",
                fields={"geo": "cn"},
            ),
            schemas.WaitlistSchema(
                name="super-product",
                source="https://super-product.mozilla.org/",
                fields={"geo": "fr", "platform": "win64"},
            ),
            schemas.WaitlistSchema(
                name="vpn",
                fields={
                    "geo": "ca",
                    "platform": "windows,android",
                },
            ),
        ],
    )


@pytest.fixture
def maximal_contact(dbsession, maximal_contact_data):
    create_contact(
        dbsession,
        maximal_contact_data.email.email_id,
        maximal_contact_data,
        get_metrics(),
    )
    dbsession.commit()
    return maximal_contact_data


@pytest.fixture
def example_contact_data():
    return ContactSchema(
        amo=schemas.AddOnsSchema(**_gather_examples(schemas.AddOnsSchema)),
        email=schemas.EmailSchema(**_gather_examples(schemas.EmailSchema)),
        fxa=schemas.FirefoxAccountsSchema(
            **_gather_examples(schemas.FirefoxAccountsSchema)
        ),
        newsletters=ContactSchema.schema()["properties"]["newsletters"]["example"],
        waitlists=[
            schemas.WaitlistSchema(**example)
            for example in ContactSchema.schema()["properties"]["waitlists"]["example"]
        ],
    )


@pytest.fixture
def example_contact(dbsession, example_contact_data):
    create_contact(
        dbsession,
        example_contact_data.email.email_id,
        example_contact_data,
        get_metrics(),
    )
    dbsession.commit()
    return example_contact_data


@pytest.fixture
def to_add_contact_data():
    return ContactSchema(
        email=schemas.EmailInSchema(
            basket_token="21aeb466-4003-4c2b-a27e-e6651c13d231",
            email_id=UUID("d1da1c99-fe09-44db-9c68-78a75752574d"),
            mailing_country="us",
            primary_email="ctms-user-to-be-created@example.com",
            sfdc_id="002A000001aBAcDEFA",
        )
    )


@pytest.fixture
def to_add_contact(dbsession, to_add_contact_data):
    create_contact(
        dbsession,
        to_add_contact_data.email.email_id,
        to_add_contact_data,
        get_metrics(),
    )
    dbsession.commit()
    return to_add_contact_data


@pytest.fixture
def simple_default_contact_data():
    return ContactSchema(
        email=schemas.EmailInSchema(
            basket_token="d3a827b5-747c-41c2-8381-59ce9ad63050",
            email_id=UUID("4f98b303-8863-421f-95d3-847cd4d83c9f"),
            mailing_country="us",
            primary_email="with-defaults@example.com",
            sfdc_id="102A000001aBAcDEFA",
        ),
        amo=schemas.AddOnsInSchema(),
    )


@pytest.fixture
def simple_default_contact(dbsession, simple_default_contact_data):
    create_contact(
        dbsession,
        simple_default_contact_data.email.email_id,
        simple_default_contact_data,
        get_metrics(),
    )
    dbsession.commit()
    return simple_default_contact_data


@pytest.fixture
def default_newsletter_contact_data():
    contact = ContactSchema(
        email=schemas.EmailInSchema(
            basket_token="b5487fbf-86ae-44b9-a638-bbb037ce61a6",
            email_id=UUID("dd2bc52c-49e4-4df9-95a8-197d3a7794cd"),
            mailing_country="us",
            primary_email="with-default-newsletter@example.com",
            sfdc_id="102A000001aBAcDEFA",
        ),
        newsletters=[],
    )
    return contact


@pytest.fixture
def default_newsletter_contact(dbsession, default_newsletter_contact_data):
    create_contact(
        dbsession,
        default_newsletter_contact_data.email.email_id,
        default_newsletter_contact_data,
        get_metrics(),
    )
    dbsession.commit()
    return default_newsletter_contact_data


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
def post_contact(client, dbsession, request):
    contact_fixture_name, fields_not_written = request.param
    contact_fixture = request.getfixturevalue(contact_fixture_name)
    email_id = contact_fixture.email.email_id

    def _add(
        modifier: Callable[[ContactSchema], ContactSchema] = lambda x: x,
        code: int = 201,
        stored_contacts: int = 1,
        check_redirect: bool = True,
        query_fields: Optional[dict] = None,
        check_written: bool = True,
    ):
        if query_fields is None:
            query_fields = {"primary_email": contact_fixture.email.primary_email}
        sample = contact_fixture.copy(deep=True)
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
def put_contact(client, dbsession, request):
    if hasattr(request, "param"):
        contact_fixture_name, fields_not_written = request.param
    else:
        contact_fixture_name = "to_add_contact_data"
        fields_not_written = set()
    contact_fixture = request.getfixturevalue(contact_fixture_name)
    sample_email_id = contact_fixture.email.email_id

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
            contact = contact_fixture
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
def stripe_price_data():
    return {
        "stripe_id": FAKE_STRIPE_PRICE_ID,
        "stripe_created": datetime(2020, 10, 27, 10, 45, tzinfo=timezone.utc),
        "stripe_product_id": fake_stripe_id("prod", "product"),
        "active": True,
        "currency": "usd",
        "recurring_interval": "month",
        "recurring_interval_count": 1,
        "unit_amount": 999,
    }


@pytest.fixture
def stripe_subscription_data():
    return {
        "stripe_id": FAKE_STRIPE_SUBSCRIPTION_ID,
        "stripe_created": datetime(2021, 9, 27, tzinfo=timezone.utc),
        "stripe_customer_id": FAKE_STRIPE_CUSTOMER_ID,
        "default_source_id": None,
        "default_payment_method_id": None,
        "cancel_at_period_end": False,
        "canceled_at": None,
        "current_period_start": datetime(2021, 10, 27, tzinfo=timezone.utc),
        "current_period_end": datetime(2021, 11, 27, tzinfo=timezone.utc),
        "ended_at": None,
        "start_date": datetime(2021, 9, 27, tzinfo=timezone.utc),
        "status": "active",
    }


@pytest.fixture
def stripe_subscription_item_data():
    return {
        "stripe_id": FAKE_STRIPE_SUBSCRIPTION_ID,
        "stripe_created": datetime(2021, 9, 27, tzinfo=timezone.utc),
        "stripe_subscription_id": FAKE_STRIPE_SUBSCRIPTION_ID,
        "stripe_price_id": FAKE_STRIPE_PRICE_ID,
    }


@pytest.fixture
def stripe_invoice_data():
    return {
        "stripe_id": FAKE_STRIPE_INVOICE_ID,
        "stripe_created": datetime(2021, 10, 28, tzinfo=timezone.utc),
        "stripe_customer_id": FAKE_STRIPE_CUSTOMER_ID,
        "default_source_id": None,
        "default_payment_method_id": None,
        "currency": "usd",
        "total": 1000,
        "status": "open",
    }


@pytest.fixture
def stripe_invoice_line_item_data():
    return {
        "stripe_id": fake_stripe_id("il", "invoice line item"),
        "stripe_price_id": FAKE_STRIPE_PRICE_ID,
        "stripe_invoice_id": FAKE_STRIPE_INVOICE_ID,
        "stripe_subscription_id": FAKE_STRIPE_SUBSCRIPTION_ID,
        "stripe_subscription_item_id": fake_stripe_id("si", "subscription_item"),
        "stripe_type": "subscription",
        "amount": 1000,
        "currency": "usd",
    }


@pytest.fixture
def raw_stripe_price_data(stripe_price_data):
    """Return minimal Stripe price data."""
    return {
        "id": stripe_price_data["stripe_id"],
        "object": "price",
        "created": unix_timestamp(stripe_price_data["stripe_created"]),
        "product": stripe_price_data["stripe_product_id"],
        "active": stripe_price_data["active"],
        "currency": stripe_price_data["currency"],
        "recurring": {
            "interval": stripe_price_data["recurring_interval"],
            "interval_count": stripe_price_data["recurring_interval_count"],
        },
        "unit_amount": stripe_price_data["unit_amount"],
    }


@pytest.fixture
def raw_stripe_subscription_data(
    stripe_subscription_data, stripe_subscription_item_data, raw_stripe_price_data
):
    """Return minimal Stripe subscription data."""
    return {
        "id": stripe_subscription_data["stripe_id"],
        "object": "subscription",
        "created": unix_timestamp(stripe_subscription_data["stripe_created"]),
        "customer": stripe_subscription_data["stripe_customer_id"],
        "cancel_at_period_end": stripe_subscription_data["cancel_at_period_end"],
        "canceled_at": stripe_subscription_data["canceled_at"],
        "current_period_start": unix_timestamp(
            stripe_subscription_data["current_period_start"]
        ),
        "current_period_end": unix_timestamp(
            stripe_subscription_data["current_period_end"]
        ),
        "ended_at": stripe_subscription_data["ended_at"],
        "start_date": unix_timestamp(stripe_subscription_data["start_date"]),
        "status": stripe_subscription_data["status"],
        "default_source": stripe_subscription_data["default_source_id"],
        "default_payment_method": stripe_subscription_data["default_payment_method_id"],
        "items": {
            "object": "list",
            "total_count": 1,
            "has_more": False,
            "url": f"/v1/subscription_items?subscription={stripe_subscription_data['stripe_id']}",
            "data": [
                {
                    "id": stripe_subscription_item_data["stripe_id"],
                    "object": "subscription_item",
                    "created": unix_timestamp(
                        stripe_subscription_item_data["stripe_created"]
                    ),
                    "subscription": stripe_subscription_item_data[
                        "stripe_subscription_id"
                    ],
                    "price": raw_stripe_price_data,
                }
            ],
        },
    }


@pytest.fixture
def raw_stripe_invoice_data(
    raw_stripe_price_data, stripe_invoice_data, stripe_invoice_line_item_data
):
    """Return minimal Stripe invoice data."""
    return {
        "id": stripe_invoice_data["stripe_id"],
        "object": "invoice",
        "created": unix_timestamp(stripe_invoice_data["stripe_created"]),
        "customer": stripe_invoice_data["stripe_customer_id"],
        "currency": stripe_invoice_data["currency"],
        "total": stripe_invoice_data["total"],
        "default_source": stripe_invoice_data["default_source_id"],
        "default_payment_method": stripe_invoice_data["default_payment_method_id"],
        "status": stripe_invoice_data["status"],
        "lines": {
            "object": "list",
            "total_count": 1,
            "has_more": False,
            "url": f"/v1/invoices/{stripe_invoice_data['stripe_id']}/lines",
            "data": [
                {
                    "id": stripe_invoice_line_item_data["stripe_id"],
                    "object": "line_item",
                    "type": stripe_invoice_line_item_data["stripe_type"],
                    "subscription": stripe_invoice_line_item_data[
                        "stripe_subscription_id"
                    ],
                    "subscription_item": stripe_invoice_line_item_data[
                        "stripe_subscription_item_id"
                    ],
                    "price": raw_stripe_price_data,
                    "amount": stripe_invoice_line_item_data["amount"],
                    "currency": stripe_invoice_line_item_data["currency"],
                }
            ],
        },
    }


@pytest.fixture
def contact_with_stripe_subscription(
    dbsession,
    example_contact,
    stripe_customer_factory,
    stripe_price_data,
    stripe_subscription_data,
    stripe_subscription_item_data,
):
    stripe_customer = stripe_customer_factory(
        stripe_id=FAKE_STRIPE_CUSTOMER_ID, fxa_id=example_contact.fxa.fxa_id
    )
    create_stripe_price(dbsession, StripePriceCreateSchema(**stripe_price_data))
    create_stripe_subscription(
        dbsession, StripeSubscriptionCreateSchema(**stripe_subscription_data)
    )
    create_stripe_subscription_item(
        dbsession,
        StripeSubscriptionItemCreateSchema(
            **stripe_subscription_item_data,
        ),
    )
    dbsession.commit()

    contact = get_contact_by_email_id(dbsession, stripe_customer.email.email_id)
    return contact


@pytest.fixture
def background_metric_service():
    """Return a BackgroundMetricService with push_to_gateway mocked."""
    service = BackgroundMetricService(CollectorRegistry(), "https://push.example.com")
    with mock.patch("ctms.background_metrics.BackgroundMetricService.push_to_gateway"):
        yield service
