from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql.functions import now

from .database import Base


class Email(Base):
    __tablename__ = "emails"
    __mapper_args__ = {"eager_defaults": True}

    email_id = Column(UUID(as_uuid=True), primary_key=True)
    primary_email = Column(String(255), unique=True, nullable=False)
    basket_token = Column(String(255), unique=True)
    sfdc_id = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    mailing_country = Column(String(255))
    email_format = Column(String(1))
    email_lang = Column(String(5))
    double_opt_in = Column(Boolean)
    has_opted_out_of_email = Column(Boolean)
    unsubscribe_reason = Column(Text)

    create_timestamp = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=now()
    )
    update_timestamp = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=now(),
        server_onupdate=now(),
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
        TIMESTAMP(timezone=True), nullable=False, server_default=now()
    )
    update_timestamp = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=now(),
        server_onupdate=now(),
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
    primary_email = Column(String(255))
    created_date = Column(String(50))
    lang = Column(String(255))
    first_service = Column(String(50))
    account_deleted = Column(Boolean)

    create_timestamp = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=now()
    )
    update_timestamp = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=now(),
        server_onupdate=now(),
    )

    email = relationship("Email", back_populates="fxa", uselist=False)


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
    location = Column(String(10))
    profile_url = Column(String(40))
    user = Column(Boolean)
    user_id = Column(String(40))
    username = Column(String(100))

    create_timestamp = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=now()
    )
    update_timestamp = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=now(),
        server_onupdate=now(),
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
        TIMESTAMP(timezone=True), nullable=False, server_default=now()
    )
    update_timestamp = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=now(),
        server_onupdate=now(),
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
    mofo_contact_id = Column(String(255))
    mofo_relevant = Column(Boolean)

    email = relationship("Email", back_populates="mofo", uselist=False)
