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
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
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
from ctms.schemas import (
    ApiClientSchema,
    ContactSchema,
    StripeCustomerCreateSchema,
    StripePriceCreateSchema,
    StripeSubscriptionCreateSchema,
    StripeSubscriptionItemCreateSchema,
)
from tests.unit.sample_data import SAMPLE_CONTACTS, SAMPLE_STRIPE_DATA

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

    echo = pytestconfig.getoption("verbose") > 2
    test_engine = create_engine(test_db_url, echo=echo)

    cfg = alembic_config.Config(os.path.join(APP_FOLDER, "alembic.ini"))
    with test_engine.begin() as cnx:
        # pylint: disable-next=unsupported-assignment-operation
        cfg.attributes["connection"] = cnx
        alembic_command.upgrade(cfg, "head")

    yield test_engine
    test_engine.dispose()
    if drop_db:
        drop_database(test_db_url)


@pytest.fixture
def connection(engine):
    """Return a connection to the database that rolls back automatically."""
    with engine.begin() as conn:
        savepoint = conn.begin_nested()
        yield conn
        savepoint.rollback()


@pytest.fixture
def dbsession(connection):
    """Return a database session that rolls back."""
    test_sessionmaker = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    db = test_sessionmaker()

    def test_get_db():
        db.begin_nested()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = test_get_db
    yield db
    del app.dependency_overrides[get_db]


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


@pytest.fixture
def maximal_contact(dbsession):
    email_id = UUID("67e52c77-950f-4f28-accb-bb3ea1a2c51a")
    contact = SAMPLE_CONTACTS[email_id]
    create_contact(dbsession, email_id, contact, get_metrics())
    dbsession.commit()
    return contact


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
def anon_client():
    """A test client with no authorization."""
    return TestClient(app)


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
