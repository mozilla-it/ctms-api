from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .models import (
    StripeCustomer,
    StripeInvoice,
    StripeInvoiceItem,
    StripePaymentMethod,
    StripePrice,
    StripeProduct,
    StripeSubscription,
    StripeSubscriptionItem,
)
from .schemas import (
    StripeCustomerCreateSchema,
    StripeInvoiceCreateSchema,
    StripeInvoiceItemCreateSchema,
    StripePaymentMethodCreateSchema,
    StripePriceCreateSchema,
    StripeProductCreateSchema,
    StripeSubscriptionCreateSchema,
    StripeSubscriptionItemCreateSchema,
)

if TYPE_CHECKING:
    from pydantic import UUID4
    from sqlalchemy.orm import Session


def create_stripe_customer(
    db: Session, email_id: UUID4, customer: StripeCustomerCreateSchema
) -> Optional[StripeCustomer]:
    db_customer = StripeCustomer(email_id=email_id, **customer.dict())
    db.add(db_customer)
    return db_customer


def create_stripe_product(
    db: Session, product: StripeProductCreateSchema
) -> Optional[StripeProduct]:
    db_product = StripeProduct(**product.dict())
    db.add(db_product)
    return db_product


def create_stripe_price(
    db: Session, product_id: str, price: StripePriceCreateSchema
) -> Optional[StripePrice]:
    db_price = StripePrice(stripe_product_id=product_id, **price.dict())
    db.add(db_price)
    return db_price


def create_stripe_payment_method(
    db: Session, customer_id: str, payment_method: StripePaymentMethodCreateSchema
) -> Optional[StripePaymentMethod]:
    db_payment_method = StripePaymentMethod(
        stripe_customer_id=customer_id, **payment_method.dict()
    )
    db.add(db_payment_method)
    return db_payment_method


def create_stripe_invoice(
    db: Session,
    customer_id: str,
    invoice: StripeInvoiceCreateSchema,
) -> Optional[StripeInvoice]:
    db_invoice = StripeInvoice(stripe_customer_id=customer_id, **invoice.dict())
    db.add(db_invoice)
    return db_invoice


def create_stripe_invoice_item(
    db: Session,
    invoice_id: str,
    price_id: str,
    invoice_item: StripeInvoiceItemCreateSchema,
) -> Optional[StripeInvoiceItem]:
    db_invoice_item = StripeInvoiceItem(
        stripe_invoice_id=invoice_id, stripe_price_id=price_id, **invoice_item.dict()
    )
    db.add(db_invoice_item)
    return db_invoice_item


def create_stripe_subscription(
    db: Session,
    customer_id: str,
    subscription: StripeSubscriptionCreateSchema,
) -> Optional[StripeSubscription]:
    db_subscription = StripeSubscription(
        stripe_customer_id=customer_id, **subscription.dict()
    )
    db.add(db_subscription)
    return db_subscription


def create_stripe_subscription_item(
    db: Session,
    subscription_id: str,
    price_id: str,
    subscription_item: StripeSubscriptionItemCreateSchema,
) -> Optional[StripeSubscriptionItem]:
    db_subscription_item = StripeSubscriptionItem(
        stripe_subscription_id=subscription_id,
        stripe_price_id=price_id,
        **subscription_item.dict()
    )
    db.add(db_subscription_item)
    return db_subscription_item
