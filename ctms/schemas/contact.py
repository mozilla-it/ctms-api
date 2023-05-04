from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING, List, Literal, Optional, Set, Union, cast
from uuid import UUID

from pydantic import AnyUrl, BaseModel, Field, root_validator, validator

from .addons import AddOnsInSchema, AddOnsSchema
from .base import ComparableBase
from .email import (
    EmailBase,
    EmailInSchema,
    EmailPatchSchema,
    EmailPutSchema,
    EmailSchema,
)
from .fxa import FirefoxAccountsInSchema, FirefoxAccountsSchema
from .mofo import MozillaFoundationInSchema, MozillaFoundationSchema
from .newsletter import NewsletterInSchema, NewsletterSchema
from .product import ProductBaseSchema
from .waitlist import (
    RelayWaitlistInSchema,
    RelayWaitlistSchema,
    VpnWaitlistInSchema,
    VpnWaitlistSchema,
    WaitlistInSchema,
    WaitlistSchema,
    validate_waitlist_newsletters,
)

if TYPE_CHECKING:
    from models import Email


def get_stripe_products(email: "Email") -> List[ProductBaseSchema]:
    """Return a list of Stripe products for the contact, if any."""
    if not email.stripe_customer:
        return []

    base_data: dict[str, Any] = {
        "payment_service": "stripe",
        # These come from the Payment Method, not imported from Stripe.
        "payment_type": None,
        "card_brand": None,
        "card_last4": None,
        "billing_country": None,
    }
    by_product = defaultdict(list)

    for subscription in email.stripe_customer.subscriptions:
        subscription_data = base_data.copy()
        subscription_data.update(
            {
                "status": subscription.status,
                "created": subscription.stripe_created,
                "start": subscription.start_date,
                "current_period_start": subscription.current_period_start,
                "current_period_end": subscription.current_period_end,
                "canceled_at": subscription.canceled_at,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "ended_at": subscription.ended_at,
            }
        )
        for item in subscription.subscription_items:
            product_data = subscription_data.copy()
            price = item.price
            product_data.update(
                {
                    "product_id": price.stripe_product_id,
                    "product_name": None,  # Products are not imported
                    "price_id": price.stripe_id,
                    "currency": price.currency,
                    "amount": price.unit_amount,
                    "interval_count": price.recurring_interval_count,
                    "interval": price.recurring_interval,
                }
            )
            by_product[price.stripe_product_id].append(product_data)

    products = []
    for subscriptions in by_product.values():
        subscriptions.sort(
            key=lambda sub: cast(datetime, sub["current_period_end"]), reverse=True
        )
        latest = subscriptions[0]
        data = latest.copy()
        if len(subscriptions) == 1:
            segment_prefix = ""
        else:
            segment_prefix = "re-"
        if latest["status"] == "active":
            if latest["canceled_at"]:
                segment = "cancelling"
                changed = latest["canceled_at"]
            else:
                segment = "active"
                changed = latest["start"]
        elif latest["status"] == "canceled":
            segment = "canceled"
            changed = latest["ended_at"]
        else:
            segment_prefix = ""
            segment = "other"
            changed = latest["created"]

        assert changed
        data.update(
            {
                "sub_count": len(subscriptions),
                "segment": f"{segment_prefix}{segment}",
                "changed": changed,
            }
        )
        products.append(ProductBaseSchema(**data))

    products.sort(key=lambda prod: prod.product_id or "")
    return products


