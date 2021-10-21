from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import Comparator, hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.sql.functions import func, now

from .database import Base


class CaseInsensitiveComparator(Comparator):  # pylint: disable=abstract-method
    def __eq__(self, other):
        return func.lower(self.__clause_element__()) == func.lower(other)


class Email(Base):
    __tablename__ = "emails"
    __mapper_args__ = {"eager_defaults": True}

    email_id = Column(UUID(as_uuid=True), primary_key=True)
    primary_email = Column(String(255), unique=True, nullable=False)
    basket_token = Column(String(255), unique=True)
    sfdc_id = Column(String(255), index=True)
    first_name = Column(String(255))
    last_name = Column(String(255))
    mailing_country = Column(String(255))
    email_format = Column(String(1))
    email_lang = Column(String(5))
    double_opt_in = Column(Boolean)
    has_opted_out_of_email = Column(Boolean)
    unsubscribe_reason = Column(Text)

    create_timestamp = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    update_timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        onupdate=func.now(),
        default=func.now(),
    )

    newsletters = relationship(
        "Newsletter", back_populates="email", order_by="Newsletter.name"
    )
    fxa = relationship("FirefoxAccount", back_populates="email", uselist=False)
    amo = relationship("AmoAccount", back_populates="email", uselist=False)
    vpn_waitlist = relationship("VpnWaitlist", back_populates="email", uselist=False)
    mofo = relationship(
        "MozillaFoundationContact", back_populates="email", uselist=False
    )
    stripe_customer = relationship(
        "StripeCustomer", back_populates="email", uselist=False
    )

    # Class Comparators
    @hybrid_property
    def primary_email_insensitive(self):
        return self.primary_email.lower()

    @primary_email_insensitive.comparator
    def primary_email_insensitive_comparator(cls):  # pylint: disable=no-self-argument
        return CaseInsensitiveComparator(cls.primary_email)

    # Indexes
    __table_args__ = (
        Index("bulk_read_index", "update_timestamp", "email_id"),
        Index("idx_email_primary_email_lower", func.lower(primary_email)),
    )


class Newsletter(Base):
    __tablename__ = "newsletters"

    id = Column(Integer, primary_key=True)
    email_id = Column(UUID(as_uuid=True), ForeignKey(Email.email_id), nullable=False)
    name = Column(String(255), nullable=False)
    subscribed = Column(Boolean)
    format = Column(String(1))
    lang = Column(String(5))
    source = Column(Text)
    unsub_reason = Column(Text)

    create_timestamp = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    update_timestamp = Column(
        DateTime(timezone=True), nullable=False, onupdate=func.now(), default=func.now()
    )

    email = relationship("Email", back_populates="newsletters", uselist=False)

    __table_args__ = (UniqueConstraint("email_id", "name", name="uix_email_name"),)


class FirefoxAccount(Base):
    __tablename__ = "fxa"

    id = Column(Integer, primary_key=True)
    fxa_id = Column(String(255), unique=True)
    email_id = Column(
        UUID(as_uuid=True), ForeignKey(Email.email_id), unique=True, nullable=False
    )
    primary_email = Column(String(255), index=True)
    created_date = Column(String(50))
    lang = Column(String(255))
    first_service = Column(String(50))
    account_deleted = Column(Boolean)

    create_timestamp = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    update_timestamp = Column(
        DateTime(timezone=True), nullable=False, onupdate=func.now(), default=func.now()
    )

    email = relationship("Email", back_populates="fxa", uselist=False)

    # Class Comparators
    @hybrid_property
    def fxa_primary_email_insensitive(self):
        return self.primary_email.lower()

    @fxa_primary_email_insensitive.comparator
    def fxa_primary_email_insensitive_comparator(
        cls,
    ):  # pylint: disable=no-self-argument
        return CaseInsensitiveComparator(cls.primary_email)

    # Indexes
    __table_args__ = (Index("idx_fxa_primary_email_lower", func.lower(primary_email)),)


class AmoAccount(Base):
    __tablename__ = "amo"

    id = Column(Integer, primary_key=True)
    email_id = Column(
        UUID(as_uuid=True), ForeignKey(Email.email_id), unique=True, nullable=False
    )
    add_on_ids = Column(String(500))
    display_name = Column(String(255))
    email_opt_in = Column(Boolean)
    language = Column(String(5))
    last_login = Column(Date)
    location = Column(String(255))
    profile_url = Column(String(40))
    user = Column(Boolean)
    user_id = Column(String(40), index=True)
    username = Column(String(100))

    create_timestamp = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    update_timestamp = Column(
        DateTime(timezone=True), nullable=False, onupdate=func.now(), default=func.now()
    )

    email = relationship("Email", back_populates="amo", uselist=False)


