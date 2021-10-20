from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import Field

from .base import ComparableBase


class StripePaymentMethodTypeEnum(str, Enum):
    """
    Stripe Payment Method type values.

    See https://stripe.com/docs/api/payment_methods/object#payment_method_object-type
    """

    ACSS_DEBIT = "acss_debit"
    AFTERPAY_CLEARPAY = "afterpay_clearpay"
    ALIPAY = "alipay"
    AU_BECS_DEBIT = "au_becs_debit"
    BACS_DEBIT = "bacs_debit"
    BANCONTACT = "bancontact"
    BOLETO = "boleto"
    CARD = "card"
    CARD_PRESENT = "card_present"
    EPS = "eps"
    FPX = "fpx"
    GIROPAY = "giropay"
    GRABPAY = "grabpay"
    IDEAL = "ideal"
    INTERAC_PRESENT = "interac_present"
    KLARNA = "klarna"
    OXXO = "oxxo"
    P24 = "p24"
    SEPA_DEBIT = "sepa_debit"
    SOFORT = "sofort"
    WECHAT_PAY = "wechat_pay"

    # For unknown, possibly new payment methods
    UNKNOWN = "unknown"


class StripePaymentMethodCardBrandEnum(str, Enum):
    """
    Stripe Payment Method card brand values.

    See https://stripe.com/docs/api/payment_methods/object#payment_method_object-card-brand
    """

    AMEX = "amex"
    DINERS = "diners"
    DISCOVER = "discover"
    JCB = "jcb"
    MASTERCARD = "mastercard"
    UNIONPAY = "unionpay"
    VISA = "visa"
    UNKNOWN = "unknown"


class StripePaymentMethodBase(ComparableBase):
    """A Stripe Payment Method.

    The subset of fields from a Stripe Payment Method record needed for
    CTMS. See https://stripe.com/docs/api/payment_methods

    Relations:
    * An PaymentMethod has zero or one Customers. We don't track cards
      unassigned to customers.
    """

    stripe_id: Optional[str]
    stripe_created: Optional[datetime]
    payment_type: Optional[StripePaymentMethodTypeEnum]
    billing_address_country: Optional[str] = None
    card_brand: Optional[StripePaymentMethodCardBrandEnum] = None
    card_country: Optional[str] = None
    card_last4: Optional[str] = None

    class Config:
        fields = {
            "stripe_id": {
                "description": "Stripe Payment Method ID",
                "example": "pm_1JmPBfKb9q6OnNsLlzx8GamM",
            },
            "stripe_created": {
                "description": "Payment Method creation time in Stripe",
                "example": "2021-10-11T19:18:03.350435+00:00",
            },
            "payment_type": {
                "description": (
                    "The type of the PaymentMethod. If 'card', then card"
                    " data will be included."
                ),
                "example": "card",
            },
            "billing_address_country": {
                "description": (
                    "2-letter country code, but could be different if"
                    " created through alternate means."
                ),
                "example": "US",
            },
            "card_brand": {"description": "Card brand", "example": "visa"},
            "card_country": {
                "description": (
                    "Two-letter ISO code representing the country of the" " card."
                ),
                "example": "US",
            },
            "card_last4": {
                "description": "The last four digits of the card.",
                "example": "4242",
            },
        }


class StripePaymentMethodCreateSchema(StripePaymentMethodBase):
    stripe_id: str
    stripe_created: datetime
    payment_type: StripePaymentMethodTypeEnum


StripePaymentMethodUpsertSchema = StripePaymentMethodCreateSchema


class StripePaymentMethodOutputSchema(StripePaymentMethodUpsertSchema):
    create_timestamp: datetime
    update_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    class Config:
        orm_mode = True
        fields = {
            "create_timestamp": {
                "description": "CTMS Stripe PaymentMethod create timestamp.",
                "example": "2021-10-11T19:27:46.440Z",
            },
            "update_timestamp": {
                "description": "CTMS Stripe PaymentMethod update timestamp",
                "example": "2021-10-11T19:27:46.440Z",
            },
        }


class StripePaymentMethodModelSchema(StripePaymentMethodOutputSchema):
    stripe_customer_id = str

    class Config:
        extra = "forbid"
        fields = {
            "stripe_customer_id": {
                "description": "Stripe Customer ID",
                "example": "cus_8epDebVEl8Bs2V",
            },
        }
