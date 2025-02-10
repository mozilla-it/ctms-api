from uuid import UUID as UUID4

from sqlalchemy import (
    JSON,
    TIMESTAMP,
    UUID,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import Comparator, hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import func


class Base(DeclarativeBase):
    pass


class CaseInsensitiveComparator(Comparator):
    def __eq__(self, other):
        return func.lower(self.__clause_element__()) == func.lower(other)


class TimestampMixin:
    @declared_attr
    def create_timestamp(cls):
        return mapped_column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=func.now(),
        )

    @declared_attr
    def update_timestamp(cls):
        return mapped_column(
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

    email_id = mapped_column(UUID, primary_key=True, server_default="uuid_generate_v4()")
    primary_email = mapped_column(String(255), unique=True, nullable=False)
    basket_token = mapped_column(String(255), unique=True)
    sfdc_id = mapped_column(String(255), index=True)
    first_name = mapped_column(String(255))
    last_name = mapped_column(String(255))
    mailing_country = mapped_column(String(255))
    email_format = mapped_column(String(1))
    email_lang = mapped_column(String(5))
    double_opt_in = mapped_column(Boolean)
    has_opted_out_of_email = mapped_column(Boolean)
    unsubscribe_reason = mapped_column(Text)

    newsletters = relationship("Newsletter", back_populates="email", order_by="Newsletter.name")
    waitlists = relationship("Waitlist", back_populates="email", order_by="Waitlist.name")
    fxa = relationship("FirefoxAccount", back_populates="email", uselist=False)
    amo = relationship("AmoAccount", back_populates="email", uselist=False)
    mofo = relationship("MozillaFoundationContact", back_populates="email", uselist=False)

    # Class Comparators
    @hybrid_property
    def primary_email_insensitive(self):
        return self.primary_email.lower()

    @primary_email_insensitive.comparator
    def primary_email_insensitive_comparator(cls):
        return CaseInsensitiveComparator(cls.primary_email)

    # Indexes
    __table_args__ = (
        Index("bulk_read_index", "update_timestamp", "email_id"),
        Index(
            "idx_email_primary_unique_email_lower",
            func.lower(primary_email),
            unique=True,
        ),
    )


class Newsletter(Base, TimestampMixin):
    __tablename__ = "newsletters"

    id = mapped_column(Integer, primary_key=True)
    email_id: Mapped[UUID4] = mapped_column(UUID(as_uuid=True), ForeignKey(Email.email_id), nullable=False)
    name = mapped_column(String(255), nullable=False)
    subscribed = mapped_column(Boolean)
    format = mapped_column(String(1))
    lang = mapped_column(String(5))
    source = mapped_column(Text)
    unsub_reason = mapped_column(Text)

    email = relationship("Email", back_populates="newsletters", uselist=False)

    __table_args__ = (UniqueConstraint("email_id", "name", name="uix_email_name"),)


class Waitlist(Base, TimestampMixin):
    __tablename__ = "waitlists"

    id = mapped_column(Integer, primary_key=True)
    email_id: Mapped[UUID4] = mapped_column(UUID(as_uuid=True), ForeignKey(Email.email_id), nullable=False)
    name = mapped_column(String(255), nullable=False)
    source = mapped_column(Text)
    subscribed = mapped_column(Boolean, nullable=False, default=True)
    unsub_reason = mapped_column(Text)
    fields = mapped_column(JSON, nullable=False, server_default="'{}'::json")

    email = relationship("Email", back_populates="waitlists", uselist=False)

    __table_args__ = (UniqueConstraint("email_id", "name", name="uix_wl_email_name"),)


class FirefoxAccount(Base, TimestampMixin):
    __tablename__ = "fxa"

    id = mapped_column(Integer, primary_key=True)
    fxa_id = mapped_column(String(255), unique=True)
    email_id = mapped_column(UUID(as_uuid=True), ForeignKey(Email.email_id), unique=True, nullable=False)
    primary_email = mapped_column(String(255), index=True)
    created_date = mapped_column(String(50))
    lang = mapped_column(String(255))
    first_service = mapped_column(String(50))
    account_deleted = mapped_column(Boolean)

    email = relationship("Email", back_populates="fxa", uselist=False)

    # Class Comparators
    @hybrid_property
    def fxa_primary_email_insensitive(self):
        return self.primary_email.lower()

    @fxa_primary_email_insensitive.comparator
    def fxa_primary_email_insensitive_comparator(
        cls,
    ):
        return CaseInsensitiveComparator(cls.primary_email)

    # Indexes
    __table_args__ = (Index("idx_fxa_primary_email_lower", func.lower(primary_email)),)


class AmoAccount(Base, TimestampMixin):
    __tablename__ = "amo"

    id = mapped_column(Integer, primary_key=True)
    email_id = mapped_column(UUID(as_uuid=True), ForeignKey(Email.email_id), unique=True, nullable=False)
    add_on_ids = mapped_column(String(500))
    display_name = mapped_column(String(255))
    email_opt_in = mapped_column(Boolean)
    language = mapped_column(String(5))
    last_login = mapped_column(Date)
    location = mapped_column(String(255))
    profile_url = mapped_column(String(40))
    user = mapped_column(Boolean)
    user_id = mapped_column(String(40), index=True)
    username = mapped_column(String(100))

    email = relationship("Email", back_populates="amo", uselist=False)


class ApiClient(Base, TimestampMixin):
    """An OAuth2 Client"""

    __tablename__ = "api_client"

    client_id = mapped_column(String(255), primary_key=True)
    email = mapped_column(String(255), nullable=False)
    enabled = mapped_column(Boolean, default=True)
    hashed_secret = mapped_column(String, nullable=False)
    last_access = mapped_column(DateTime(timezone=True))

    # Relationships
    roles = relationship("ApiClientRoles", back_populates="api_client", lazy="joined")


class MozillaFoundationContact(Base, TimestampMixin):
    __tablename__ = "mofo"

    id = mapped_column(Integer, primary_key=True)
    email_id = mapped_column(UUID(as_uuid=True), ForeignKey(Email.email_id), unique=True, nullable=False)
    mofo_email_id = mapped_column(String(255), unique=True)
    mofo_contact_id = mapped_column(String(255), index=True)
    mofo_relevant = mapped_column(Boolean)

    email = relationship("Email", back_populates="mofo", uselist=False)


# Permissions models.


class Roles(Base):
    __tablename__ = "roles"

    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String(255), nullable=False, unique=True)
    description = mapped_column(Text, nullable=True)

    # Relationships
    permissions = relationship("RolePermissions", back_populates="role", lazy="joined")
    api_clients = relationship("ApiClientRoles", back_populates="role", lazy="joined")


class Permissions(Base):
    __tablename__ = "permissions"

    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String(255), nullable=False, unique=True)
    description = mapped_column(Text, nullable=True)

    # Relationships
    roles = relationship("RolePermissions", back_populates="permission", lazy="joined")


class RolePermissions(Base):
    __tablename__ = "role_permissions"

    id = mapped_column(Integer, primary_key=True)
    role_id = mapped_column(ForeignKey(Roles.id, ondelete="CASCADE"), nullable=False)
    permission_id = mapped_column(ForeignKey(Permissions.id, ondelete="CASCADE"), nullable=False)

    # Relationships
    role = relationship("Roles", back_populates="permissions")
    permission = relationship("Permissions", back_populates="roles", lazy="joined")


class ApiClientRoles(Base):
    __tablename__ = "api_client_roles"

    id = mapped_column(Integer, primary_key=True)
    api_client_id = mapped_column(ForeignKey(ApiClient.client_id, ondelete="CASCADE"), nullable=False)
    role_id = mapped_column(ForeignKey(Roles.id, ondelete="CASCADE"), nullable=False)

    # Relationships
    api_client = relationship("ApiClient", back_populates="roles")
    role = relationship("Roles", back_populates="api_clients")