class VpnWaitlist(Base):
    __tablename__ = "vpn_waitlist"

    id = Column(Integer, primary_key=True)
    email_id = Column(
        UUID(as_uuid=True), ForeignKey(Email.email_id), unique=True, nullable=False
    )
    geo = Column(String(100))
    platform = Column(String(100))

    create_timestamp = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    update_timestamp = Column(
        DateTime(timezone=True), nullable=False, onupdate=func.now(), default=func.now()
    )

    email = relationship("Email", back_populates="vpn_waitlist", uselist=False)


class ApiClient(Base):
    """An OAuth2 Client"""

    __tablename__ = "api_client"

    client_id = Column(String(255), primary_key=True)
    email = Column(String(255), nullable=False)
    enabled = Column(Boolean, default=True)
    hashed_secret = Column(String, nullable=False)

    create_timestamp = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=now()
    )
    update_timestamp = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=now(),
        server_onupdate=now(),
    )


class MozillaFoundationContact(Base):
    __tablename__ = "mofo"

    id = Column(Integer, primary_key=True)
    email_id = Column(
        UUID(as_uuid=True), ForeignKey(Email.email_id), unique=True, nullable=False
    )
    mofo_email_id = Column(String(255), unique=True)
    mofo_contact_id = Column(String(255), index=True)
    mofo_relevant = Column(Boolean)

    email = relationship("Email", back_populates="mofo", uselist=False)


class PendingAcousticRecord(Base):
    __tablename__ = "pending_acoustic"

    id = Column(Integer, primary_key=True)
    email_id = Column(UUID(as_uuid=True), ForeignKey(Email.email_id), nullable=False)
    retry = Column(Integer, nullable=False, default=0)
    create_timestamp = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    update_timestamp = Column(
        DateTime(timezone=True), nullable=False, onupdate=func.now(), default=func.now()
    )

    email = relationship("Email", uselist=False)


class StripeCustomer(Base):
    __tablename__ = "stripe_customer"

    id = Column(Integer, primary_key=True)
    email_id = Column(UUID(as_uuid=True), ForeignKey(Email.email_id), nullable=False)
    stripe_id = Column(String(255), nullable=False, unique=True, index=True)
    invoice_settings_default_payment_method = Column(
        String(255),
        ForeignKey("stripe_payment_method.stripe_id"),
        nullable=True,
    )

    stripe_created = Column(DateTime(timezone=True), nullable=False)
    deleted = Column(Boolean, nullable=False, default=False)

    create_timestamp = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    update_timestamp = Column(
        DateTime(timezone=True), nullable=False, onupdate=func.now(), default=func.now()
    )

    email = relationship("Email", uselist=False)
    payment_methods = relationship(
        "StripePaymentMethod",
        back_populates="customer",
        uselist=True,
        primaryjoin="StripeCustomer.stripe_id==StripePaymentMethod.stripe_customer_id",
    )
    invoices = relationship("StripeInvoice", back_populates="customer", uselist=True)
    subscriptions = relationship(
        "StripeSubscription", back_populates="customer", uselist=True
    )


class StripeProduct(Base):
    __tablename__ = "stripe_product"

    id = Column(Integer, primary_key=True)
    stripe_id = Column(String(255), nullable=False, unique=True, index=True)

    stripe_created = Column(DateTime(timezone=True), nullable=False)
    stripe_updated = Column(DateTime(timezone=True), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    name = Column(String(255), nullable=False)

    create_timestamp = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=now()
    )
    update_timestamp = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=now(),
        server_onupdate=now(),
    )

    prices = relationship("StripePrice", back_populates="product", uselist=True)


class StripePrice(Base):
    __tablename__ = "stripe_price"

    id = Column(Integer, primary_key=True)
    stripe_id = Column(String(255), nullable=False, unique=True, index=True)
    stripe_product_id = Column(
        String(255),
        ForeignKey(StripeProduct.stripe_id),
        nullable=False,
    )

    stripe_created = Column(DateTime(timezone=True), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    currency = Column(String(3), nullable=False)
    recurring_interval = Column(String(5), nullable=True)
    recurring_interval_count = Column(Integer, nullable=True)
    unit_amount = Column(Integer, nullable=True)

    create_timestamp = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=now()
    )
    update_timestamp = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=now(),
        server_onupdate=now(),
    )

    product = relationship("StripeProduct", back_populates="prices", uselist=False)
    invoice_items = relationship(
        "StripeInvoiceItem", back_populates="price", uselist=True
    )
    subscription_items = relationship(
        "StripeSubscriptionItem", back_populates="price", uselist=True
    )


