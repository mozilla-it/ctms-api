"""adding an index to updatetimestamp in Email table

Revision ID: 832a2a588c88
Revises: c57f9a6084eb
Create Date: 2021-04-27 22:29:57.766070

"""
# pylint: disable=no-member invalid-name
# no-member is triggered by alembic.op, which has dynamically added functions
# invalid-name is triggered by migration file names with a date prefix
# invalid-name is triggered by top-level alembic constants like revision instead of REVISION

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "832a2a588c88"  # pragma: allowlist secret
down_revision = "c57f9a6084eb"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index(
        op.f("ix_emails_update_timestamp"), "emails", ["update_timestamp"], unique=False
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_emails_update_timestamp"), table_name="emails")
    # ### end Alembic commands ###