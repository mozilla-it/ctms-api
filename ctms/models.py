from sqlalchemy import TIMESTAMP, Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .db import Base


class Email(Base):
    __tablename__ = "emails"

    email_id = Column(UUID(as_uuid=True), primary_key=True)
    primary_email = Column(String(255), unique=True, nullable=False)
    basket_token = Column(String(255), unique=True)
    fxa_id = Column(String(37), unique=True)
    first_name = Column(String(255))
    last_name = Column(String(255))
    mailing_country = Column(String(255))
    browser_locale = Column(String(5))
    mofo_relevant = Column(Boolean)
    signup_source = Column(Text)
    has_opted_out_of_email = Column(Boolean)
    subscriber = Column(Boolean)
    unengaged = Column(Boolean)
    unsubscribe_reason = Column(Text)

    # TODO: not null, default now(), update on update
    create_timestamp = Column(TIMESTAMP(timezone=True))
    update_timestamp = Column(TIMESTAMP(timezone=True))

    newsletters = relationship("Newsletter", back_populates="email")


class Newsletter(Base):
    __tablename__ = "newsletters"
    # TODO: There's still more in the schema to encode here

    id = Column(Integer, primary_key=True)
    email_id = Column(UUID(as_uuid=True), ForeignKey(Email.email_id))
    newsletter_name = Column(String(255), nullable=False)
    subscribed = Column(Boolean)

    email = relationship("Email", back_populates="newsletters")
