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
    get_emails_by_any_id,
    get_stripe_customer_by_stripe_id,
)
from ctms.models import (  # TODO: Move into TYPE_CHECKING after pylint update
    StripeBase,
    StripeCustomer,
)
from ctms.schemas import (
    EmailInSchema,
    FirefoxAccountsInSchema,
    StripeCustomerCreateSchema,
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


INGESTERS: Dict[str, Callable[[Session, Dict[str, Any]], StripeBase]] = {
    "customer": ingest_stripe_customer,
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
