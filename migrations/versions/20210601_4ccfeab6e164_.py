"""Add source to emails table

Revision ID: 4ccfeab6e164
Revises: 37edf9c48404
Create Date: 2021-06-01 14:43:42.123041

"""
# pylint: disable=no-member invalid-name
# no-member is triggered by alembic.op, which has dynamically added functions
# invalid-name is triggered by migration file names with a date prefix
# invalid-name is triggered by top-level alembic constants like revision instead of REVISION

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "4ccfeab6e164"  # pragma: allowlist secret
down_revision = "37edf9c48404"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("emails", sa.Column("source", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("emails", "source")
