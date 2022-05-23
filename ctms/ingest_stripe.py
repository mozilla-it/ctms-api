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

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Set, Tuple, cast

from ctms.crud import (
    StripeModel,
    create_stripe_customer,
    create_stripe_invoice,
    create_stripe_invoice_line_item,
    create_stripe_price,
    create_stripe_subscription,
    create_stripe_subscription_item,
    get_stripe_customer_by_fxa_id,
    get_stripe_customer_by_stripe_id,
    get_stripe_invoice_by_stripe_id,
    get_stripe_invoice_line_item_by_stripe_id,
    get_stripe_price_by_stripe_id,
    get_stripe_subscription_by_stripe_id,
    get_stripe_subscription_item_by_stripe_id,
    schedule_acoustic_record,
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
    StripeCustomerCreateSchema,
    StripeInvoiceCreateSchema,
    StripeInvoiceLineItemCreateSchema,
    StripePriceCreateSchema,
    StripeSubscriptionCreateSchema,
    StripeSubscriptionItemCreateSchema,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


# What actions were taken by an ingester
StripeIngestActions = Dict[str, Set]


def from_ts(timestamp: Optional[int]) -> datetime:
    """Convert from a (possibly None) timestamp to a UTC datetime."""
    if not timestamp:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


class StripeIngestError(Exception):
    """Base class for errors when ingesting a Stripe object."""


class StripeIngestFxAIdConflict(StripeIngestError):
    """
    An existing StripeCustomer has the same FxA ID.

    Duplicate FxA IDs have been seen in the staging instance, due to bugs or
    direct interaction with Stripe.
    """

    def __init__(self, stripe_id, fxa_id, *args, **kwargs):
        self.stripe_id = stripe_id
        self.fxa_id = fxa_id
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"Existing StripeCustomer {self.stripe_id!r} has FxA ID {self.fxa_id!r}."

    def __repr__(self):
        return f"{self.__class__.__name__}({self.stripe_id!r}, {self.fxa_id!r})"


def ingest_stripe_customer(
    db_session: Session, data: Dict[str, Any]
) -> Tuple[Optional[StripeCustomer], StripeIngestActions]:
    """
    Ingest a Stripe Customer object.

    Raises StripeIngestFxAIdConflict if an existing StripeCustomer has the same
    FxA ID.

    TODO: Handle expanded default_source
    TODO: Handle expanded invoice_settings.default_payment_method
    """
    assert data["object"] == "customer", data.get("object", "[MISSING]")
    customer_id = data["id"]
    fxa_id = data.get("description")
    is_deleted = data.get("deleted", False)

    customer = get_stripe_customer_by_stripe_id(
        db_session, customer_id, for_update=True
    )

    # Detect duplicate FxA ID
    fxa_check = fxa_id and ((customer is None) or (customer.fxa_id != fxa_id))
    if fxa_check:
        by_fxa = get_stripe_customer_by_fxa_id(db_session, fxa_id, for_update=True)
        if by_fxa is not None:
            raise StripeIngestFxAIdConflict(by_fxa.stripe_id, fxa_id)

    if customer:
        orig_dict = customer.__dict__.copy()
        if is_deleted:
            # Mark customer as deleted. Downstream consumers may need to
            # be updated before the data is cleaned up.
            customer.deleted = True
        else:
            # Update existing customer
            customer.created = from_ts(data["created"])
            customer.fxa_id = fxa_id
            customer.default_source_id = data["default_source"]
            _dpm = data["invoice_settings"]["default_payment_method"]
            customer.invoice_settings_default_payment_method_id = _dpm
        action = "no_change" if customer.__dict__ == orig_dict else "updated"
        return customer, {
            action: {
                f"{data['object']}:{customer_id}",
            }
        }

    if is_deleted:
        # Do not create records for deleted Customer records.
        return None, {
            "skipped": {
                f"{data['object']}:{customer_id}",
            }
        }

    _dpm = data["invoice_settings"]["default_payment_method"]
    schema = StripeCustomerCreateSchema(
        stripe_id=customer_id,
        stripe_created=data["created"],
        fxa_id=fxa_id,
        deleted=data.get("deleted", False),
        default_source_id=data["default_source"],
        invoice_settings_default_payment_method_id=_dpm,
    )
    return create_stripe_customer(db_session, schema), {
        "created": {
            f"{data['object']}:{customer_id}",
        }
    }


def ingest_stripe_subscription(
    db_session: Session, data: Dict[str, Any]
) -> Tuple[StripeSubscription, StripeIngestActions]:
    """
    Ingest a Stripe Subscription object.

    TODO: Handle expanded customer
    TODO: Handle expanded default_payment_method
    TODO: Handle expanded latest_invoice
    TODO: Handle expanded default_source
    """
    assert data["object"] == "subscription", data.get("object", "[MISSING]")
    subscription_id = data["id"]

    subscription = get_stripe_subscription_by_stripe_id(
        db_session, subscription_id, for_update=True
    )
    if subscription:
        orig_dict = subscription.__dict__.copy()
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
            sub_item_id
            for sub_item_id, in (
                db_session.query(StripeSubscriptionItem.stripe_id)
                .with_for_update()
                .filter(
                    StripeSubscriptionItem.stripe_subscription_id
                    == subscription.stripe_id
                )
                .all()
            )
        }
        action = "no_change" if subscription.__dict__ == orig_dict else "updated"
    else:
        action = "created"
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
    actions = {
        action: {
            f"{data['object']}:{data['id']}",
        }
    }

    for item_data in data["items"]["data"]:
        sub_items_to_delete.discard(item_data["id"])
        _, item_actions = ingest_stripe_subscription_item(db_session, item_data)
        for key, values in item_actions.items():
            actions.setdefault(key, set()).update(cast(set, values))

    # Remove any orphaned subscription items
    if sub_items_to_delete:
        (
            db_session.query(StripeSubscriptionItem)
            .filter(StripeSubscriptionItem.stripe_id.in_(sub_items_to_delete))
            .delete(synchronize_session=False)
        )
        actions.setdefault("deleted", set()).update(
            {f"subscription_item:{item_id}" for item_id in sub_items_to_delete}
        )

    return subscription, actions


