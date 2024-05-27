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
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import Comparator, hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.sql.functions import func

from .database import Base


class CaseInsensitiveComparator(Comparator):  # pylint: disable=abstract-method
    def __eq__(self, other):
        return func.lower(self.__clause_element__()) == func.lower(other)


class TimestampMixin:
    @declared_attr
    def create_timestamp(cls):  # pylint: disable=no-self-argument
        return Column(
            TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
        )

    @declared_attr
    def update_timestamp(cls):  # pylint: disable=no-self-argument
        return Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=func.now(),
            # server_onupdate would be nice to use here, but it's not supported
            # by Postgres
            onupdate=func.now(),
        )


class Email(Base, TimestampMixin):
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


class Newsletter(Base, TimestampMixin):
    __tablename__ = "newsletters"

    id = Column(Integer, primary_key=True)
    email_id = Column(UUID(as_uuid=True), ForeignKey(Email.email_id), nullable=False)
    name = Column(String(255), nullable=False)
    subscribed = Column(Boolean)
    format = Column(String(1))
    lang = Column(String(5))
    source = Column(Text)
    unsub_reason = Column(Text)

    email = relationship("Email", back_populates="newsletters", uselist=False)

    __table_args__ = (UniqueConstraint("email_id", "name", name="uix_email_name"),)


class Waitlist(Base, TimestampMixin):
    __tablename__ = "waitlists"

    id = Column(Integer, primary_key=True)
    email_id = Column(UUID(as_uuid=True), ForeignKey(Email.email_id), nullable=False)
    name = Column(String(255), nullable=False)
    source = Column(Text)
    subscribed = Column(Boolean, nullable=False, default=True)
    unsub_reason = Column(Text)
    fields = Column(JSON, nullable=False, server_default="'{}'::json")

    email = relationship("Email", back_populates="waitlists", uselist=False)

    __table_args__ = (UniqueConstraint("email_id", "name", name="uix_wl_email_name"),)


class FirefoxAccount(Base, TimestampMixin):
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


class AmoAccount(Base, TimestampMixin):
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

    email = relationship("Email", back_populates="amo", uselist=False)


class ApiClient(Base, TimestampMixin):
    """An OAuth2 Client"""

    __tablename__ = "api_client"

    client_id = Column(String(255), primary_key=True)
    email = Column(String(255), nullable=False)
    enabled = Column(Boolean, default=True)
    hashed_secret = Column(String, nullable=False)
    last_access = Column(DateTime(timezone=True))


class MozillaFoundationContact(Base, TimestampMixin):
    __tablename__ = "mofo"

    id = Column(Integer, primary_key=True)
    email_id = Column(
        UUID(as_uuid=True), ForeignKey(Email.email_id), unique=True, nullable=False
    )
    mofo_email_id = Column(String(255), unique=True)
    mofo_contact_id = Column(String(255), index=True)
    mofo_relevant = Column(Boolean)

    email = relationship("Email", back_populates="mofo", uselist=False)
