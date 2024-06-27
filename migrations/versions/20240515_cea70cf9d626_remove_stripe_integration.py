"""Remove stripe integration

Revision ID: cea70cf9d626
Revises: 432e8585fe17
Create Date: 2024-05-15 23:12:34.649746

"""

# pylint: disable=no-member invalid-name
# no-member is triggered by alembic.op, which has dynamically added functions
# invalid-name is triggered by migration file names with a date prefix
# invalid-name is triggered by top-level alembic constants like revision instead of REVISION

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "cea70cf9d626"  # pragma: allowlist secret
down_revision = "432e8585fe17"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index("ix_stripe_customer_fxa_id", table_name="stripe_customer")
    op.drop_index(
        "ix_stripe_invoice_line_item_stripe_invoice_id",
        table_name="stripe_invoice_line_item",
    )
    op.drop_index(
        "ix_stripe_invoice_line_item_stripe_price_id",
        table_name="stripe_invoice_line_item",
    )
    op.drop_table("stripe_subscription_item")
    op.drop_table("stripe_subscription")
    op.drop_table("stripe_invoice_line_item")
    op.drop_table("stripe_invoice")
    op.drop_table("stripe_price")
    op.drop_table("stripe_customer")


def downgrade():
    op.create_table(
        "stripe_price",
        sa.Column(
            "stripe_id", sa.VARCHAR(length=255), autoincrement=False, nullable=False
        ),
        sa.Column(
            "stripe_product_id",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "stripe_created",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("active", sa.BOOLEAN(), autoincrement=False, nullable=False),
        sa.Column(
            "currency", sa.VARCHAR(length=3), autoincrement=False, nullable=False
        ),
        sa.Column(
            "recurring_interval",
            sa.VARCHAR(length=5),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "recurring_interval_count", sa.INTEGER(), autoincrement=False, nullable=True
        ),
        sa.Column("unit_amount", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column(
            "create_timestamp",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "update_timestamp",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("stripe_id", name="stripe_price_pkey"),
    )
    op.create_table(
        "stripe_invoice",
        sa.Column(
            "stripe_id", sa.VARCHAR(length=255), autoincrement=False, nullable=False
        ),
        sa.Column(
            "stripe_customer_id",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "default_payment_method_id",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "default_source_id",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "stripe_created",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "currency", sa.VARCHAR(length=3), autoincrement=False, nullable=False
        ),
        sa.Column("total", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("status", sa.VARCHAR(length=15), autoincrement=False, nullable=False),
        sa.Column(
            "create_timestamp",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "update_timestamp",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("stripe_id", name="stripe_invoice_pkey"),
    )
    op.create_table(
        "stripe_invoice_line_item",
        sa.Column(
            "stripe_id", sa.VARCHAR(length=255), autoincrement=False, nullable=False
        ),
        sa.Column(
            "stripe_invoice_id",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "stripe_type", sa.VARCHAR(length=14), autoincrement=False, nullable=False
        ),
        sa.Column(
            "stripe_price_id",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "stripe_invoice_item_id",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "stripe_subscription_id",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "stripe_subscription_item_id",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("amount", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            "currency", sa.VARCHAR(length=3), autoincrement=False, nullable=False
        ),
        sa.Column(
            "create_timestamp",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "update_timestamp",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["stripe_invoice_id"],
            ["stripe_invoice.stripe_id"],
            name="stripe_invoice_line_item_stripe_invoice_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["stripe_price_id"],
            ["stripe_price.stripe_id"],
            name="stripe_invoice_line_item_stripe_price_id_fkey",
        ),
        sa.PrimaryKeyConstraint("stripe_id", name="stripe_invoice_line_item_pkey"),
    )
    op.create_table(
        "stripe_subscription",
        sa.Column(
            "stripe_id", sa.VARCHAR(length=255), autoincrement=False, nullable=False
        ),
        sa.Column(
            "stripe_customer_id",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "default_payment_method_id",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "default_source_id",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "stripe_created",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "cancel_at_period_end", sa.BOOLEAN(), autoincrement=False, nullable=False
        ),
        sa.Column(
            "canceled_at",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "current_period_end",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "current_period_start",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "ended_at",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "start_date",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("status", sa.VARCHAR(length=20), autoincrement=False, nullable=False),
        sa.Column(
            "create_timestamp",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "update_timestamp",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("stripe_id", name="stripe_subscription_pkey"),
    )
    op.create_table(
        "stripe_subscription_item",
        sa.Column(
            "stripe_id", sa.VARCHAR(length=255), autoincrement=False, nullable=False
        ),
        sa.Column(
            "stripe_subscription_id",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "stripe_price_id",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "stripe_created",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "create_timestamp",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "update_timestamp",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["stripe_price_id"],
            ["stripe_price.stripe_id"],
            name="stripe_subscription_item_stripe_price_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["stripe_subscription_id"],
            ["stripe_subscription.stripe_id"],
            name="stripe_subscription_item_stripe_subscription_id_fkey",
        ),
        sa.PrimaryKeyConstraint("stripe_id", name="stripe_subscription_item_pkey"),
    )
    op.create_table(
        "stripe_customer",
        sa.Column(
            "stripe_id", sa.VARCHAR(length=255), autoincrement=False, nullable=False
        ),
        sa.Column(
            "default_source_id",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "invoice_settings_default_payment_method_id",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "stripe_created",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("deleted", sa.BOOLEAN(), autoincrement=False, nullable=False),
        sa.Column(
            "create_timestamp",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "update_timestamp",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "fxa_id", sa.VARCHAR(length=255), autoincrement=False, nullable=False
        ),
        sa.PrimaryKeyConstraint("stripe_id", name="stripe_customer_pkey"),
    )
    op.create_index(
        "ix_stripe_customer_fxa_id", "stripe_customer", ["fxa_id"], unique=False
    )
    op.create_index(
        "ix_stripe_invoice_line_item_stripe_price_id",
        "stripe_invoice_line_item",
        ["stripe_price_id"],
        unique=False,
    )
    op.create_index(
        "ix_stripe_invoice_line_item_stripe_invoice_id",
        "stripe_invoice_line_item",
        ["stripe_invoice_id"],
        unique=False,
    )
    # ### end Alembic commands ###
