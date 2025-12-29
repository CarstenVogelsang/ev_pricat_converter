"""Add icon, farbe and modul_id to lookup_wert table

Revision ID: f1219a5748fd
Revises: b168587a39b0
Create Date: 2025-12-28 13:28:10.712460

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1219a5748fd'
down_revision = 'b168587a39b0'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to lookup_wert table
    with op.batch_alter_table('lookup_wert', schema=None) as batch_op:
        batch_op.add_column(sa.Column('icon', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('farbe', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('modul_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_lookup_wert_modul', 'modul', ['modul_id'], ['id'])


def downgrade():
    with op.batch_alter_table('lookup_wert', schema=None) as batch_op:
        batch_op.drop_constraint('fk_lookup_wert_modul', type_='foreignkey')
        batch_op.drop_column('modul_id')
        batch_op.drop_column('farbe')
        batch_op.drop_column('icon')
