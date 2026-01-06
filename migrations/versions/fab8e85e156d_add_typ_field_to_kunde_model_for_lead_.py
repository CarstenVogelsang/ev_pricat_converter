"""Add typ field to Kunde model for Lead distinction

Revision ID: fab8e85e156d
Revises: cb8401b27c4c
Create Date: 2026-01-05 14:18:27.406075

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fab8e85e156d'
down_revision = 'cb8401b27c4c'
branch_labels = None
depends_on = None


def upgrade():
    # Add typ column with default 'kunde' for existing records
    # All existing records are customers (not leads)
    with op.batch_alter_table('kunde', schema=None) as batch_op:
        batch_op.add_column(sa.Column('typ', sa.String(length=20), nullable=False, server_default='kunde'))
        batch_op.create_index(batch_op.f('ix_kunde_typ'), ['typ'], unique=False)


def downgrade():
    with op.batch_alter_table('kunde', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_kunde_typ'))
        batch_op.drop_column('typ')
