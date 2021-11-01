"""Add Stripe Subscription tables

Revision ID: 1b62022b71b2
Revises: a444065d1b11
Create Date: 2021-10-29 18:56:08.882997

"""
# pylint: disable=no-member invalid-name
# no-member is triggered by alembic.op, which has dynamically added functions
# invalid-name is triggered by migration file names with a date prefix
# invalid-name is triggered by top-level alembic constants like revision instead of REVISION

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1b62022b71b2"  # pragma: allowlist secret
down_revision = "a444065d1b11"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "stripe_price",
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
        sa.PrimaryKeyConstraint("stripe_id"),
    )
    op.create_table(
        "stripe_subscription",
        sa.Column("stripe_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=False),
        sa.Column("default_payment_method_id", sa.String(length=255), nullable=True),
        sa.Column("default_source_id", sa.String(length=255), nullable=True),
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
        sa.PrimaryKeyConstraint("stripe_id"),
    )
    op.create_table(
        "stripe_subscription_item",
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
        sa.PrimaryKeyConstraint("stripe_id"),
    )


def downgrade():
    op.drop_table("stripe_subscription_item")
    op.drop_table("stripe_subscription")
    op.drop_table("stripe_price")
