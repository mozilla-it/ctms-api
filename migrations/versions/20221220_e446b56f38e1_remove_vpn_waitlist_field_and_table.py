"""Remove vpn_waitlist field and table

Revision ID: e446b56f38e1
Revises: 9c37ea9b5bba
Create Date: 2022-12-20 11:18:28.007114

"""
# pylint: disable=no-member invalid-name
# no-member is triggered by alembic.op, which has dynamically added functions
# invalid-name is triggered by migration file names with a date prefix
# invalid-name is triggered by top-level alembic constants like revision instead of REVISION

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "e446b56f38e1"  # pragma: allowlist secret
down_revision = "9c37ea9b5bba"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    # Migrate the VPN data to the `waitlist` table.
    op.execute(
        """
    INSERT INTO waitlists(email_id, name, fields, create_timestamp, update_timestamp)
    SELECT email_id, 'vpn', json_build_object('platform', platform, 'geo', geo), create_timestamp, update_timestamp
    FROM vpn_waitlist
    """
    )

    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("vpn_waitlist")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "vpn_waitlist",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("email_id", postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column("geo", sa.VARCHAR(length=100), autoincrement=False, nullable=True),
        sa.Column(
            "platform", sa.VARCHAR(length=100), autoincrement=False, nullable=True
        ),
        sa.Column(
            "create_timestamp",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "update_timestamp",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["email_id"], ["emails.email_id"], name="vpn_waitlist_email_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="vpn_waitlist_pkey"),
        sa.UniqueConstraint("email_id", name="vpn_waitlist_email_id_key"),
    )
    # ### end Alembic commands ###

    # Migrate the `waitlists` data into the `vpn_waitlist` table.
    op.execute(
        """
    INSERT INTO vpn_waitlist(email_id, geo, platform, create_timestamp, update_timestamp)
    SELECT email_id, fields->>'geo', fields->>'platform', create_timestamp, update_timestamp
    FROM waitlists
    WHERE name = 'vpn'
    """
    )