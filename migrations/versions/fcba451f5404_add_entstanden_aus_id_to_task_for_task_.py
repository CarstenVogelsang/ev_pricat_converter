"""Add entstanden_aus_id to Task for task splitting PRD011-T041

Revision ID: fcba451f5404
Revises: cac7aea9faeb
Create Date: 2025-12-31 14:28:49.438312

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fcba451f5404'
down_revision = 'cac7aea9faeb'
branch_labels = None
depends_on = None


def upgrade():
    # PRD011-T041: Add entstanden_aus_id for task splitting
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.add_column(sa.Column('entstanden_aus_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_task_entstanden_aus',
            'task',
            ['entstanden_aus_id'],
            ['id']
        )


def downgrade():
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.drop_constraint('fk_task_entstanden_aus', type_='foreignkey')
        batch_op.drop_column('entstanden_aus_id')
