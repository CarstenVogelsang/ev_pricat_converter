"""Add TaskKommentar model PRD011-T055

Revision ID: cb8401b27c4c
Revises: 5f3cf28e46e5
Create Date: 2026-01-01 12:02:41.133368

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cb8401b27c4c'
down_revision = '5f3cf28e46e5'
branch_labels = None
depends_on = None


def upgrade():
    # PRD011-T055: Create task_kommentar table for review workflow
    op.create_table('task_kommentar',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('typ', sa.String(length=20), nullable=False, server_default='kommentar'),
        sa.Column('inhalt', sa.Text(), nullable=False),
        sa.Column('erledigt', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('erledigt_am', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['task.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    # Index for faster queries
    op.create_index(op.f('ix_task_kommentar_task_id'), 'task_kommentar', ['task_id'], unique=False)
    op.create_index(op.f('ix_task_kommentar_typ'), 'task_kommentar', ['typ'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_task_kommentar_typ'), table_name='task_kommentar')
    op.drop_index(op.f('ix_task_kommentar_task_id'), table_name='task_kommentar')
    op.drop_table('task_kommentar')
