"""Add admin_page_visit table for recently visited tracking

Revision ID: d887e4092bf3
Revises: bdb466fd8e04
Create Date: 2026-01-15 08:38:52.309899

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd887e4092bf3'
down_revision = 'bdb466fd8e04'
branch_labels = None
depends_on = None


def upgrade():
    # Create admin_page_visit table for tracking recently visited admin pages
    op.create_table('admin_page_visit',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('endpoint', sa.String(length=200), nullable=False),
        sa.Column('page_url', sa.String(length=500), nullable=False),
        sa.Column('page_title', sa.String(length=200), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], name='fk_admin_page_visit_user_id'),
        sa.PrimaryKeyConstraint('id')
    )
    # Create indexes for efficient queries
    op.create_index('ix_admin_page_visit_user_id', 'admin_page_visit', ['user_id'], unique=False)
    op.create_index('ix_admin_page_visit_timestamp', 'admin_page_visit', ['timestamp'], unique=False)
    op.create_index('idx_admin_page_visit_user_timestamp', 'admin_page_visit', ['user_id', 'timestamp'], unique=False)


def downgrade():
    # Drop indexes first
    op.drop_index('idx_admin_page_visit_user_timestamp', table_name='admin_page_visit')
    op.drop_index('ix_admin_page_visit_timestamp', table_name='admin_page_visit')
    op.drop_index('ix_admin_page_visit_user_id', table_name='admin_page_visit')
    # Drop table
    op.drop_table('admin_page_visit')
