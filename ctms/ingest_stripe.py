"""
Ingest Stripe data.

This may come from the Firefox Accounts (FxA) Firestore instance.

TODO: Flexibly handle expanded responses.

When requesting data, the default is to include the ID of the related object.
For example, the Customer object has a reference to the default_payment_method.
When making the request, you can specify that some references can be expanded.
For example, the default_payment_method can be expanded from an ID to the full
Payment Method object.
This code should handle both when the related object is an ID and when it is
an expanded object, so that it is flexible for FxA request changes.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional
from uuid import uuid4

from ctms.crud import (
    create_email,
    create_fxa,
    create_stripe_customer,
    create_stripe_invoice,
    create_stripe_invoice_line_item,
    create_stripe_price,
    create_stripe_subscription,
    create_stripe_subscription_item,
    get_emails_by_any_id,
    get_stripe_customer_by_stripe_id,
    get_stripe_invoice_by_stripe_id,
    get_stripe_invoice_line_item_by_stripe_id,
    get_stripe_price_by_stripe_id,
    get_stripe_subscription_by_stripe_id,
    get_stripe_subscription_item_by_stripe_id,
)
from ctms.models import (  # TODO: Move into TYPE_CHECKING after pylint update
    StripeBase,
    StripeCustomer,
    StripeInvoice,
    StripeInvoiceLineItem,
    StripePrice,
    StripeSubscription,
    StripeSubscriptionItem,
)
from ctms.schemas import (
    EmailInSchema,
    FirefoxAccountsInSchema,
    StripeCustomerCreateSchema,
    StripeInvoiceCreateSchema,
    StripeInvoiceLineItemCreateSchema,
    StripePriceCreateSchema,
    StripeSubscriptionCreateSchema,
    StripeSubscriptionItemCreateSchema,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def from_ts(timestamp: Optional[int]) -> datetime:
    """Convert from a (possibly None) timestamp to a UTC datetime."""
    if not timestamp:
        return None
    return datetime.utcfromtimestamp(timestamp)


def ingest_stripe_customer(
    db_session: Session, data: Dict[str, Any]
) -> Optional[StripeCustomer]:
    """
    Ingest a Stripe Customer object.

    If there is a match by customer ID, then the fields are updated (but no
    further contact fields)

    If there is no existing Customer with that ID, then a new customer record
    is created, and associated with an existing contact (if matched by FxA ID,
    or falling back to email), or a new contact.

    TODO: Handle expanded default_source
    TODO: Handle expanded invoice_settings.default_payment_method
    """
    assert data["object"] == "customer", data.get("object", "[MISSING]")
    customer_id = data["id"]
    is_deleted = data.get("deleted", False)

    customer = get_stripe_customer_by_stripe_id(db_session, customer_id)
    if customer:
        if is_deleted:
            # Mark customer as deleted. Downstream consumers may need to
            # be updated before the data is cleaned up.
            customer.deleted = True
        else:
            # Update existing customer
            customer.created = from_ts(data["created"])
            customer.default_source_id = data["default_source"]
            _dpm = data["invoice_settings"]["default_payment_method"]
            customer.invoice_settings_default_payment_method_id = _dpm
        return customer

    if is_deleted:
        # Do not create records for deleted Customer records.
        return None

    # Create new customer
    fxa_id = data["description"]
    emails = get_emails_by_any_id(db_session, fxa_id=fxa_id)
    if len(emails) == 0:
        # Try by primary email
        email = data["email"]
        emails = get_emails_by_any_id(db_session, primary_email=email)
        if emails:
            assert len(emails) == 1
            email_id = emails[0].email_id
        else:
            # Create new contact
            email_id = uuid4()
            new_email = EmailInSchema(email_id=email_id, primary_email=email)
            create_email(db_session, new_email)

        # Create new FxA row
        new_fxa = FirefoxAccountsInSchema(fxa_id=fxa_id, primary_email=email)
        create_fxa(db_session, email_id, new_fxa)
    else:
        # Associate with existing contact
        assert len(emails) == 1
        email_id = emails[0].email_id

    _dpm = data["invoice_settings"]["default_payment_method"]
    schema = StripeCustomerCreateSchema(
        stripe_id=customer_id,
        stripe_created=data["created"],
        email_id=email_id,
        deleted=data.get("deleted", False),
        default_source_id=data["default_source"],
        invoice_settings_default_payment_method_id=_dpm,
    )
    return create_stripe_customer(db_session, schema)


def ingest_stripe_subscription(
    db_session: Session, data: Dict[str, Any]
) -> StripeSubscription:
    """
    Ingest a Stripe Subscription object.

    TODO: Handle expanded customer
    TODO: Handle expanded default_payment_method
    TODO: Handle expanded latest_invoice
    TODO: Handle expanded default_source
    """
    assert data["object"] == "subscription", data.get("object", "[MISSING]")
    subscription_id = data["id"]

    subscription = get_stripe_subscription_by_stripe_id(db_session, subscription_id)
    if subscription:
        subscription.stripe_created = from_ts(data["created"])
        subscription.stripe_customer_id = data["customer"]
        subscription.default_payment_method_id = data["default_payment_method"]
        subscription.default_source_id = data["default_source"]
        subscription.cancel_at_period_end = data["cancel_at_period_end"]
        subscription.canceled_at = from_ts(data["canceled_at"])
        subscription.current_period_end = from_ts(data["current_period_end"])
        subscription.current_period_start = from_ts(data["current_period_start"])
        subscription.ended_at = from_ts(data["ended_at"])
        subscription.start_date = from_ts(data["start_date"])
        subscription.status = data["status"]
        sub_items_to_delete = {
            sub_item.stripe_id for sub_item in subscription.subscription_items
        }
    else:
        schema = StripeSubscriptionCreateSchema(
            stripe_id=subscription_id,
            stripe_created=data["created"],
            stripe_customer_id=data["customer"],
            default_payment_method_id=data["default_payment_method"],
            default_source_id=data["default_source"],
            cancel_at_period_end=data["cancel_at_period_end"],
            canceled_at=data["canceled_at"],
            current_period_end=data["current_period_end"],
            current_period_start=data["current_period_start"],
            ended_at=data["ended_at"],
            start_date=data["start_date"],
            status=data["status"],
        )
        subscription = create_stripe_subscription(db_session, schema)
        sub_items_to_delete = set()

    for item_data in data["items"]["data"]:
        sub_items_to_delete.discard(item_data["id"])
        ingest_stripe_subscription_item(db_session, item_data)

    # Remove any orphaned subscription items
    if sub_items_to_delete:
        (
            db_session.query(StripeSubscriptionItem)
            .filter(StripeSubscriptionItem.stripe_id.in_(sub_items_to_delete))
            .delete(synchronize_session=False)
        )

    return subscription


def ingest_stripe_subscription_item(
    db_session: Session, data: Dict[str, Any]
) -> StripeSubscriptionItem:
    """Ingest a Stripe Subscription Item object."""
    assert data["object"] == "subscription_item", data.get("object", "[MISSING]")

    # Price is always included, and should be created first if new
    price = ingest_stripe_price(db_session, data["price"])

    subscription_item_id = data["id"]
    subscription_item = get_stripe_subscription_item_by_stripe_id(
        db_session, subscription_item_id
    )
    if subscription_item:
        subscription_item.stripe_created = from_ts(data["created"])
        subscription_item.stripe_price_id = price.stripe_id
        subscription_item.stripe_subscription_id = data["subscription"]
    else:
        schema = StripeSubscriptionItemCreateSchema(
            stripe_id=subscription_item_id,
            stripe_created=data["created"],
            stripe_price_id=price.stripe_id,
            stripe_subscription_id=data["subscription"],
        )
        subscription_item = create_stripe_subscription_item(db_session, schema)

    return subscription_item


def ingest_stripe_price(db_session: Session, data: Dict[str, Any]) -> StripePrice:
    """
    Ingest a Stripe Price object.

    TODO: Handle expanded product
    """
    assert data["object"] == "price", data.get("object", "[MISSING]")
    price_id = data["id"]
    recurring = data.get("recurring", {})
    price = get_stripe_price_by_stripe_id(db_session, price_id)
    if price:
        price.stripe_created = from_ts(data["created"])
        price.stripe_product_id = data["product"]
        price.active = data["active"]
        price.currency = data["currency"]
        price.recurring_interval = recurring.get("interval")
        price.recurring_interval_count = recurring.get("interval_count")
        price.unit_amount = data.get("unit_amount")
    else:
        schema = StripePriceCreateSchema(
            stripe_id=price_id,
            stripe_created=data["created"],
            stripe_product_id=data["product"],
            active=data["active"],
            currency=data["currency"],
            recurring_interval=recurring.get("interval"),
            recurring_interval_count=recurring.get("interval_count"),
            unit_amount=data.get("unit_amount"),
        )
        price = create_stripe_price(db_session, schema)
    return price


def ingest_stripe_invoice(db_session: Session, data: Dict[str, Any]) -> StripeInvoice:
    """
    Ingest a Stripe Invoice object.

    TODO: Handle expanded customer
    TODO: Handle expanded subscription
    TODO: Handle expanded default_payment_method
    TODO: Handle expanded default_source
    """
    assert data["object"] == "invoice", data.get("object", "[MISSING]")
    invoice_id = data["id"]
    invoice = get_stripe_invoice_by_stripe_id(db_session, invoice_id)
    if invoice:
        invoice.stripe_created = from_ts(data["created"])
        invoice.stripe_customer_id = data["customer"]
        invoice.currency = data["currency"]
        invoice.total = data["total"]
        invoice.status = data["status"]
        invoice.default_payment_method_id = data["default_payment_method"]
        invoice.default_source = data["default_source"]
        lines_to_delete = {line.stripe_id for line in invoice.line_items}
    else:
        schema = StripeInvoiceCreateSchema(
            stripe_id=invoice_id,
            stripe_created=data["created"],
            stripe_customer_id=data["customer"],
            currency=data["currency"],
            total=data["total"],
            status=data["status"],
            default_payment_method_id=data["default_payment_method"],
            default_source=data["default_source"],
        )
        invoice = create_stripe_invoice(db_session, schema)
        lines_to_delete = set()

    for line_data in data["lines"]["data"]:
        lines_to_delete.discard(line_data["id"])
        ingest_stripe_invoice_line_item(db_session, invoice_id, line_data)

    # Remove any orphaned invoice items
    if lines_to_delete:
        (
            db_session.query(StripeInvoiceLineItem)
            .filter(StripeInvoiceLineItem.stripe_id.in_(lines_to_delete))
            .delete(synchronize_session=False)
        )

    return invoice


def ingest_stripe_invoice_line_item(
    db_session: Session, invoice_id: str, data: Dict[str, Any]
) -> StripeInvoiceLineItem:
    """Ingest a Stripe Line Item object."""
    assert data["object"] == "line_item", data.get("object", "[MISSING]")

    # Price is always included, and should be created first if new
    price = ingest_stripe_price(db_session, data["price"])

    invoice_line_item_id = data["id"]
    invoice_line_item = get_stripe_invoice_line_item_by_stripe_id(
        db_session, invoice_line_item_id
    )
    if invoice_line_item:
        invoice_line_item.stripe_type = data["type"]
        invoice_line_item.stripe_price_id = price.stripe_id
        invoice_line_item.stripe_invoice_item_id = data.get("invoice_item")
        invoice_line_item.stripe_subscription_id = data.get("subscription")
        invoice_line_item.stripe_subscription_item = data.get("subscription_item")
        invoice_line_item.amount = data["amount"]
        invoice_line_item.currency = data["currency"]
    else:
        schema = StripeInvoiceLineItemCreateSchema(
            stripe_id=invoice_line_item_id,
            stripe_type=data["type"],
            stripe_price_id=price.stripe_id,
            stripe_invoice_id=invoice_id,
            stripe_invoice_item_id=data.get("invoice_item"),
            stripe_subscription_id=data.get("subscription"),
            stripe_subscription_item_id=data.get("subscription_item"),
            amount=data["amount"],
            currency=data["currency"],
        )
        invoice_line_item = create_stripe_invoice_line_item(db_session, schema)

    return invoice_line_item


INGESTERS: Dict[str, Callable[[Session, Dict[str, Any]], StripeBase]] = {
    "customer": ingest_stripe_customer,
    "invoice": ingest_stripe_invoice,
    "subscription": ingest_stripe_subscription,
    "subscription_item": ingest_stripe_subscription_item,
    "price": ingest_stripe_price,
}


class StripeIngestError(Exception):
    """Base class for errors when ingesting a Stripe object."""


class StripeIngestBadObjectError(StripeIngestError):
    def __init__(self, the_object, *args, **kwargs):
        self.the_object = the_object
        StripeIngestError.__init__(self, *args, **kwargs)

    def __str__(self):
        return "Data is not a Stripe object."

    def __repr__(self):
        return f"{self.__class__.__name__}({self.the_object!r})"


class StripeIngestUnknownObjectError(StripeIngestError):
    def __init__(self, object_value, *args, **kwargs):
        self.object_value = object_value
        StripeIngestError.__init__(self, *args, **kwargs)

    def __str__(self):
        return f"Unknown Stripe object {self.object_value!r}."

    def __repr__(self):
        return f"{self.__class__.__name__}({self.object_value!r})"


def ingest_stripe_object(
    db_session: Session, data: Dict[str, Any]
) -> Optional[StripeBase]:

    try:
        object_type = data["object"]
    except (TypeError, KeyError) as exception:
        raise StripeIngestBadObjectError(data) from exception

    try:
        ingester = INGESTERS[object_type]
    except KeyError as exception:
        raise StripeIngestUnknownObjectError(object_type) from exception

    return ingester(db_session, data)
