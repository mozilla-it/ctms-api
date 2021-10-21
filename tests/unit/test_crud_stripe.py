"""Test database operations on Stripe models"""
from datetime import datetime, timedelta, timezone

import pytest

from ctms.crud_stripe import (
    create_stripe_customer,
    create_stripe_invoice,
    create_stripe_invoice_item,
    create_stripe_payment_method,
    create_stripe_price,
    create_stripe_product,
    create_stripe_subscription,
    create_stripe_subscription_item,
)
from ctms.schemas import (
    StripeCustomerCreateSchema,
    StripeCustomerOutputSchema,
    StripeInvoiceCreateSchema,
    StripeInvoiceItemCreateSchema,
    StripeInvoiceItemOutputSchema,
    StripeInvoiceOutputSchema,
    StripePaymentMethodCreateSchema,
    StripePaymentMethodOutputSchema,
    StripePriceCreateSchema,
    StripePriceOutputSchema,
    StripeProductCreateSchema,
    StripeProductOutputSchema,
    StripeSubscriptionCreateSchema,
    StripeSubscriptionItemCreateSchema,
    StripeSubscriptionItemOutputSchema,
    StripeSubscriptionOutputSchema,
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
def stripe_payment_method(dbsession, stripe_customer):
    payment_method = StripePaymentMethodCreateSchema(
        stripe_id="pm_1JmPBfKb9q6OnNsLlzx8GamM",
        stripe_created=datetime.now(tz=timezone.utc),
        payment_type="card",
        billing_address_country="US",
        card_brand="visa",
        card_country="US",
        card_last4="4242",
    )
    db_payment_method = create_stripe_payment_method(
        dbsession, stripe_customer.stripe_id, payment_method
    )
    assert db_payment_method
    dbsession.commit()
    dbsession.refresh(db_payment_method)
    return db_payment_method


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
    dbsession.commit()
    dbsession.refresh(db_price)
    return db_price


@pytest.fixture
def stripe_invoice(dbsession, stripe_customer):
    invoice = StripeInvoiceCreateSchema(
        stripe_id="in_1JmPBbKb9q6OnNsLb8ofPsbX",
        stripe_created=datetime.now(tz=timezone.utc),
        currency="usd",
        total=999,
        status="paid",
    )
    db_invoice = create_stripe_invoice(dbsession, stripe_customer.stripe_id, invoice)
    assert db_invoice
    dbsession.commit()
    dbsession.refresh(db_invoice)
    return db_invoice


@pytest.fixture
def stripe_invoice_item(dbsession, stripe_invoice, stripe_price):
    invoice_item = StripeInvoiceItemCreateSchema(
        stripe_id="ii_1JfEslKb9q6OnNsLh8hPmhX0",
        stripe_created=datetime.now(tz=timezone.utc),
    )
    db_invoice_item = create_stripe_invoice_item(
        dbsession, stripe_invoice.stripe_id, stripe_price.stripe_id, invoice_item
    )
    assert db_invoice_item
    dbsession.commit()
    dbsession.refresh(db_invoice_item)
    return db_invoice_item


@pytest.fixture
def stripe_subscription(dbsession, stripe_customer):
    subscription = StripeSubscriptionCreateSchema(
        stripe_id="sub_FvT2g7CI2jXnyE",
        stripe_created=datetime.now(tz=timezone.utc),
        cancel_at_period_end=True,
        canceled_at=None,
        current_period_end=datetime.now(tz=timezone.utc) + timedelta(days=30),
        current_period_start=datetime.now(tz=timezone.utc),
        ended_at=None,
        start_date=datetime.now(tz=timezone.utc),
        status="active",
    )
    db_subscription = create_stripe_subscription(
        dbsession, stripe_customer.stripe_id, subscription
    )
    assert db_subscription
    dbsession.commit()
    dbsession.refresh(db_subscription)
    return db_subscription


@pytest.fixture
def stripe_subscription_item(dbsession, stripe_subscription, stripe_price):
    subscription_item = StripeSubscriptionItemCreateSchema(
        stripe_id="si_KRfz6PPWeN8vxm",
        stripe_created=datetime.now(tz=timezone.utc),
    )
    db_subscription_item = create_stripe_subscription_item(
        dbsession,
        stripe_subscription.stripe_id,
        stripe_price.stripe_id,
        subscription_item,
    )
    assert db_subscription_item
    dbsession.commit()
    dbsession.refresh(db_subscription_item)
    return db_subscription_item


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
    dbsession.commit()
    dbsession.refresh(db_price)
    out_price = StripePriceOutputSchema.from_orm(db_price)
    assert out_price.stripe_id == "price_1Jkcl3Kb9q6OnNsLFbECmMtd"
    assert out_price.recurring_interval is None
    assert out_price.recurring_interval_count is None
    assert out_price.unit_amount is None


def test_create_stripe_payment_method_from_fixture(dbsession, stripe_payment_method):
    out_payment_method = StripePaymentMethodOutputSchema.from_orm(stripe_payment_method)
    assert out_payment_method.stripe_id == "pm_1JmPBfKb9q6OnNsLlzx8GamM"


def test_create_stripe_payment_method_non_card(dbsession, stripe_customer):
    payment_method = StripePaymentMethodCreateSchema(
        stripe_id="pm_1JmPBfKb9q6OnNsLlzx8GamM",
        stripe_created=datetime.now(tz=timezone.utc),
        payment_type="card_present",
    )
    db_payment_method = create_stripe_payment_method(
        dbsession, stripe_customer.stripe_id, payment_method
    )
    assert db_payment_method
    dbsession.commit()
    dbsession.refresh(db_payment_method)
    out_payment_method = StripePaymentMethodOutputSchema.from_orm(db_payment_method)
    assert out_payment_method.stripe_id == "pm_1JmPBfKb9q6OnNsLlzx8GamM"
    assert out_payment_method.billing_address_country is None
    assert out_payment_method.card_brand is None
    assert out_payment_method.card_country is None
    assert out_payment_method.card_last4 is None


def test_create_stripe_invoice_from_fixture(dbsession, stripe_invoice):
    out_invoice = StripeInvoiceOutputSchema.from_orm(stripe_invoice)
    assert out_invoice.stripe_id == "in_1JmPBbKb9q6OnNsLb8ofPsbX"
    assert out_invoice.default_payment_method is None


def test_stripe_invoice_with_payment_method(
    dbsession, stripe_customer, stripe_payment_method
):
    invoice = StripeInvoiceCreateSchema(
        stripe_id="in_1JmPBbKb9q6OnNsLb8ofPsbX",
        stripe_created=datetime.now(tz=timezone.utc),
        currency="usd",
        total=999,
        status="paid",
        default_payment_method=stripe_payment_method.stripe_id,
    )
    db_invoice = create_stripe_invoice(dbsession, stripe_customer.stripe_id, invoice)
    assert db_invoice
    dbsession.commit()
    dbsession.refresh(db_invoice)
    assert db_invoice.payment_method == stripe_payment_method


def test_create_stripe_invoice_item_from_fixture(dbsession, stripe_invoice_item):
    out_invoice_item = StripeInvoiceItemOutputSchema.from_orm(stripe_invoice_item)
    assert out_invoice_item.stripe_id == "ii_1JfEslKb9q6OnNsLh8hPmhX0"


def test_create_stripe_subscription_from_fixture(dbsession, stripe_subscription):
    out_subscription = StripeSubscriptionOutputSchema.from_orm(stripe_subscription)
    assert out_subscription.stripe_id == "sub_FvT2g7CI2jXnyE"
    assert out_subscription.canceled_at is None
    assert out_subscription.ended_at is None
    assert out_subscription.default_payment_method is None


def test_create_stripe_subscription_canceled(dbsession, stripe_customer):
    subscription = StripeSubscriptionCreateSchema(
        stripe_id="sub_FvT2g7CI2jXnyE",
        stripe_created=datetime.now(tz=timezone.utc) - timedelta(days=60),
        cancel_at_period_end=True,
        canceled_at=datetime.now(tz=timezone.utc) - timedelta(days=45),
        current_period_end=datetime.now(tz=timezone.utc) - timedelta(days=30),
        current_period_start=datetime.now(tz=timezone.utc) - timedelta(days=60),
        ended_at=datetime.now(tz=timezone.utc) - timedelta(days=30),
        start_date=datetime.now(tz=timezone.utc),
        status="canceled",
    )
    db_subscription = create_stripe_subscription(
        dbsession, stripe_customer.stripe_id, subscription
    )
    assert db_subscription
    dbsession.commit()
    dbsession.refresh(db_subscription)
    out_subscription = StripeSubscriptionOutputSchema.from_orm(db_subscription)
    assert out_subscription.stripe_id == "sub_FvT2g7CI2jXnyE"
    assert out_subscription.default_payment_method is None


def test_create_stripe_subscription_with_payment(
    dbsession, stripe_customer, stripe_payment_method
):
    subscription = StripeSubscriptionCreateSchema(
        stripe_id="sub_FvT2g7CI2jXnyE",
        stripe_created=datetime.now(tz=timezone.utc) - timedelta(days=60),
        cancel_at_period_end=True,
        current_period_end=datetime.now(tz=timezone.utc) - timedelta(days=30),
        current_period_start=datetime.now(tz=timezone.utc) - timedelta(days=60),
        start_date=datetime.now(tz=timezone.utc),
        status="canceled",
        default_payment_method=stripe_payment_method.stripe_id,
    )
    db_subscription = create_stripe_subscription(
        dbsession, stripe_customer.stripe_id, subscription
    )
    assert db_subscription
    dbsession.commit()
    dbsession.refresh(db_subscription)
    assert db_subscription.payment_method == stripe_payment_method


def test_create_stripe_subscription_item_from_fixture(
    dbsession, stripe_subscription_item
):
    out_subscription_item = StripeSubscriptionItemOutputSchema.from_orm(
        stripe_subscription_item
    )
    assert out_subscription_item.stripe_id == "si_KRfz6PPWeN8vxm"