class ContactSchema(ComparableBase):
    """A complete contact."""

    amo: Optional[AddOnsSchema] = None
    email: EmailSchema
    fxa: Optional[FirefoxAccountsSchema] = None
    mofo: Optional[MozillaFoundationSchema] = None
    newsletters: List[NewsletterSchema] = []
    waitlists: List[WaitlistSchema] = []
    products: List[ProductBaseSchema] = []

    @classmethod
    def from_email(cls, email: "Email") -> "ContactSchema":
        return cls(
            amo=email.amo,
            email=email,
            fxa=email.fxa,
            mofo=email.mofo,
            newsletters=email.newsletters,
            waitlists=email.waitlists,
            products=get_stripe_products(email),
        )

    class Config:
        fields = {
            "newsletters": {
                "description": "List of newsletters for which the contact is or was subscribed",
                "example": [{"name": "firefox-welcome"}, {"name": "mozilla-welcome"}],
            },
            "waitlists": {
                "description": "List of waitlists for which the contact is or was subscribed",
                "example": [
                    {
                        "name": "example-product",
                        "fields": {"geo": "fr", "platform": "win64"},
                    },
                    {
                        "name": "relay",
                        "fields": {"geo": "fr"},
                    },
                    {
                        "name": "vpn",
                        "fields": {"geo": "fr", "platform": "ios,mac"},
                    },
                ],
            },
        }

    def as_identity_response(self) -> "IdentityResponse":
        """Return the identities of a contact"""
        return IdentityResponse(
            amo_user_id=getattr(self.amo, "user_id", None),
            basket_token=getattr(self.email, "basket_token", None),
            email_id=getattr(self.email, "email_id", None),
            fxa_id=getattr(self.fxa, "fxa_id", None),
            fxa_primary_email=getattr(self.fxa, "primary_email", None),
            mofo_contact_id=getattr(self.mofo, "mofo_contact_id", None),
            mofo_email_id=getattr(self.mofo, "mofo_email_id", None),
            primary_email=getattr(self.email, "primary_email", None),
            sfdc_id=getattr(self.email, "sfdc_id", None),
        )

    def find_default_fields(self) -> Set[str]:
        """Return names of fields that contain default values only"""
        default_fields = set()
        if hasattr(self, "amo") and self.amo and self.amo.is_default():
            default_fields.add("amo")
        if hasattr(self, "fxa") and self.fxa and self.fxa.is_default():
            default_fields.add("fxa")
        if hasattr(self, "mofo") and self.mofo and self.mofo.is_default():
            default_fields.add("mofo")
        if all(n.is_default() for n in self.newsletters):
            default_fields.add("newsletters")
        if all(n.is_default() for n in self.waitlists):
            default_fields.add("waitlists")
        return default_fields


class ContactInBase(ComparableBase):
    """A contact as provided by callers."""

    amo: Optional[AddOnsInSchema] = None
    email: EmailBase
    fxa: Optional[FirefoxAccountsInSchema] = None
    mofo: Optional[MozillaFoundationInSchema] = None
    newsletters: List[NewsletterInSchema] = []
    waitlists: List[WaitlistInSchema] = []
    # TODO waitlist: remove once Basket leverages the `waitlists` field.
    vpn_waitlist: Optional[VpnWaitlistInSchema] = None
    relay_waitlist: Optional[RelayWaitlistInSchema] = None

    class Config:
        fields = ContactSchema.Config.fields

    @root_validator
    def check_fields(cls, values):  # pylint:disable = no-self-argument
        """
        This makes sure a Relay country is specified when one of the `relay-*-waitlist`
        newsletter is subscribed.

        TODO waitlist: remove once Basket leverages the `waitlists` field.
        """
        return validate_waitlist_newsletters(values)

    def idempotent_equal(self, other):
        def _noneify(field):
            if not field:
                return None
            return None if field.is_default() else field

        return (
            self.email == other.email
            and _noneify(self.amo) == _noneify(other.amo)
            and _noneify(self.fxa) == _noneify(other.fxa)
            and _noneify(self.mofo) == _noneify(other.mofo)
            and sorted(self.newsletters) == sorted(other.newsletters)
            and sorted(self.waitlists) == sorted(other.waitlists)
        )


class ContactInSchema(ContactInBase):
    """A contact as provided by callers when using POST. This is nearly identical to the ContactPutSchema but doesn't require an email_id."""

    email: EmailInSchema


class ContactPutSchema(ContactInBase):
    """A contact as provided by callers when using PUT. This is nearly identical to the ContactInSchema but does require an email_id."""

    email: EmailPutSchema


