"""Drop old email.mofo columns

Revision ID: 2bc6c4d12e2e
Revises: c770b3d28ea1
Create Date: 2021-03-30 13:43:10.312694

"""

# pylint: disable=no-member invalid-name
# no-member is triggered by alembic.op, which has dynamically added functions
# invalid-name is triggered by migration file names with a date prefix
# invalid-name is triggered by top-level alembic constants like revision instead of REVISION

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2bc6c4d12e2e"  # pragma: allowlist secret
down_revision = "c770b3d28ea1"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("emails", "mofo_relevant")
    op.drop_column("emails", "mofo_id")


def downgrade():
    op.add_column(
        "emails",
        sa.Column(
            "mofo_id", sa.VARCHAR(length=255), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        "emails",
        sa.Column("mofo_relevant", sa.BOOLEAN(), autoincrement=False, nullable=True),
    )
