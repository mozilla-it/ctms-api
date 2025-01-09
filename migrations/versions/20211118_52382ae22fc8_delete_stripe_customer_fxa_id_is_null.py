"""Delete stripe_customer.fxa_id is NULL

Revision ID: 52382ae22fc8
Revises: ad4a8f10e344
Create Date: 2021-11-18 23:42:11.649087

"""

# pylint: disable=no-member invalid-name
# no-member is triggered by alembic.op, which has dynamically added functions
# invalid-name is triggered by migration file names with a date prefix
# invalid-name is triggered by top-level alembic constants like revision instead of REVISION

from alembic import op

# revision identifiers, used by Alembic.
revision = "52382ae22fc8"  # pragma: allowlist secret
down_revision = "ad4a8f10e344"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DELETE FROM stripe_customer WHERE stripe_customer.fxa_id IS NULL")


def downgrade():
    # Non-reversible migration
    pass