class StripePaymentMethod(Base):
    __tablename__ = "stripe_payment_method"

    id = Column(Integer, primary_key=True)
    stripe_id = Column(String(255), nullable=False, unique=True, index=True)
    stripe_customer_id = Column(
        String(255), ForeignKey(StripeCustomer.stripe_id), nullable=False
    )

    stripe_created = Column(DateTime(timezone=True), nullable=False)
    payment_type = Column(String(20), nullable=False)
    billing_address_country = Column(String(20), nullable=True)
    card_brand = Column(String(12), nullable=True)
    card_country = Column(String(2), nullable=True)
    card_last4 = Column(String(4), nullable=True)

    create_timestamp = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=now()
    )
    update_timestamp = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=now(),
        server_onupdate=now(),
    )

    customer = relationship(
        "StripeCustomer",
        foreign_keys=[stripe_customer_id],
        back_populates="payment_methods",
        uselist=False,
    )
    invoices = relationship(
        "StripeInvoice", back_populates="payment_method", uselist=True
    )
    subscriptions = relationship(
        "StripeSubscription", back_populates="payment_method", uselist=True
    )


class StripeInvoiceItem(Base):
    __tablename__ = "stripe_invoice_item"

    id = Column(Integer, primary_key=True)
    stripe_id = Column(String(255), nullable=False, unique=True, index=True)
    stripe_invoice_id = Column(
        String(255),
        ForeignKey("stripe_invoice.stripe_id"),
        nullable=False,
    )
    stripe_price_id = Column(
        String(255),
        ForeignKey(StripePrice.stripe_id),
        nullable=False,
    )

    stripe_created = Column(DateTime(timezone=True), nullable=False)

    create_timestamp = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=now()
    )
    update_timestamp = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=now(),
        server_onupdate=now(),
    )

    invoice = relationship(
        "StripeInvoice", back_populates="invoice_items", uselist=False
    )
    price = relationship("StripePrice", back_populates="invoice_items", uselist=False)


class StripeInvoice(Base):
    __tablename__ = "stripe_invoice"

    id = Column(Integer, primary_key=True)
    stripe_id = Column(String(255), nullable=False, unique=True, index=True)
    stripe_customer_id = Column(
        String(255), ForeignKey(StripeCustomer.stripe_id), nullable=False
    )
    default_payment_method = Column(
        String(255),
        ForeignKey(StripePaymentMethod.stripe_id),
        nullable=True,
        default=None,
    )

    stripe_created = Column(DateTime(timezone=True), nullable=False)
    currency = Column(String(3), nullable=False)
    total = Column(Integer, nullable=False)
    status = Column(String(15), nullable=False)

    create_timestamp = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=now()
    )
    update_timestamp = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=now(),
        server_onupdate=now(),
    )

    customer = relationship("StripeCustomer", back_populates="invoices", uselist=False)
    payment_method = relationship(
        "StripePaymentMethod", back_populates="invoices", uselist=False
    )
    invoice_items = relationship(
        "StripeInvoiceItem", back_populates="invoice", uselist=True
    )


class StripeSubscription(Base):
    __tablename__ = "stripe_subscription"

    id = Column(Integer, primary_key=True)
    stripe_id = Column(String(255), nullable=False, unique=True, index=True)
    stripe_customer_id = Column(
        String(255),
        ForeignKey(StripeCustomer.stripe_id),
        nullable=False,
    )
    default_payment_method = Column(
        String(255),
        ForeignKey(StripePaymentMethod.stripe_id),
        nullable=True,
    )

    stripe_created = Column(DateTime(timezone=True), nullable=False)
    cancel_at_period_end = Column(Boolean, nullable=False)
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=False)
    current_period_start = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), nullable=False)

    create_timestamp = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=now()
    )
    update_timestamp = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=now(),
        server_onupdate=now(),
    )

    customer = relationship(
        "StripeCustomer", back_populates="subscriptions", uselist=False
    )
    payment_method = relationship(
        "StripePaymentMethod", back_populates="subscriptions", uselist=False
    )
    subscription_items = relationship(
        "StripeSubscriptionItem", back_populates="subscription", uselist=True
    )


class StripeSubscriptionItem(Base):
    __tablename__ = "stripe_subscription_item"

    id = Column(Integer, primary_key=True)
    stripe_id = Column(String(255), nullable=False, unique=True, index=True)
    stripe_subscription_id = Column(
        String(255),
        ForeignKey(StripeSubscription.stripe_id),
        nullable=False,
    )
    stripe_price_id = Column(
        String(255),
        ForeignKey(StripePrice.stripe_id),
        nullable=False,
    )

    stripe_created = Column(DateTime(timezone=True), nullable=False)

    create_timestamp = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=now()
    )
    update_timestamp = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=now(),
        server_onupdate=now(),
    )

    subscription = relationship(
        "StripeSubscription", back_populates="subscription_items", uselist=False
    )
    price = relationship(
        "StripePrice", back_populates="subscription_items", uselist=False
    )
