"""add unique constraint to newsletters

Revision ID: 3c94af7ca946
Revises: 435d9701a9a4
Create Date: 2021-03-19 11:39:52.506358

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "3c94af7ca946"  # pragma: allowlist secret
down_revision = "435d9701a9a4"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint("uix_email_name", "newsletters", ["email_id", "name"])


def downgrade():
    op.drop_constraint("uix_email_name", "newsletters", type_="unique")
