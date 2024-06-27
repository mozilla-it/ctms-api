"""Add FxA ID to Stripe Customer

Revision ID: 1ef38317ff85
Revises: ba5072d08178
Create Date: 2021-11-16 23:19:30.987274

"""

# pylint: disable=no-member invalid-name
# no-member is triggered by alembic.op, which has dynamically added functions
# invalid-name is triggered by migration file names with a date prefix
# invalid-name is triggered by top-level alembic constants like revision instead of REVISION

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "1ef38317ff85"  # pragma: allowlist secret
down_revision = "ba5072d08178"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "stripe_customer", sa.Column("fxa_id", sa.String(length=255), nullable=True)
    )
    op.create_index(
        op.f("ix_stripe_customer_fxa_id"), "stripe_customer", ["fxa_id"], unique=True
    )
    op.alter_column(
        "stripe_customer", "email_id", existing_type=postgresql.UUID(), nullable=True
    )


def downgrade():
    op.alter_column(
        "stripe_customer", "email_id", existing_type=postgresql.UUID(), nullable=False
    )
    op.drop_index(op.f("ix_stripe_customer_fxa_id"), table_name="stripe_customer")
    op.drop_column("stripe_customer", "fxa_id")
