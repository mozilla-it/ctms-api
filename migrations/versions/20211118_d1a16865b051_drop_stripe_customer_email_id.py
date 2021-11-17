"""Drop stripe_customer.email_id

Revision ID: d1a16865b051
Revises: 52382ae22fc8
Create Date: 2021-11-18 23:44:58.435343

"""
# pylint: disable=no-member invalid-name
# no-member is triggered by alembic.op, which has dynamically added functions
# invalid-name is triggered by migration file names with a date prefix
# invalid-name is triggered by top-level alembic constants like revision instead of REVISION

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "d1a16865b051"  # pragma: allowlist secret
down_revision = "52382ae22fc8"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "stripe_customer",
        "fxa_id",
        existing_type=sa.VARCHAR(length=255),
        nullable=False,
    )
    op.drop_constraint(
        "stripe_customer_email_id_fkey", "stripe_customer", type_="foreignkey"
    )
    op.drop_column("stripe_customer", "email_id")


def downgrade():
    op.add_column(
        "stripe_customer",
        sa.Column("email_id", postgresql.UUID(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(
        "stripe_customer_email_id_fkey",
        "stripe_customer",
        "emails",
        ["email_id"],
        ["email_id"],
    )
    op.alter_column(
        "stripe_customer", "fxa_id", existing_type=sa.VARCHAR(length=255), nullable=True
    )
