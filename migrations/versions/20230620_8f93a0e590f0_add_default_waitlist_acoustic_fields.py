"""Add default Waitlist Acoustic fields

Revision ID: 8f93a0e590f0
Revises: a016433d3e8b
Create Date: 2023-06-20 11:41:55.215930

"""
# pylint: disable=no-member invalid-name
# no-member is triggered by alembic.op, which has dynamically added functions
# invalid-name is triggered by migration file names with a date prefix
# invalid-name is triggered by top-level alembic constants like revision instead of REVISION

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8f93a0e590f0"  # pragma: allowlist secret
down_revision = "a016433d3e8b"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
    INSERT INTO acoustic_field(tablename, field)
        VALUES
            ('waitlist', 'geo'),
            ('waitlist', 'platform')
        ON CONFLICT DO NOTHING
    """
    )


def downgrade():
    pass
