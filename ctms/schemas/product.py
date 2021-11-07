from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from .base import ComparableBase
from .stripe_price import StripeCurrencyType, StripePriceIntervalEnum
from .stripe_subscription import StripeSubscriptionStatusEnum


class ProductSegmentEnum(str, Enum):
    """Subscription segment, for targeting emails"""

    # On first subscription for product
    ACTIVE = "active"
    CANCELLING = "cancelling"
    CANCELED = "canceled"

    # On second or later subscription for product
    REACTIVE = "re-active"
    RECANCELLING = "re-cancelling"
    RECANCELED = "re-canceled"

    # Anything else
    OTHER = "other"


class ProductPaymentService(str, Enum):
    """Product payment service"""

    STRIPE = "stripe"
    UNKNOWN = "unknown"


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


class ProductBaseSchema(ComparableBase):
    """
    A product subscription, like Mozilla ISP through Stripe.
    """

    payment_service: Optional[ProductPaymentService]
    product_id: Optional[str]
    segment: Optional[ProductSegmentEnum]
    changed: Optional[datetime]
    sub_count: Optional[int]

    # From Stripe data
    product_name: Optional[str]
    price_id: Optional[str]
    payment_type: Optional[StripePaymentMethodTypeEnum]
    card_brand: Optional[StripePaymentMethodCardBrandEnum]
    card_last4: Optional[str]
    currency: Optional[StripeCurrencyType]
    amount: Optional[int]
    billing_country: Optional[str]
    status: Optional[StripeSubscriptionStatusEnum]
    interval_count: Optional[int]
    interval: Optional[StripePriceIntervalEnum]
    created: Optional[datetime]
    start: Optional[datetime]
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    canceled_at: Optional[datetime]
    cancel_at_period_end: Optional[bool]
    ended_at: Optional[datetime]

    class Config:
        fields = {
            "payment_service": {
                "description": "The service used to pay for the product.",
                "example": "stripe",
            },
            "product_id": {
                "description": "Service-specific Product ID",
                "example": "prod_cHJvZHVjdA",
            },
            "product_name": {
                "description": "Product name in English",
                "example": "Mozilla ISP",
            },
            "segment": {
                "description": "Subscription segment for targeting emails.",
                "example": "cancelling",
            },
            "changed": {
                "description": "When the targeting segment changed.",
                "example": "2021-10-14T18:33:09.348050+00:00",
            },
            "sub_count": {
                "description": "How many times the contact subscribed to this service",
                "example": 1,
            },
            "price_id": {
                "description": "Stripe Price ID",
                "example": "price_cHJpY2U",
            },
            "payment_type": {
                "description": "The type of the payment.",
                "example": "card",
            },
            "card_brand": {"description": "Card brand", "example": "visa"},
            "card_last4": {
                "description": "The last four digits of the card.",
                "example": "4242",
            },
            "currency": {
                "description": "Three-letter ISO currency code, in lowercase.",
                "example": "usd",
            },
            "amount": {
                "description": "How much the subscription plan costs.",
                "example": 999,
            },
            "billing_country": {
                "description": (
                    "2-letter country code, but could be different if"
                    " created through alternate means."
                ),
                "example": "US",
            },
            "status": {"description": "Subscription status", "example": "active"},
            "interval_count": {
                "description": (
                    "The number of intervals between subscription billings."
                ),
                "example": 1,
            },
            "interval": {
                "description": ("The frequency at which a subscription is billed."),
                "example": "month",
            },
            "created": {
                "description": "Subscription creation time.",
                "example": "2021-10-14T18:33:09.348050+00:00",
            },
            "start": {
                "description": "Date when the subscription was first created.",
                "example": "2021-10-14T18:33:09.348050+00:00",
            },
            "current_period_start": {
                "description": (
                    "Start of the current period that the subscription has been"
                    " invoiced for."
                ),
                "example": "2021-10-14T18:33:09.348050+00:00",
            },
            "current_period_end": {
                "description": (
                    "End of the current period that the subscription has been"
                    " invoiced for. At the end of this period, a new invoice will"
                    " be created."
                ),
                "example": "2021-10-14T18:33:09.348050+00:00",
            },
            "canceled_at": {
                "description": (
                    "If the subscription has been canceled, the date of that"
                    " cancellation."
                ),
                "example": "2021-10-14T18:33:09.348050+00:00",
            },
            "cancel_at_period_end": {
                "description": (
                    "True if the subscription will be canceled at the end of"
                    " the current period"
                ),
                "example": False,
            },
            "ended_at": {
                "description": (
                    "If the subscription has ended, the date the subscription" " ended."
                ),
                "example": "2021-10-14T18:33:09.348050+00:00",
            },
        }
