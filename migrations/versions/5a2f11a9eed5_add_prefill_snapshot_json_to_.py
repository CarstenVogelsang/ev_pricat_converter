"""Add prefill_snapshot_json to FragebogenTeilnahme

Revision ID: 5a2f11a9eed5
Revises: 855ad509f342
Create Date: 2025-12-22 15:07:22.479446

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5a2f11a9eed5'
down_revision = '855ad509f342'
branch_labels = None
depends_on = None


def upgrade():
    """Add prefill_snapshot_json column for V2 questionnaire prefill tracking."""
    with op.batch_alter_table('fragebogen_teilnahme', schema=None) as batch_op:
        batch_op.add_column(sa.Column('prefill_snapshot_json', sa.JSON(), nullable=True))


def downgrade():
    """Remove prefill_snapshot_json column."""
    with op.batch_alter_table('fragebogen_teilnahme', schema=None) as batch_op:
        batch_op.drop_column('prefill_snapshot_json')
