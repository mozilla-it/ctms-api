"""Remove duplicate Stripe Customers

Revision ID: 4eed7a83e324
Revises: 47c59393f5d8
Create Date: 2021-11-18 22:14:33.853594

"""
# pylint: disable=no-member invalid-name
# no-member is triggered by alembic.op, which has dynamically added functions
# invalid-name is triggered by migration file names with a date prefix
# invalid-name is triggered by top-level alembic constants like revision instead of REVISION

from alembic import op

# revision identifiers, used by Alembic.
revision = "4eed7a83e324"  # pragma: allowlist secret
down_revision = "47c59393f5d8"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    """
    Find stripe_customers with the same email_id, order them by
    stripe_created, and delete all but the most recent one.

    One path for these duplicates are that a Stripe Customer
    and related FxA account can be rapidly deleted if an invalid
    payment is provided.
    """

    op.execute(
        """
    WITH duplicated AS (
      SELECT email_id, count(*)
      FROM stripe_customer
      WHERE email_id IS NOT NULL
      GROUP BY email_id
      HAVING count(*) > 1),
    ordered AS (
      SELECT sc.email_id,
        stripe_created,
        rank() OVER (partition BY sc.email_id ORDER BY sc.stripe_created) as rnk
      FROM stripe_customer sc
      JOIN duplicated d on d.email_id = sc.email_id),
    to_delete AS (
      SELECT email_id, stripe_created
      FROM ordered
      WHERE rnk >= 2
    )
    DELETE
    FROM stripe_customer
    USING to_delete
    WHERE stripe_customer.email_id = to_delete.email_id
      AND stripe_customer.stripe_created = to_delete.stripe_created;
    """
    )


def downgrade():
    # Non-reversible migration
    pass
