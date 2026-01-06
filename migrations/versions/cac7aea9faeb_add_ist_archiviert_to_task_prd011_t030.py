"""Add ist_archiviert to Task (PRD011-T030)

Revision ID: cac7aea9faeb
Revises: 248a296ef2c5
Create Date: 2025-12-31 09:38:54.564594

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cac7aea9faeb'
down_revision = '248a296ef2c5'
branch_labels = None
depends_on = None


def upgrade():
    # Add ist_archiviert field to task table with default value for existing rows
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ist_archiviert', sa.Boolean(),
                                       nullable=False, server_default='0'))


def downgrade():
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.drop_column('ist_archiviert')
