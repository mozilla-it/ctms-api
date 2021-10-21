"""Add Stripe tables, part 1

Revision ID: a236d9bd93fd
Revises: 37edf9c48404
Create Date: 2021-10-21 17:46:41.992888

"""
# pylint: disable=no-member invalid-name
# no-member is triggered by alembic.op, which has dynamically added functions
# invalid-name is triggered by migration file names with a date prefix
# invalid-name is triggered by top-level alembic constants like revision instead of REVISION

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "a236d9bd93fd"  # pragma: allowlist secret
down_revision = "37edf9c48404"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "stripe_product",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stripe_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stripe_updated", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "create_timestamp",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "update_timestamp",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_stripe_product_stripe_id"),
        "stripe_product",
        ["stripe_id"],
        unique=True,
    )
    op.create_table(
        "stripe_customer",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stripe_id", sa.String(length=255), nullable=False),
        sa.Column(
            "invoice_settings_default_payment_method",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column("stripe_created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.Column(
            "create_timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("update_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["email_id"],
            ["emails.email_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_stripe_customer_stripe_id"),
        "stripe_customer",
        ["stripe_id"],
        unique=True,
    )
    op.create_table(
        "stripe_price",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stripe_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_product_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("recurring_interval", sa.String(length=5), nullable=True),
        sa.Column("recurring_interval_count", sa.Integer(), nullable=True),
        sa.Column("unit_amount", sa.Integer(), nullable=True),
        sa.Column(
            "create_timestamp",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "update_timestamp",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["stripe_product_id"],
            ["stripe_product.stripe_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_stripe_price_stripe_id"), "stripe_price", ["stripe_id"], unique=True
    )
    op.create_table(
        "stripe_payment_method",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stripe_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payment_type", sa.String(length=20), nullable=False),
        sa.Column("billing_address_country", sa.String(length=20), nullable=True),
        sa.Column("card_brand", sa.String(length=12), nullable=True),
        sa.Column("card_country", sa.String(length=2), nullable=True),
        sa.Column("card_last4", sa.String(length=4), nullable=True),
        sa.Column(
            "create_timestamp",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "update_timestamp",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["stripe_customer_id"],
            ["stripe_customer.stripe_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_stripe_payment_method_stripe_id"),
        "stripe_payment_method",
        ["stripe_id"],
        unique=True,
    )
    op.create_table(
        "stripe_invoice",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stripe_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=False),
        sa.Column("default_payment_method", sa.String(length=255), nullable=True),
        sa.Column("stripe_created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=15), nullable=False),
        sa.Column(
            "create_timestamp",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "update_timestamp",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["default_payment_method"],
            ["stripe_payment_method.stripe_id"],
        ),
        sa.ForeignKeyConstraint(
            ["stripe_customer_id"],
            ["stripe_customer.stripe_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_stripe_invoice_stripe_id"),
        "stripe_invoice",
        ["stripe_id"],
        unique=True,
    )
    op.create_table(
        "stripe_subscription",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stripe_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=False),
        sa.Column("default_payment_method", sa.String(length=255), nullable=True),
        sa.Column("stripe_created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "create_timestamp",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "update_timestamp",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["default_payment_method"],
            ["stripe_payment_method.stripe_id"],
        ),
        sa.ForeignKeyConstraint(
            ["stripe_customer_id"],
            ["stripe_customer.stripe_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_stripe_subscription_stripe_id"),
        "stripe_subscription",
        ["stripe_id"],
        unique=True,
    )
    op.create_table(
        "stripe_invoice_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stripe_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_invoice_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_price_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_created", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "create_timestamp",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "update_timestamp",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["stripe_invoice_id"],
            ["stripe_invoice.stripe_id"],
        ),
        sa.ForeignKeyConstraint(
            ["stripe_price_id"],
            ["stripe_price.stripe_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_stripe_invoice_item_stripe_id"),
        "stripe_invoice_item",
        ["stripe_id"],
        unique=True,
    )
    op.create_table(
        "stripe_subscription_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stripe_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_price_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_created", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "create_timestamp",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "update_timestamp",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["stripe_price_id"],
            ["stripe_price.stripe_id"],
        ),
        sa.ForeignKeyConstraint(
            ["stripe_subscription_id"],
            ["stripe_subscription.stripe_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_stripe_subscription_item_stripe_id"),
        "stripe_subscription_item",
        ["stripe_id"],
        unique=True,
    )


def downgrade():
    op.drop_index(
        op.f("ix_stripe_subscription_item_stripe_id"),
        table_name="stripe_subscription_item",
    )
    op.drop_table("stripe_subscription_item")
    op.drop_index(
        op.f("ix_stripe_invoice_item_stripe_id"), table_name="stripe_invoice_item"
    )
    op.drop_table("stripe_invoice_item")
    op.drop_index(
        op.f("ix_stripe_subscription_stripe_id"), table_name="stripe_subscription"
    )
    op.drop_table("stripe_subscription")
    op.drop_index(op.f("ix_stripe_invoice_stripe_id"), table_name="stripe_invoice")
    op.drop_table("stripe_invoice")
    op.drop_index(
        op.f("ix_stripe_payment_method_stripe_id"), table_name="stripe_payment_method"
    )
    op.drop_table("stripe_payment_method")
    op.drop_index(op.f("ix_stripe_price_stripe_id"), table_name="stripe_price")
    op.drop_table("stripe_price")
    op.drop_index(op.f("ix_stripe_customer_stripe_id"), table_name="stripe_customer")
    op.drop_table("stripe_customer")
    op.drop_index(op.f("ix_stripe_product_stripe_id"), table_name="stripe_product")
    op.drop_table("stripe_product")
