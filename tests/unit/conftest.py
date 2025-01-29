"""pytest fixtures for the CTMS app"""

import logging
import os.path
from datetime import datetime, timezone
from time import mktime
from typing import Callable, Optional
from urllib.parse import urlparse
from uuid import UUID

import pytest
from alembic import command as alembic_command
from alembic import config as alembic_config
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry
from pydantic import PostgresDsn
from pytest_factoryboy import register
from sqlalchemy import create_engine
from sqlalchemy_utils.functions import create_database, database_exists, drop_database

from ctms import metrics as metrics_module
from ctms import schemas
from ctms.app import app
from ctms.config import Settings
from ctms.crud import (
    create_api_client,
    create_contact,
    get_amo_by_email_id,
    get_contacts_by_any_id,
    get_email,
    get_fxa_by_email_id,
    get_mofo_by_email_id,
    get_newsletters_by_email_id,
    get_waitlists_by_email_id,
)
from ctms.database import ScopedSessionLocal, SessionLocal
from ctms.dependencies import get_api_client, get_db
from ctms.metrics import get_metrics
from ctms.schemas import ApiClientSchema, ContactSchema
from ctms.schemas.contact import ContactInSchema
from tests import factories

MY_FOLDER = os.path.dirname(__file__)
TEST_FOLDER = os.path.dirname(MY_FOLDER)
APP_FOLDER = os.path.dirname(TEST_FOLDER)

LOG_CONFIG_TESTS = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {
        "httpx": {"level": logging.CRITICAL},
    },
}


def _gather_examples(schema_class) -> dict[str, str]:
    """Gather the examples from a schema definition"""
    examples = {}
    for key, props in schema_class.model_json_schema()["properties"].items():
        if "examples" in props:
            examples[key] = props["examples"][0]
    return examples


def unix_timestamp(the_time: Optional[datetime] = None) -> int:
    """Create a UNIX timestamp from a datetime or now"""
    the_time = the_time or datetime.now(tz=timezone.utc)
    return int(mktime(the_time.timetuple()))


@pytest.fixture(autouse=True, scope="session")
def setup_logging():
    logging.config.dictConfig(LOG_CONFIG_TESTS)


