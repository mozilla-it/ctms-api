"""Add mofo table

Revision ID: c770b3d28ea1
Revises: 3c94af7ca946
Create Date: 2021-03-26 16:43:30.841280

"""

# pylint: disable=no-member invalid-name
# no-member is triggered by alembic.op, which has dynamically added functions
# invalid-name is triggered by migration file names with a date prefix
# invalid-name is triggered by top-level alembic constants like revision instead of REVISION

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c770b3d28ea1"  # pragma: allowlist secret
down_revision = "3c94af7ca946"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mofo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mofo_email_id", sa.String(length=255), nullable=True),
        sa.Column("mofo_contact_id", sa.String(length=255), nullable=True),
        sa.Column("mofo_relevant", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(
            ["email_id"],
            ["emails.email_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email_id"),
        sa.UniqueConstraint("mofo_email_id"),
    )


def downgrade():
    op.drop_table("mofo")
