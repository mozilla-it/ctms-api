from typing import Optional, cast
from uuid import UUID as PythonUUID

from sqlalchemy import (
    JSON,
    TIMESTAMP,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
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
    waitlists = relationship(
        "Waitlist", back_populates="email", order_by="Waitlist.name"
    )
    fxa = relationship("FirefoxAccount", back_populates="email", uselist=False)
    amo = relationship("AmoAccount", back_populates="email", uselist=False)
    mofo = relationship(
        "MozillaFoundationContact", back_populates="email", uselist=False
    )
    stripe_customer = relationship(
        "StripeCustomer",
        uselist=False,
        back_populates="email",
        primaryjoin="Email.email_id==FirefoxAccount.email_id",
        secondaryjoin="remote(FirefoxAccount.fxa_id)==foreign(StripeCustomer.fxa_id)",
        secondary="join(FirefoxAccount, StripeCustomer, FirefoxAccount.fxa_id == StripeCustomer.fxa_id)",
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


class Waitlist(Base):
    __tablename__ = "waitlists"

    id = Column(Integer, primary_key=True)
    email_id = Column(UUID(as_uuid=True), ForeignKey(Email.email_id), nullable=False)
    name = Column(String(255), nullable=False)
    source = Column(Text)
    fields = Column(JSON, nullable=False, server_default="'{}'::json")

    create_timestamp = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    update_timestamp = Column(
        DateTime(timezone=True), nullable=False, onupdate=func.now(), default=func.now()
    )

    email = relationship("Email", back_populates="waitlists", uselist=False)

    __table_args__ = (UniqueConstraint("email_id", "name", name="uix_wl_email_name"),)


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
    stripe_customer = relationship(
        "StripeCustomer",
        uselist=False,
        viewonly=True,
        primaryjoin=("foreign(FirefoxAccount.fxa_id)==remote(StripeCustomer.fxa_id)"),
    )

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


class AcousticField(Base):
    __tablename__ = "acoustic_field"

    tablename = Column(String, default="main")
    field = Column(String)

    __table_args__ = (
        PrimaryKeyConstraint("tablename", "field", name="pk_tablename_field"),
    )


class AcousticNewsletterMapping(Base):
    __tablename__ = "acoustic_newsletter_mapping"

    source = Column(String, primary_key=True)
    destination = Column(String)


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


class StripeBase(Base):
    """Base class for Stripe objects."""

    __abstract__ = True

    def get_email_id(self) -> Optional[PythonUUID]:
        """Return the email_id of the associated contact, if any."""
        raise NotImplementedError()


class StripeCustomer(StripeBase):
    __tablename__ = "stripe_customer"

    stripe_id = Column(String(255), nullable=False, primary_key=True)
    fxa_id = Column(String(255), nullable=False, unique=True, index=True)
    default_source_id = Column(String(255), nullable=True)
    invoice_settings_default_payment_method_id = Column(String(255), nullable=True)

    stripe_created = Column(DateTime(timezone=True), nullable=False)
    deleted = Column(Boolean, nullable=False, default=False)

    create_timestamp = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    update_timestamp = Column(
        DateTime(timezone=True), nullable=False, onupdate=func.now(), default=func.now()
    )

    email = relationship(
        "Email",
        uselist=False,
        back_populates="stripe_customer",
        primaryjoin="remote(FirefoxAccount.fxa_id)==foreign(StripeCustomer.fxa_id)",
        secondaryjoin="remote(Email.email_id)==foreign(FirefoxAccount.email_id)",
        secondary="join(FirefoxAccount, StripeCustomer, FirefoxAccount.fxa_id == StripeCustomer.fxa_id)",
    )
    fxa = relationship(
        "FirefoxAccount",
        uselist=False,
        viewonly=True,
        primaryjoin=("remote(FirefoxAccount.fxa_id)==foreign(StripeCustomer.fxa_id)"),
    )
    invoices = relationship(
        "StripeInvoice",
        uselist=True,
        viewonly=True,
        primaryjoin=(
            "foreign(StripeCustomer.stripe_id) =="
            " remote(StripeInvoice.stripe_customer_id)"
        ),
    )
    subscriptions = relationship(
        "StripeSubscription",
        back_populates="customer",
        uselist=True,
        primaryjoin=(
            "foreign(StripeCustomer.stripe_id) =="
            " remote(StripeSubscription.stripe_customer_id)"
        ),
    )

    def get_email_id(self) -> Optional[PythonUUID]:
        if self.fxa:
            return cast(PythonUUID, self.fxa.email.email_id)
        return None


class StripePrice(StripeBase):
    __tablename__ = "stripe_price"

    stripe_id = Column(String(255), nullable=False, primary_key=True)
    stripe_product_id = Column(String(255), nullable=False)

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

    invoice_line_items = relationship(
        "StripeInvoiceLineItem", back_populates="price", uselist=True
    )
    subscription_items = relationship(
        "StripeSubscriptionItem", back_populates="price", uselist=True
    )

    def get_email_id(self) -> None:
        """Prices can be related to multiple Customers, so return None."""
        return None


class StripeInvoice(StripeBase):
    __tablename__ = "stripe_invoice"

    stripe_id = Column(String(255), nullable=False, primary_key=True)
    stripe_customer_id = Column(String(255), nullable=False)
    default_payment_method_id = Column(String(255), nullable=True, default=None)
    default_source_id = Column(String(255), nullable=True, default=None)

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

    customer = relationship(
        "StripeCustomer",
        uselist=False,
        viewonly=True,
        primaryjoin=(
            " remote(StripeCustomer.stripe_id) =="
            "foreign(StripeInvoice.stripe_customer_id)"
        ),
    )
    line_items = relationship(
        "StripeInvoiceLineItem", back_populates="invoice", uselist=True
    )

    def get_email_id(self) -> Optional[PythonUUID]:
        if self.customer:
            return cast(PythonUUID, self.customer.get_email_id())
        return None


class StripeInvoiceLineItem(StripeBase):
    __tablename__ = "stripe_invoice_line_item"

    stripe_id = Column(String(255), nullable=False, primary_key=True)
    stripe_invoice_id = Column(
        String(255),
        ForeignKey("stripe_invoice.stripe_id"),
        nullable=False,
        index=True,
    )
    stripe_type = Column(String(14), nullable=False)
    stripe_price_id = Column(
        String(255),
        ForeignKey(StripePrice.stripe_id),
        nullable=False,
        index=True,
    )
    stripe_invoice_item_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    stripe_subscription_item_id = Column(String(255), nullable=True)
    amount = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False)

    create_timestamp = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=now()
    )
    update_timestamp = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=now(),
        server_onupdate=now(),
    )

    invoice = relationship("StripeInvoice", back_populates="line_items", uselist=False)
    price = relationship(
        "StripePrice", back_populates="invoice_line_items", uselist=False
    )
    subscription = relationship(
        "StripeSubscription",
        uselist=False,
        primaryjoin=(
            " remote(StripeSubscription.stripe_id) =="
            "foreign(StripeInvoiceLineItem.stripe_subscription_id)"
        ),
    )
    subscription_item = relationship(
        "StripeSubscriptionItem",
        uselist=False,
        primaryjoin=(
            " remote(StripeSubscriptionItem.stripe_id) =="
            "foreign(StripeInvoiceLineItem.stripe_subscription_item_id)"
        ),
    )

    def get_email_id(self) -> Optional[PythonUUID]:
        return cast(Optional[PythonUUID], self.invoice.get_email_id())


class StripeSubscription(StripeBase):
    __tablename__ = "stripe_subscription"

    stripe_id = Column(String(255), nullable=False, primary_key=True)
    stripe_customer_id = Column(String(255), nullable=False)
    default_payment_method_id = Column(String(255), nullable=True)
    default_source_id = Column(String(255), nullable=True)

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
        "StripeCustomer",
        uselist=False,
        primaryjoin=(
            " remote(StripeCustomer.stripe_id)=="
            "foreign(StripeSubscription.stripe_customer_id)"
        ),
    )
    subscription_items = relationship(
        "StripeSubscriptionItem", back_populates="subscription", uselist=True
    )

    def get_email_id(self) -> Optional[PythonUUID]:
        if self.customer:
            return cast(PythonUUID, self.customer.get_email_id())
        return None


class StripeSubscriptionItem(StripeBase):
    __tablename__ = "stripe_subscription_item"

    stripe_id = Column(String(255), nullable=False, primary_key=True)
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

    def get_email_id(self) -> Optional[PythonUUID]:
        return cast(Optional[PythonUUID], self.subscription.get_email_id())
