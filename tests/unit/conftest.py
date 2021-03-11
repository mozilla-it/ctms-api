"""pytest fixtures for the CTMS app"""
from typing import Callable, Set
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import PostgresDsn
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils.functions import create_database, database_exists, drop_database

from ctms.app import app, get_api_client, get_db
from ctms.config import Settings
from ctms.crud import create_contact, get_contacts_by_any_id
from ctms.models import Base
from ctms.sample_data import SAMPLE_CONTACTS
from ctms.schemas import ApiClientSchema, ContactInSchema, ContactSchema


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

    # TODO: Convert to running alembic migrations
    Base.metadata.create_all(bind=test_engine)

    yield test_engine
    test_engine.dispose()
    if drop_db:
        drop_database(test_db_url)


@pytest.fixture
def connection(engine):
    """Return a connection to the database that rolls back automatically."""
    with engine.begin() as connection:
        savepoint = connection.begin_nested()
        yield connection
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
    assert contact.vpn_waitlist is None
    create_contact(dbsession, email_id, contact)
    dbsession.commit()
    return contact


@pytest.fixture
def maximal_contact(dbsession):
    email_id = UUID("67e52c77-950f-4f28-accb-bb3ea1a2c51a")
    contact = SAMPLE_CONTACTS[email_id]
    create_contact(dbsession, email_id, contact)
    dbsession.commit()
    return contact


@pytest.fixture
def example_contact(dbsession):
    email_id = UUID("332de237-cab7-4461-bcc3-48e68f42bd5c")
    contact = SAMPLE_CONTACTS[email_id]
    create_contact(dbsession, email_id, contact)
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
