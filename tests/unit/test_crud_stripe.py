"""Test database operations on Stripe models"""
from datetime import datetime, timezone
import pytest

from ctms.crud_stripe import (
    create_stripe_customer,
    create_stripe_product,
    create_stripe_price,
)
from ctms.schemas import (
    StripeCustomerCreateSchema,
    StripeCustomerOutputSchema,
    StripePriceCreateSchema,
    StripePriceOutputSchema,
    StripeProductCreateSchema,
    StripeProductOutputSchema,
)


@pytest.fixture
def stripe_customer(dbsession, example_contact):
    customer = StripeCustomerCreateSchema(
        stripe_id="cus_8epDebVEl8Bs2V",
        stripe_created=datetime.now(tz=timezone.utc),
    )
    db_customer = create_stripe_customer(
        dbsession, example_contact.email.email_id, customer
    )
    dbsession.commit()
    dbsession.refresh(db_customer)
    return db_customer


@pytest.fixture
def stripe_product(dbsession):
    product = StripeProductCreateSchema(
        stripe_id="prod_KPReWHqwGqZBzc",
        stripe_created=datetime.now(tz=timezone.utc),
        stripe_updated=datetime.now(tz=timezone.utc),
        name="Mozilla ISP",
    )
    db_product = create_stripe_product(dbsession, product)
    dbsession.commit()
    dbsession.refresh(db_product)
    return db_product


@pytest.fixture
def stripe_price(dbsession, stripe_product):
    price = StripePriceCreateSchema(
        stripe_id="price_1Jkcl3Kb9q6OnNsLFbECmMtd",
        stripe_created=datetime.now(tz=timezone.utc),
        currency="usd",
        recurring_interval="month",
        recurring_interval_count=6,
        unit_amount=1499,
    )
    db_price = create_stripe_price(dbsession, stripe_product.stripe_id, price)
    assert db_price
    dbsession.commit()  # Does not throw
    dbsession.refresh(db_price)
    return db_price


def test_create_stripe_customer_by_fixture(stripe_customer):
    out_customer = StripeCustomerOutputSchema.from_orm(stripe_customer)
    assert out_customer.stripe_id == "cus_8epDebVEl8Bs2V"


def test_create_stripe_product_by_fixture(stripe_product):
    out_product = StripeProductOutputSchema.from_orm(stripe_product)
    assert out_product.stripe_id == "prod_KPReWHqwGqZBzc"


def test_create_stripe_price_from_fixture(dbsession, stripe_price):
    out_price = StripePriceOutputSchema.from_orm(stripe_price)
    assert out_price.stripe_id == "price_1Jkcl3Kb9q6OnNsLFbECmMtd"


def test_create_stripe_price_nonrecurring(dbsession, stripe_product):
    price = StripePriceCreateSchema(
        stripe_id="price_1Jkcl3Kb9q6OnNsLFbECmMtd",
        stripe_created=datetime.now(tz=timezone.utc),
        currency="usd",
    )
    db_price = create_stripe_price(dbsession, stripe_product.stripe_id, price)
    assert db_price
    dbsession.commit()  # Does not throw
    dbsession.refresh(db_price)
    out_price = StripePriceOutputSchema.from_orm(db_price)
    assert out_price.stripe_id == "price_1Jkcl3Kb9q6OnNsLFbECmMtd"
