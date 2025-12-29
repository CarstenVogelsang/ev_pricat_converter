"""Add LieferantBranche junction table

Revision ID: 46224706c611
Revises: 0a8a1f543f8e
Create Date: 2025-12-29 09:54:24.910619

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '46224706c611'
down_revision = '0a8a1f543f8e'
branch_labels = None
depends_on = None


def upgrade():
    # Create lieferant_branche junction table
    op.create_table('lieferant_branche',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lieferant_id', sa.Integer(), nullable=False),
        sa.Column('branche_id', sa.Integer(), nullable=False),
        sa.Column('ist_hauptbranche', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['branche_id'], ['branche.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lieferant_id'], ['lieferant.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lieferant_id', 'branche_id', name='uq_lieferant_branche')
    )


def downgrade():
    op.drop_table('lieferant_branche')
