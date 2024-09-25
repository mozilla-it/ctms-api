"""migrate-de-fr-kip-to-fxn-deng-4402

Revision ID: 8181a9a3df53
Revises: 3689b813fe22
Create Date: 2024-09-23 12:17:16.531473

"""
# pylint: disable=no-member invalid-name
# no-member is triggered by alembic.op, which has dynamically added functions
# invalid-name is triggered by migration file names with a date prefix
# invalid-name is triggered by top-level alembic constants like revision instead of REVISION

import sqlalchemy as sa
from alembic import op

revision = "8181a9a3df53"  # pragma: allowlist secret
down_revision = "3689b813fe22"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    # Subscribe users to 'mozilla-and-you' a/k/a Firefox News
    op.execute("""\
        INSERT INTO newsletters (email_id, name, subscribed)
        SELECT e.email_id, 'mozilla-and-you', TRUE
        FROM emails e
        JOIN newsletters n ON e.email_id = n.email_id
        WHERE n.name = 'knowledge-is-power'
          AND n.subscribed = TRUE
          AND (e.email_lang ~* 'de|fr' OR n.lang ~* 'de|fr')
        ON CONFLICT (email_id, name) DO NOTHING;
    """)

    # Unsubscribe users from 'knowledge-is-power'
    op.execute("""\
        UPDATE newsletters
        SET subscribed = FALSE, unsub_reason = 'Jira ticket DENG-4402'
        WHERE email_id IN (
            SELECT e.email_id
            FROM emails e
            JOIN newsletters n ON e.email_id = n.email_id
            WHERE n.name = 'knowledge-is-power'
              AND n.subscribed = TRUE
              AND (e.email_lang ~* 'de|fr' OR n.lang ~* 'de|fr')
        )
          AND name = 'knowledge-is-power'
          AND subscribed = TRUE;
    """)


def downgrade():
    pass
