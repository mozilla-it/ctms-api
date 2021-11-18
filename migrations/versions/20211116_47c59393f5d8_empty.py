"""(Empty Revision, moved to ad4a8f10e344)

Revision ID: 47c59393f5d8
Revises: 1ef38317ff85
Create Date: 2021-11-16 23:39:28.095851

"""
# pylint: disable=no-member invalid-name
# no-member is triggered by alembic.op, which has dynamically added functions
# invalid-name is triggered by migration file names with a date prefix
# invalid-name is triggered by top-level alembic constants like revision instead of REVISION

# revision identifiers, used by Alembic.
revision = "47c59393f5d8"  # pragma: allowlist secret
down_revision = "1ef38317ff85"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