@pytest.fixture(scope="session")
def engine(pytestconfig):
    """Return a SQLAlchemy engine for a fresh test database."""

    orig_db_url = Settings().db_url
    parsed_db_url = urlparse(orig_db_url)
    if parsed_db_url.path.endswith("test"):
        # The database ends with test, assume the caller wanted us to use it
        test_db_url = orig_db_url
        drop_db = False
        assert database_exists(test_db_url)
    else:
        # Assume the regular database was passed, create a new test database
        test_db_url = str(
            PostgresDsn.build(
                scheme=parsed_db_url.scheme,
                username=parsed_db_url.username,
                password=parsed_db_url.password,
                host=parsed_db_url.hostname,
                port=parsed_db_url.port,
                path=parsed_db_url.path + "_test",
                query=parsed_db_url.query,
                fragment=parsed_db_url.fragment,
            )
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
    cfg.attributes["unit-tests"] = True
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
    SessionLocal.configure(bind=conn, join_transaction_mode="create_savepoint")
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def dbsession(request, connection):
    """Return a database session that rolls back.

    Adapted from https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites
    """
    if "disable_autouse" in request.keywords:
        yield
    else:
        transaction = connection.begin()
        session = ScopedSessionLocal()
        yield session
        session.close()
        transaction.rollback()


# Database models
register(factories.models.EmailFactory)
register(factories.models.NewsletterFactory)
register(factories.models.WaitlistFactory)


def create_full_contact(db, contact: ContactSchema):
    """Helper to save a whole contact object into the database.
    Unlike the `crud.py` functions, this takes a `ContactSchema`
    instead of a `ContactInSchema` as input, and will save the specified
    timestamps.
    """
    contact_input = ContactInSchema(**contact.model_dump())
    create_contact(db, contact.email.email_id, contact_input, get_metrics())
    db.flush()

    if contact.email.create_timestamp and contact.email.update_timestamp:
        email_in_db = get_email(db, contact.email.email_id)
        email_in_db.create_timestamp = contact.email.create_timestamp
        email_in_db.update_timestamp = contact.email.update_timestamp

    if contact.amo and contact.amo.create_timestamp and contact.amo.create_timestamp:
        amo_in_db = get_amo_by_email_id(db, contact.email.email_id)
        amo_in_db.create_timestamp = contact.amo.create_timestamp
        amo_in_db.update_timestamp = contact.amo.update_timestamp
        db.add(amo_in_db)

    specified_newsletters_by_name = {nl.name: nl for nl in contact.newsletters}
    if specified_newsletters_by_name:
        for newsletter_in_db in get_newsletters_by_email_id(db, contact.email.email_id):
            newsletter_in_db.create_timestamp = specified_newsletters_by_name[newsletter_in_db.name].create_timestamp
            newsletter_in_db.update_timestamp = specified_newsletters_by_name[newsletter_in_db.name].update_timestamp
            db.add(newsletter_in_db)

    specified_waitlists_by_name = {wl.name: wl for wl in contact.waitlists}
    if specified_waitlists_by_name:
        for waitlist_in_db in get_waitlists_by_email_id(db, contact.email.email_id):
            waitlist_in_db.create_timestamp = specified_waitlists_by_name[waitlist_in_db.name].create_timestamp
            waitlist_in_db.update_timestamp = specified_waitlists_by_name[waitlist_in_db.name].update_timestamp
            db.add(waitlist_in_db)

    db.commit()


@pytest.fixture
def minimal_contact_data() -> ContactSchema:
    email_id = UUID("93db83d4-4119-4e0c-af87-a713786fa81d")
    return ContactSchema(
        email=schemas.EmailSchema(
            basket_token="142e20b6-1ef5-43d8-b5f4-597430e956d7",
            create_timestamp="2014-01-22T15:24:00.000+0000",
            email_id=email_id,
            mailing_country="us",
            primary_email="ctms-user@example.com",
            sfdc_id="001A000001aABcDEFG",
            update_timestamp="2020-01-22T15:24:00.000+0000",
        ),
        newsletters=[
            schemas.NewsletterTableSchema(
                name="app-dev",
                email_id=email_id,
                create_timestamp="2014-01-22T15:24:00.000+0000",
                update_timestamp="2020-01-22T15:24:00.000+0000",
            ),
            schemas.NewsletterTableSchema(
                name="maker-party",
                email_id=email_id,
                create_timestamp="2014-01-22T15:24:00.000+0000",
                update_timestamp="2020-01-22T15:24:00.000+0000",
            ),
            schemas.NewsletterTableSchema(
                name="mozilla-foundation",
                email_id=email_id,
                create_timestamp="2014-01-22T15:24:00.000+0000",
                update_timestamp="2020-01-22T15:24:00.000+0000",
            ),
            schemas.NewsletterTableSchema(
                name="mozilla-learning-network",
                email_id=email_id,
                create_timestamp="2014-01-22T15:24:00.000+0000",
                update_timestamp="2020-01-22T15:24:00.000+0000",
            ),
        ],
    )


@pytest.fixture
def maximal_contact_data() -> ContactSchema:
    email_id = UUID("67e52c77-950f-4f28-accb-bb3ea1a2c51a")
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
            email_id=email_id,
            primary_email="mozilla-fan@example.com",
            basket_token=UUID("d9ba6182-f5dd-4728-a477-2cc11bf62b69"),
            first_name="Fan",
            last_name="of Mozilla",
            mailing_country="ca",
            email_lang="fr",
            sfdc_id="001A000001aMozFan",
            double_opt_in=True,
            unsubscribe_reason="done with this mailing list",
            create_timestamp="2010-01-01T08:04:00.000+0000",
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
            schemas.NewsletterTableSchema(
                email_id=email_id,
                name="ambassadors",
                source="https://www.mozilla.org/en-US/contribute/studentambassadors/",
                subscribed=False,
                unsub_reason="Graduated, don't have time for FSA",
                create_timestamp="2010-01-01T08:04:00.000+0000",
                update_timestamp="2020-01-28T14:50:00.000+0000",
            ),
            schemas.NewsletterTableSchema(
                email_id=email_id,
                name="common-voice",
                format="T",
                lang="fr",
                source="https://commonvoice.mozilla.org/fr",
                create_timestamp="2010-01-01T08:04:00.000+0000",
                update_timestamp="2020-01-28T14:50:00.000+0000",
            ),
            schemas.NewsletterTableSchema(
                email_id=email_id,
                name="firefox-accounts-journey",
                source="https://www.mozilla.org/fr/firefox/accounts/",
                lang="fr",
                subscribed=False,
                unsub_reason="done with this mailing list",
                create_timestamp="2010-01-01T08:04:00.000+0000",
                update_timestamp="2020-01-28T14:50:00.000+0000",
            ),
            schemas.NewsletterTableSchema(
                email_id=email_id,
                name="firefox-os",
                create_timestamp="2010-01-01T08:04:00.000+0000",
                update_timestamp="2020-01-28T14:50:00.000+0000",
            ),
            schemas.NewsletterTableSchema(
                email_id=email_id,
                name="hubs",
                lang="fr",
                create_timestamp="2010-01-01T08:04:00.000+0000",
                update_timestamp="2020-01-28T14:50:00.000+0000",
            ),
            schemas.NewsletterTableSchema(
                email_id=email_id,
                name="mozilla-festival",
                create_timestamp="2010-01-01T08:04:00.000+0000",
                update_timestamp="2020-01-28T14:50:00.000+0000",
            ),
            schemas.NewsletterTableSchema(
                email_id=email_id,
                name="mozilla-foundation",
                lang="fr",
                create_timestamp="2010-01-01T08:04:00.000+0000",
                update_timestamp="2020-01-28T14:50:00.000+0000",
            ),
        ],
        waitlists=[
            schemas.WaitlistTableSchema(
                email_id=email_id,
                name="a-software",
                source="https://a-software.mozilla.org/",
                fields={"geo": "fr"},
                subscribed=True,
                create_timestamp="2010-01-01T08:04:00.000+0000",
                update_timestamp="2020-01-28T14:50:00.000+0000",
            ),
            schemas.WaitlistTableSchema(
                email_id=email_id,
                name="relay",
                fields={"geo": "cn"},
                subscribed=True,
                create_timestamp="2010-01-01T08:04:00.000+0000",
                update_timestamp="2020-01-28T14:50:00.000+0000",
            ),
            schemas.WaitlistTableSchema(
                email_id=email_id,
                name="super-product",
                source="https://super-product.mozilla.org/",
                fields={"geo": "fr", "platform": "win64"},
                subscribed=True,
                create_timestamp="2010-01-01T08:04:00.000+0000",
                update_timestamp="2020-01-28T14:50:00.000+0000",
            ),
            schemas.WaitlistTableSchema(
                email_id=email_id,
                name="vpn",
                fields={
                    "geo": "ca",
                    "platform": "windows,android",
                },
                subscribed=True,
                create_timestamp="2010-01-01T08:04:00.000+0000",
                update_timestamp="2020-01-28T14:50:00.000+0000",
            ),
        ],
    )


