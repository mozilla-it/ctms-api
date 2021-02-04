from sqlalchemy import TIMESTAMP, Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .db import Base


class Email(Base):
    __tablename__ = "email"

    email_id = Column(String(36), primary_key=True)
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

    newsletters = relationship("Newsletter")


class Newsletter(Base):
    __tablename__ = "newsletter"
    # TODO: There's still more in the schema to encode here

    email = Column(String(36), ForeignKey("emails.email_id"))
    newsletter_name = Column(String(255), nullable=False)
    subscribed = Column(Boolean)

    email = relationship("Email")
