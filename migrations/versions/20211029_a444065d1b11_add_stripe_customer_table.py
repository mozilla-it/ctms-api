"""Add Stripe Customer table

Revision ID: a444065d1b11
Revises: 37edf9c48404
Create Date: 2021-10-29 18:25:05.629813

"""

# pylint: disable=no-member invalid-name
# no-member is triggered by alembic.op, which has dynamically added functions
# invalid-name is triggered by migration file names with a date prefix
# invalid-name is triggered by top-level alembic constants like revision instead of REVISION

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "a444065d1b11"  # pragma: allowlist secret
down_revision = "37edf9c48404"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "stripe_customer",
        sa.Column("email_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stripe_id", sa.String(length=255), nullable=False),
        sa.Column("default_source_id", sa.String(length=255), nullable=True),
        sa.Column(
            "invoice_settings_default_payment_method_id",
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
        sa.PrimaryKeyConstraint("stripe_id"),
    )


def downgrade():
    op.drop_table("stripe_customer")
