from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .models import StripeCustomer, StripePaymentMethod, StripePrice, StripeProduct
from .schemas import (
    StripeCustomerCreateSchema,
    StripePaymentMethodCreateSchema,
    StripePriceCreateSchema,
    StripeProductCreateSchema,
)

if TYPE_CHECKING:
    from pydantic import UUID4
    from sqlalchemy.orm import Session


def create_stripe_customer(
    db: Session, email_id: UUID4, customer: StripeCustomerCreateSchema
) -> Optional[StripeCustomer]:
    if customer.is_default():
        return None
    db_customer = StripeCustomer(email_id=email_id, **customer.dict())
    db.add(db_customer)
    return db_customer


def create_stripe_product(
    db: Session, product: StripeProductCreateSchema
) -> Optional[StripeProduct]:
    if product.is_default():
        return None
    db_product = StripeProduct(**product.dict())
    db.add(db_product)
    return db_product


def create_stripe_price(
    db: Session, product_id: str, price: StripePriceCreateSchema
) -> Optional[StripePrice]:
    if price.is_default():
        return None
    db_price = StripePrice(stripe_product_id=product_id, **price.dict())
    db.add(db_price)
    return db_price


def create_stripe_payment_method(
    db: Session, customer_id: str, payment_method: StripePaymentMethodCreateSchema
) -> Optional[StripePaymentMethod]:
    if payment_method.is_default():
        return None
    db_payment_method = StripePaymentMethod(
        stripe_customer_id=customer_id, **payment_method.dict()
    )
    db.add(db_payment_method)
    return db_payment_method


# def create_stripe_invoice_item(
# def create_stripe_invoice(
# def create_stripe_subscription(
# def create_stripe_subscription_item(
