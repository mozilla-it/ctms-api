"""Add Stripe tables, part 2

Revision ID: f7316f16c53e
Revises: a236d9bd93fd
Create Date: 2021-10-21 17:53:33.972758

"""
# pylint: disable=no-member invalid-name
# no-member is triggered by alembic.op, which has dynamically added functions
# invalid-name is triggered by migration file names with a date prefix
# invalid-name is triggered by top-level alembic constants like revision instead of REVISION

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f7316f16c53e"  # pragma: allowlist secret
down_revision = "a236d9bd93fd"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    op.create_foreign_key(
        None,
        "stripe_customer",
        "stripe_payment_method",
        ["invoice_settings_default_payment_method"],
        ["stripe_id"],
    )


def downgrade():
    op.drop_constraint(None, "stripe_customer", type_="foreignkey")