class ContactPatchSchema(ComparableBase):
    """A contact provided by callers when using PATCH.

    This is nearly identical to ContactInSchema, but almost everything
    is optional, and some values can be action strings (like "DELETE" or
    "UNSUBSCRIBE" instead of lists or objects.
    """

    amo: Optional[Union[Literal["DELETE"], AddOnsInSchema]]
    email: Optional[EmailPatchSchema]
    fxa: Optional[Union[Literal["DELETE"], FirefoxAccountsInSchema]]
    mofo: Optional[Union[Literal["DELETE"], MozillaFoundationInSchema]]
    newsletters: Optional[Union[List[NewsletterSchema], Literal["UNSUBSCRIBE"]]]
    waitlists: Optional[Union[List[WaitlistInSchema], Literal["UNSUBSCRIBE"]]]
    # TODO waitlist: remove once Basket leverages the `waitlists` field.
    vpn_waitlist: Optional[Union[Literal["DELETE"], VpnWaitlistInSchema]]
    relay_waitlist: Optional[Union[Literal["DELETE"], RelayWaitlistInSchema]]

    @root_validator
    def check_fields(cls, values):  # pylint:disable = no-self-argument
        """
        This makes sure a Relay country is specified when one of the `relay-*-waitlist`
        newsletter is subscribed.

        TODO waitlist: remove once Basket leverages the `waitlists` field.
        """
        return validate_waitlist_newsletters(values)

    class Config:
        fields = {
            "amo": {"description": 'Add-ons data to update, or "DELETE" to reset.'},
            "fxa": {
                "description": 'Firefox Accounts data to update, or "DELETE" to reset.'
            },
            "mofo": {
                "description": 'Mozilla Foundation data to update, or "DELETE" to reset.'
            },
            "newsletters": {
                "description": (
                    "List of newsletters to add or update, or 'UNSUBSCRIBE' to"
                    " unsubscribe from all."
                ),
                "example": [{"name": "firefox-welcome", "subscribed": False}],
            },
            "vpn_waitlist": {
                "description": 'VPN Waitlist data to update, or "DELETE" to reset.'
            },
            "relay_waitlist": {
                "description": 'Relay Waitlist data to update, or "DELETE" to reset.'
            },
            "waitlists": {
                "description": ("List of waitlists to add or update."),
                "example": [
                    {
                        "name": "example-product",
                        "fields": {"geo": "fr", "platform": "win64"},
                    }
                ],
            },
        }


class CTMSResponse(BaseModel):
    """
    Response for GET /ctms/ by alternate IDs

    Similar to ContactSchema, but groups are required
    """

    amo: AddOnsSchema
    email: EmailSchema
    fxa: FirefoxAccountsSchema
    mofo: MozillaFoundationSchema
    newsletters: List[NewsletterSchema]
    waitlists: List[WaitlistSchema]
    # Retro-compat fields
    vpn_waitlist: VpnWaitlistSchema
    relay_waitlist: RelayWaitlistSchema

    @validator("amo", pre=True, always=True)
    def set_default_amo(cls, value):  # pylint: disable=no-self-argument
        return value or AddOnsSchema()

    @validator("fxa", pre=True, always=True)
    def set_default_fxa(cls, value):  # pylint: disable=no-self-argument
        return value or FirefoxAccountsSchema()

    @validator("mofo", pre=True, always=True)
    def set_default_mofo(cls, value):  # pylint: disable=no-self-argument
        return value or MozillaFoundationSchema()

    @root_validator(pre=True)
    def legacy_waitlists(cls, values):  # pylint: disable=no-self-argument
        # Show computed fields in response for retro-compatibility.
        values["vpn_waitlist"] = VpnWaitlistSchema()
        values["relay_waitlist"] = RelayWaitlistSchema()
        for waitlist in values.get("waitlists", []):
            if isinstance(waitlist, dict):
                # TODO: figure out why dict from `response_model` decorators param in app.py)
                waitlist = WaitlistSchema(**waitlist)
            if isinstance(waitlist, WaitlistInSchema):
                # Many tests instantiates CTMSResponse with `WaitlistInSchema` (input schema).
                waitlist = WaitlistSchema(**waitlist.dict())
            if waitlist.name == "vpn":
                values["vpn_waitlist"] = VpnWaitlistSchema(
                    geo=waitlist.fields.get("geo"),
                    platform=waitlist.fields.get("platform"),
                )
            # If multiple `relay-` waitlists are present, the `geo` field of the
            # first waitlist is set as the value of `relay_waitlist["geo"]`. This
            # property is intended for legacy consumers. New consumers should prefer the
            # `waitlists` property of the contact schema
            if (
                waitlist.name.startswith("relay")
                and values["relay_waitlist"].geo is None
            ):
                values["relay_waitlist"] = RelayWaitlistSchema(
                    geo=waitlist.fields.get("geo")
                )

        return values


class CTMSSingleResponse(CTMSResponse):
    """
    Response for /ctms/<email_id>

    Similar to ContactSchema, but groups are required and includes status: OK
    """

    status: Literal["ok"] = Field(
        default="ok", description="Request was successful", example="ok"
    )


class CTMSBulkResponse(BaseModel):
    """
    Response for GET /updates/

    """

    start: datetime
    end: datetime
    limit: int
    after: Optional[str] = None
    next: Optional[Union[AnyUrl, str]] = None
    items: List[CTMSResponse]


class IdentityResponse(BaseModel):
    """The identity keys for a contact."""

    email_id: UUID
    primary_email: str
    basket_token: Optional[UUID] = None
    sfdc_id: Optional[str] = None
    mofo_contact_id: Optional[str] = None
    mofo_email_id: Optional[str] = None
    amo_user_id: Optional[str] = None
    fxa_id: Optional[str] = None
    fxa_primary_email: Optional[str] = None
