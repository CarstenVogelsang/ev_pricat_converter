"""Add create_changelog_on_complete to Task

Revision ID: 86324463d2b8
Revises: c4c541842994
Create Date: 2025-12-30 16:29:56.210431

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '86324463d2b8'
down_revision = 'c4c541842994'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.add_column(sa.Column('create_changelog_on_complete', sa.Boolean(), nullable=True))


def downgrade():
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.drop_column('create_changelog_on_complete')