def ingest_stripe_subscription_item(
    db_session: Session, data: Dict[str, Any]
) -> Tuple[StripeSubscriptionItem, StripeIngestActions]:
    """Ingest a Stripe Subscription Item object."""
    assert data["object"] == "subscription_item", data.get("object", "[MISSING]")

    # Price is always included, and should be created first if new
    price, actions = ingest_stripe_price(db_session, data["price"])

    subscription_item_id = data["id"]
    subscription_item = get_stripe_subscription_item_by_stripe_id(
        db_session, subscription_item_id, for_update=True
    )
    if subscription_item:
        orig_dict = subscription_item.__dict__.copy()
        subscription_item.stripe_created = from_ts(data["created"])
        subscription_item.stripe_price_id = price.stripe_id
        subscription_item.stripe_subscription_id = data["subscription"]
        action = "no_change" if subscription_item.__dict__ == orig_dict else "updated"
    else:
        action = "created"
        schema = StripeSubscriptionItemCreateSchema(
            stripe_id=subscription_item_id,
            stripe_created=data["created"],
            stripe_price_id=price.stripe_id,
            stripe_subscription_id=data["subscription"],
        )
        subscription_item = create_stripe_subscription_item(db_session, schema)

    actions.setdefault(action, set()).add(f"{data['object']}:{data['id']}")
    return subscription_item, actions


def ingest_stripe_price(
    db_session: Session, data: Dict[str, Any]
) -> Tuple[StripePrice, StripeIngestActions]:
    """
    Ingest a Stripe Price object.

    TODO: Handle expanded product
    """
    assert data["object"] == "price", data.get("object", "[MISSING]")
    price_id = data["id"]
    recurring = data.get("recurring", {})
    price = get_stripe_price_by_stripe_id(db_session, price_id, for_update=False)
    if price:
        orig_dict = price.__dict__.copy()
        price.stripe_created = from_ts(data["created"])
        price.stripe_product_id = data["product"]
        price.active = data["active"]
        price.currency = data["currency"]
        price.recurring_interval = recurring.get("interval")
        price.recurring_interval_count = recurring.get("interval_count")
        price.unit_amount = data.get("unit_amount")
        action = "no_change" if price.__dict__ == orig_dict else "updated"
    else:
        action = "created"
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
    return price, {
        action: {
            f"{data['object']}:{data['id']}",
        }
    }


def ingest_stripe_invoice(
    db_session: Session, data: Dict[str, Any]
) -> Tuple[StripeInvoice, StripeIngestActions]:
    """
    Ingest a Stripe Invoice object.

    TODO: Handle expanded customer
    TODO: Handle expanded subscription
    TODO: Handle expanded default_payment_method
    TODO: Handle expanded default_source
    """
    assert data["object"] == "invoice", data.get("object", "[MISSING]")
    invoice_id = data["id"]
    invoice = get_stripe_invoice_by_stripe_id(db_session, invoice_id, for_update=True)
    if invoice:
        orig_dict = invoice.__dict__.copy()
        invoice.stripe_created = from_ts(data["created"])
        invoice.stripe_customer_id = data["customer"]
        invoice.currency = data["currency"]
        invoice.total = data["total"]
        invoice.status = data["status"]
        invoice.default_payment_method_id = data["default_payment_method"]
        invoice.default_source_id = data["default_source"]
        lines_to_delete = {
            line_id
            for line_id, in (
                db_session.query(StripeInvoiceLineItem.stripe_id)
                .with_for_update()
                .filter(StripeInvoiceLineItem.stripe_invoice_id == invoice.stripe_id)
                .all()
            )
        }
        action = "no_change" if invoice.__dict__ == orig_dict else "updated"
    else:
        action = "created"
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
    actions = {
        action: {
            f"{data['object']}:{data['id']}",
        }
    }

    for line_data in data["lines"]["data"]:
        lines_to_delete.discard(line_data["id"])
        _, items_actions = ingest_stripe_invoice_line_item(
            db_session, invoice_id, line_data
        )
        for key, values in items_actions.items():
            actions.setdefault(key, set()).update(values)

    # Remove any orphaned invoice items
    if lines_to_delete:
        (
            db_session.query(StripeInvoiceLineItem)
            .filter(StripeInvoiceLineItem.stripe_id.in_(lines_to_delete))
            .delete(synchronize_session=False)
        )
        actions.setdefault("deleted", set()).update(
            {f"line_item:{item_id}" for item_id in lines_to_delete}
        )

    return invoice, actions