@pytest.fixture
def example_contact_data() -> ContactSchema:
    return ContactSchema(
        amo=schemas.AddOnsSchema(**_gather_examples(schemas.AddOnsSchema)),
        email=schemas.EmailSchema(**_gather_examples(schemas.EmailSchema)),
        fxa=schemas.FirefoxAccountsSchema(**_gather_examples(schemas.FirefoxAccountsSchema)),
        newsletters=ContactSchema.model_json_schema()["properties"]["newsletters"]["examples"][0],
        waitlists=[schemas.WaitlistTableSchema(**example) for example in ContactSchema.model_json_schema()["properties"]["waitlists"]["examples"][0]],
    )


@pytest.fixture
def example_contact(dbsession, example_contact_data) -> ContactSchema:
    create_full_contact(dbsession, example_contact_data)
    return example_contact_data


@pytest.fixture
def to_add_contact_data() -> ContactSchema:
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
def default_waitlist_contact_data():
    contact = ContactSchema(
        email=schemas.EmailInSchema(
            basket_token="6D854AA2-C1CF-4DC0-9581-2641AD3FA52D",
            email_id=UUID("0A6ECCA3-D007-4BD4-B596-C09DA94F0FEF"),
            mailing_country="us",
            primary_email="with-default-waitlist@example.com",
            sfdc_id="7772A000001aBAcXZY",
        ),
        waitlists=[],
    )
    return contact


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
        return ApiClientSchema(client_id="test_client", email="test_client@example.com", enabled=True)

    app.dependency_overrides[get_api_client] = test_api_client
    yield anon_client
    del app.dependency_overrides[get_api_client]


