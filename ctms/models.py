from sqlalchemy import TIMESTAMP, Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


class Email(Base):
    __tablename__ = "emails"

    email_id = Column(UUID(as_uuid=True), primary_key=True)
    primary_email = Column(String(255), unique=True, nullable=False)
    basket_token = Column(String(255), unique=True)
    sfdc_id = Column(String(255))
    mofo_id = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    mailing_country = Column(String(255))
    email_format = Column(String(1))
    email_lang = Column(String(5))
    mofo_relevant = Column(Boolean)
    has_opted_out_of_email = Column(Boolean)
    unsubscribe_reason = Column(Text)

    # TODO: not null, default now(), update on update
    create_timestamp = Column(TIMESTAMP(timezone=True))
    update_timestamp = Column(TIMESTAMP(timezone=True))

    newsletters = relationship("Newsletter", back_populates="email")
    fxa = relationship("FirefoxAccount", back_populates="email")
    amo = relationship("AmoAccount", back_populates="email")
    vpn_waitlist = relationship("VpnWaitlist", back_populates="email")


class Newsletter(Base):
    __tablename__ = "newsletters"

    id = Column(Integer, primary_key=True)
    email_id = Column(UUID(as_uuid=True), ForeignKey(Email.email_id))
    name = Column(String(255), nullable=False)
    subscribed = Column(Boolean)
    format = Column(String(1))
    lang = Column(String(5))
    source = Column(Text)
    unsub_reason = Column(Text)

    # TODO: not null, default now(), update on update
    create_timestamp = Column(TIMESTAMP(timezone=True))
    update_timestamp = Column(TIMESTAMP(timezone=True))

    email = relationship("Email", back_populates="newsletters")


class FirefoxAccount(Base):
    __tablename__ = "fxa"

    id = Column(Integer, primary_key=True)
    fxa_id = Column(String(255), unique=True)
    email_id = Column(UUID(as_uuid=True), ForeignKey(Email.email_id))
    primary_email = Column(String(255))
    created_date = Column(String(50))
    lang = Column(String(10))
    first_service = Column(String(50))
    account_deleted = Column(Boolean)

    # TODO: not null, default now(), update on update
    create_timestamp = Column(TIMESTAMP(timezone=True))
    update_timestamp = Column(TIMESTAMP(timezone=True))

    email = relationship("Email", back_populates="fxa")


class AmoAccount(Base):
    __tablename__ = "amo"

    id = Column(Integer, primary_key=True)
    email_id = Column(UUID(as_uuid=True), ForeignKey(Email.email_id))
    add_on_ids = Column(String(500))
    display_name = Column(String(255))
    email_opt_in = Column(Boolean)
    language = Column(String(5))
    last_login = Column(String(40))
    location = Column(String(10))
    profile_url = Column(String(40))
    user = Column(Boolean)
    user_id = Column(String(40))
    username = Column(String(100))

    # TODO: not null, default now(), update on update
    create_timestamp = Column(TIMESTAMP(timezone=True))
    update_timestamp = Column(TIMESTAMP(timezone=True))

    email = relationship("Email", back_populates="amo")


class VpnWaitlist(Base):
    __tablename__ = "vpn_waitlist"

    id = Column(Integer, primary_key=True)
    email_id = Column(UUID(as_uuid=True), ForeignKey(Email.email_id))
    geo = Column(String(100))
    platform = Column(String(100))

    # TODO: not null, default now(), update on update
    create_timestamp = Column(TIMESTAMP(timezone=True))
    update_timestamp = Column(TIMESTAMP(timezone=True))

    email = relationship("Email", back_populates="vpn_waitlist")
