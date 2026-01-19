"""Add Medium model for global media library

Revision ID: bdb466fd8e04
Revises: 5a469e9dca89
Create Date: 2026-01-14 20:17:20.571483

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bdb466fd8e04'
down_revision = '5a469e9dca89'
branch_labels = None
depends_on = None


def upgrade():
    # Create medium table for global media library
    op.create_table('medium',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('titel', sa.String(length=200), nullable=False),
        sa.Column('beschreibung', sa.Text(), nullable=True),
        sa.Column('typ', sa.String(length=50), nullable=True),
        sa.Column('dateiname', sa.String(length=255), nullable=True),
        sa.Column('dateipfad', sa.String(length=500), nullable=True),
        sa.Column('externe_url', sa.String(length=1000), nullable=True),
        sa.Column('thumbnail_url', sa.String(length=1000), nullable=True),
        sa.Column('dateigroesse', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('breite', sa.Integer(), nullable=True),
        sa.Column('hoehe', sa.Integer(), nullable=True),
        sa.Column('erstellt_am', sa.DateTime(), nullable=True),
        sa.Column('erstellt_von_id', sa.Integer(), nullable=True),
        sa.Column('aktiv', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['erstellt_von_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('medium')