@pytest.fixture
def settings():
    return Settings()


@pytest.fixture
def setup_metrics(monkeypatch):
    """Setup a metrics registry and metrics, use them in the app"""

    test_registry = CollectorRegistry()
    test_metrics = metrics_module.init_metrics(test_registry)
    # Because these methods are called from a middleware
    # we can't use dependency injection like with get_db
    monkeypatch.setattr(metrics_module, "METRICS_REGISTRY", test_registry)
    monkeypatch.setattr(metrics_module, "METRICS", test_metrics)
    yield test_registry, test_metrics


@pytest.fixture
def registry(setup_metrics):
    """Get the test metrics registry"""
    test_registry, _ = setup_metrics
    return test_registry


@pytest.fixture
def metrics(setup_metrics):
    """Get the test metrics"""
    _, test_metrics = setup_metrics
    return test_metrics


@pytest.fixture
def client_id_and_secret(dbsession):
    """Return valid OAuth2 client_id and client_secret."""
    api_client = ApiClientSchema(client_id="id_db_api_client", email="db_api_client@example.com", enabled=True)
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
        sample = contact_fixture.model_copy(deep=True)
        sample = modifier(sample)
        resp = client.post("/ctms", content=sample.model_dump_json())
        assert resp.status_code == code, resp.text
        if check_redirect:
            assert resp.headers["location"] == f"/ctms/{sample.email.email_id}"
        saved = get_contacts_by_any_id(dbsession, **query_fields)
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
            if sample.model_dump().get(field) and code in {200, 201}:
                if field in fields_not_written:
                    if result_list:
                        assert results == [], f"{email_id} has field `{field}` but it is _default_ and it should _not_ have been written to db"
                    else:
                        assert results is None, f"{email_id} has field `{field}` but it is _default_ and it should _not_ have been written to db"
                else:
                    assert results, f"{email_id} has field `{field}` and it should have been written to db"
            elif result_list:
                assert results == [], f"{email_id} does not have field `{field}` and it should _not_ have been written to db"
            else:
                assert results is None, f"{email_id} does not have field `{field}` and it should _not_ have been written to db"

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
        sample = contact.model_copy(deep=True)
        sample = modifier(sample)
        resp = client.put(f"/ctms/{sample.email.email_id}", content=sample.model_dump_json())
        assert resp.status_code == code, resp.text
        saved = get_contacts_by_any_id(dbsession, **query_fields)
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
            if sample.model_dump().get(field) and code in {200, 201}:
                if field in fields_not_written or field in new_default_fields:
                    assert results is None or (isinstance(results, list) and len(results) == 0), (
                        f"{sample_email_id} has field `{field}` but it is _default_ and it should _not_ have been written to db"
                    )
                else:
                    assert results, f"{sample_email_id} has field `{field}` and it should have been written to db"
            else:
                assert results is None or (isinstance(results, list) and len(results) == 0), (
                    f"{sample_email_id} does not have field `{field}` and it should _not_ have been written to db"
                )

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
