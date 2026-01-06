"""Add icon column to modul_erp PRD011-T054

Revision ID: 5f3cf28e46e5
Revises: 2516b7931ee1
Create Date: 2026-01-01 11:17:17.593343

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5f3cf28e46e5'
down_revision = '2516b7931ee1'
branch_labels = None
depends_on = None


def upgrade():
    # PRD011-T054: Add icon column to modul_erp for visual representation
    with op.batch_alter_table('modul_erp', schema=None) as batch_op:
        batch_op.add_column(sa.Column('icon', sa.String(length=50), nullable=True, server_default='ti-plug'))


def downgrade():
    with op.batch_alter_table('modul_erp', schema=None) as batch_op:
        batch_op.drop_column('icon')
