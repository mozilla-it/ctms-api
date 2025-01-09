"""Populate stripe_customer.fxa_id (was 47c59393f5d8)

Revision ID: ad4a8f10e344
Revises: 4eed7a83e324
Create Date: 2021-11-18 22:20:37.154955

"""

# pylint: disable=no-member invalid-name
# no-member is triggered by alembic.op, which has dynamically added functions
# invalid-name is triggered by migration file names with a date prefix
# invalid-name is triggered by top-level alembic constants like revision instead of REVISION

from alembic import op

# revision identifiers, used by Alembic.
revision = "ad4a8f10e344"  # pragma: allowlist secret
down_revision = "4eed7a83e324"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
    UPDATE stripe_customer
    SET fxa_id=(
       SELECT fxa_id FROM fxa WHERE fxa.email_id=stripe_customer.email_id
    )
    WHERE email_id IS NOT NULL
    """
    )
    op.execute("UPDATE stripe_customer SET email_id=NULL")


def downgrade():
    op.execute(
        """
    UPDATE stripe_customer
    SET email_id=(
       SELECT email_id FROM fxa WHERE fxa.fxa_id=stripe_customer.fxa_id
    )
    WHERE FXA_ID IS NOT NULL
    """
    )
    op.execute("UPDATE stripe_customer SET fxa_id=NULL")
