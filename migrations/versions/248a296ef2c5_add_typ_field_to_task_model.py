"""Add typ field to Task model

Revision ID: 248a296ef2c5
Revises: 86324463d2b8
Create Date: 2025-12-30 18:47:21.769495

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '248a296ef2c5'
down_revision = '86324463d2b8'
branch_labels = None
depends_on = None


def upgrade():
    # Add typ field to task table with default value for existing rows
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.add_column(sa.Column('typ', sa.String(length=30), nullable=False, server_default='funktion'))


def downgrade():
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.drop_column('typ')
