"""Add api_client table

Revision ID: 435d9701a9a4
Revises: 20f05b0d3dc8
Create Date: 2021-03-09 21:28:16.818488

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "435d9701a9a4"  # pragma: allowlist secret
down_revision = "20f05b0d3dc8"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "api_client",
        sa.Column("client_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("hashed_secret", sa.String(), nullable=False),
        sa.Column(
            "create_timestamp",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "update_timestamp",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("client_id"),
    )


def downgrade():
    op.drop_table("api_client")
