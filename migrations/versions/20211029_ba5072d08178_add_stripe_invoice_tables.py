"""Add Stripe Invoice tables

Revision ID: ba5072d08178
Revises: 1b62022b71b2
Create Date: 2021-10-29 19:25:39.773144

"""

# pylint: disable=no-member invalid-name
# no-member is triggered by alembic.op, which has dynamically added functions
# invalid-name is triggered by migration file names with a date prefix
# invalid-name is triggered by top-level alembic constants like revision instead of REVISION

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ba5072d08178"  # pragma: allowlist secret
down_revision = "1b62022b71b2"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "stripe_invoice",
        sa.Column("stripe_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=False),
        sa.Column("default_payment_method_id", sa.String(length=255), nullable=True),
        sa.Column("default_source_id", sa.String(length=255), nullable=True),
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
        sa.PrimaryKeyConstraint("stripe_id"),
    )
    op.create_table(
        "stripe_invoice_line_item",
        sa.Column("stripe_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_invoice_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_type", sa.String(length=14), nullable=False),
        sa.Column("stripe_price_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_invoice_item_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_subscription_item_id", sa.String(length=255), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
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
        sa.PrimaryKeyConstraint("stripe_id"),
    )


def downgrade():
    op.drop_table("stripe_invoice_line_item")
    op.drop_table("stripe_invoice")