def ingest_stripe_invoice_line_item(
    db_session: Session, invoice_id: str, data: Dict[str, Any]
) -> Tuple[StripeInvoiceLineItem, StripeIngestActions]:
    """Ingest a Stripe Line Item object."""
    assert data["object"] == "line_item", data.get("object", "[MISSING]")

    # Price is always included, and should be created first if new
    price, actions = ingest_stripe_price(db_session, data["price"])

    invoice_line_item_id = data["id"]
    invoice_line_item = get_stripe_invoice_line_item_by_stripe_id(
        db_session, invoice_line_item_id, for_update=True
    )
    if invoice_line_item:
        orig_dict = invoice_line_item.__dict__.copy()
        invoice_line_item.stripe_type = data["type"]
        invoice_line_item.stripe_price_id = price.stripe_id
        invoice_line_item.stripe_invoice_item_id = data.get("invoice_item")
        invoice_line_item.stripe_subscription_id = data.get("subscription")
        invoice_line_item.stripe_subscription_item_id = data.get("subscription_item")
        invoice_line_item.amount = data["amount"]
        invoice_line_item.currency = data["currency"]
        action = "no_change" if invoice_line_item.__dict__ == orig_dict else "updated"
    else:
        action = "created"
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

    actions.setdefault(action, set()).add(f"{data['object']}:{data['id']}")
    return invoice_line_item, actions


INGESTERS: Dict[
    str, Callable[[Session, Dict[str, Any]], Tuple[StripeBase, StripeIngestActions]]
] = {
    "customer": ingest_stripe_customer,
    "invoice": ingest_stripe_invoice,
    "subscription": ingest_stripe_subscription,
    "subscription_item": ingest_stripe_subscription_item,
    "price": ingest_stripe_price,
}


class StripeIngestBadObjectError(StripeIngestError):
    def __init__(self, the_object, *args, **kwargs):
        self.the_object = the_object
        StripeIngestError.__init__(self, *args, **kwargs)

    def __str__(self):
        return "Data is not a Stripe object."

    def __repr__(self):
        return f"{self.__class__.__name__}({self.the_object!r})"


class StripeIngestUnknownObjectError(StripeIngestError):
    def __init__(self, object_value, object_id, *args, **kwargs):
        self.object_value = object_value
        self.object_id = object_id
        StripeIngestError.__init__(self, *args, **kwargs)

    def __str__(self):
        return (
            f"Unknown Stripe object {self.object_value!r} with ID {self.object_id!r}."
        )

    def __repr__(self):
        return f"{self.__class__.__name__}({self.object_value!r}, {self.object_id!r})"


class StripeToAcousticParseError(StripeIngestError):
    def __init__(self, object_value, object_id, *args, **kwargs):
        self.object_value = object_value
        self.object_id = object_id
        StripeIngestError.__init__(self, *args, **kwargs)

    def __str__(self):
        return f"Following was not added to Acoustic queue: Stripe object {self.object_value!r} with ID {self.object_id!r}."

    def __repr__(self):
        return f"{self.__class__.__name__}({self.object_value!r}, {self.object_id!r})"


def ingest_stripe_object(
    db_session: Session, data: Dict[str, Any]
) -> Tuple[Optional[StripeBase], StripeIngestActions]:

    try:
        object_type = data["object"]
    except (TypeError, KeyError) as exception:
        raise StripeIngestBadObjectError(data) from exception

    try:
        ingester = INGESTERS[object_type]
    except KeyError as exception:
        raise StripeIngestUnknownObjectError(object_type, data["id"]) from exception

    return ingester(db_session, data)


COLLECTORS: Dict[str, Callable[[Session, Dict[str, Any]], Optional[StripeModel]]] = {
    "customer": get_stripe_customer_by_stripe_id,
    "invoice": get_stripe_invoice_by_stripe_id,
    "subscription": get_stripe_subscription_by_stripe_id,
    "subscription_item": get_stripe_subscription_item_by_stripe_id,
    "price": get_stripe_price_by_stripe_id,
}


def add_stripe_object_to_acoustic_queue(db_session: Session, data: Dict[str, Any]):

    try:
        object_type = data["object"]
        stripe_id = data["id"]
    except (TypeError, KeyError) as exception:
        raise StripeIngestBadObjectError(data) from exception

    try:
        collector = COLLECTORS[object_type]

    except KeyError as exception:
        raise StripeIngestUnknownObjectError(object_type, data["id"]) from exception
    try:
        stripe_object: StripeBase = collector(db_session, stripe_id)
        schedule_acoustic_record(db=db_session, email_id=stripe_object.get_email_id())
    except TypeError as exception:
        raise StripeToAcousticParseError(object_type, data["id"]) from exception
