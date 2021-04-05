"""update fields from sample data learnings

Revision ID: 8019ffa1614e
Revises: 2bc6c4d12e2e
Create Date: 2021-03-30 15:40:21.231088

"""
# pylint: disable=no-member invalid-name
# no-member is triggered by alembic.op, which has dynamically added functions
# invalid-name is triggered by migration file names with a date prefix
# invalid-name is triggered by top-level alembic constants like revision instead of REVISION

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8019ffa1614e"  # pragma: allowlist secret
down_revision = "2bc6c4d12e2e"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "amo",
        "location",
        existing_type=sa.VARCHAR(length=10),
        type_=sa.String(length=255),
        existing_nullable=True,
    )


def downgrade():
    op.alter_column(
        "amo",
        "location",
        existing_type=sa.String(length=255),
        type_=sa.VARCHAR(length=10),
        existing_nullable=True,
    )
