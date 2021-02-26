"""Add email.double_opt_in

Revision ID: 3f8a97b79852
Revises: 9a91e36e6e6f
Create Date: 2021-02-26 15:07:33.266833

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "3f8a97b79852"  # pragma: allowlist secret
down_revision = "9a91e36e6e6f"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("emails", sa.Column("double_opt_in", sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column("emails", "double_opt_in")
