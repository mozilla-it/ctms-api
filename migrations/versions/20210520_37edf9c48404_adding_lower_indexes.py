"""Adding lower-indexes

Revision ID: 37edf9c48404
Revises: cad3c933830b
Create Date: 2021-05-20 00:28:25.950122

"""
# pylint: disable=no-member invalid-name
# no-member is triggered by alembic.op, which has dynamically added functions
# invalid-name is triggered by migration file names with a date prefix
# invalid-name is triggered by top-level alembic constants like revision instead of REVISION

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "37edf9c48404"  # pragma: allowlist secret
down_revision = "cad3c933830b"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    # UserWarning: autogenerate skipping functional index idx_email_primary_email_lower; not supported by SQLAlchemy reflection
    op.create_index(
        "idx_email_primary_email_lower",
        "emails",
        [sa.text("lower(primary_email)")],
        unique=True,
    )
    # UserWarning: autogenerate skipping functional index idx_fxa_primary_email_lower; not supported by SQLAlchemy reflection
    op.create_index(
        "idx_fxa_primary_email_lower",
        "fxa",
        [sa.text("lower(primary_email)")],
        unique=False,
    )


def downgrade():
    op.drop_index("idx_email_primary_email_lower", table_name="emails")
    op.drop_index("idx_fxa_primary_email_lower", table_name="fxa")
