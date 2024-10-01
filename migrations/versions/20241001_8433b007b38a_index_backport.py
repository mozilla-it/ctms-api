"""Create index on lowercase primary emails

Revision ID: 8433b007b38a
Revises: 3689b813fe22
Create Date: 2024-10-01 18:46:43.405004

"""
# pylint: disable=no-member invalid-name
# no-member is triggered by alembic.op, which has dynamically added functions
# invalid-name is triggered by migration file names with a date prefix
# invalid-name is triggered by top-level alembic constants like revision instead of REVISION

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8433b007b38a"  # pragma: allowlist secret
down_revision = "3689b813fe22"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """CREATE UNIQUE INDEX IF NOT EXISTS idx_email_primary_unique_email_lower ON public.emails USING btree (lower((primary_email)::text));"""
    )


def downgrade():
    op.execute("""DROP INDEX IF EXISTS idx_email_primary_unique_email_lower;""")
