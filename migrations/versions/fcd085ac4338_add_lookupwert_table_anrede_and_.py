"""Add LookupWert table, anrede and kommunikation_stil to Kunde

Revision ID: fcd085ac4338
Revises: f5898ef9f836
Create Date: 2025-12-24 10:23:56.988613

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fcd085ac4338'
down_revision = 'f5898ef9f836'
branch_labels = None
depends_on = None


def upgrade():
    # Create LookupWert table for generic key-value storage (if not exists)
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()

    if 'lookup_wert' not in tables:
        op.create_table(
            'lookup_wert',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('kategorie', sa.String(length=50), nullable=False),
            sa.Column('schluessel', sa.String(length=50), nullable=False),
            sa.Column('wert', sa.String(length=255), nullable=False),
            sa.Column('sortierung', sa.Integer(), nullable=True, default=0),
            sa.Column('aktiv', sa.Boolean(), nullable=False, default=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('kategorie', 'schluessel', name='uq_lookup_kategorie_schluessel')
        )
        op.create_index(op.f('ix_lookup_wert_kategorie'), 'lookup_wert', ['kategorie'], unique=False)

    # Add anrede and kommunikation_stil columns to kunde (if not exists)
    columns = [c['name'] for c in inspector.get_columns('kunde')]
    with op.batch_alter_table('kunde', schema=None) as batch_op:
        if 'anrede' not in columns:
            batch_op.add_column(sa.Column('anrede', sa.String(length=20), nullable=True, server_default='firma'))
        if 'kommunikation_stil' not in columns:
            batch_op.add_column(sa.Column('kommunikation_stil', sa.String(length=20), nullable=True, server_default='foermlich'))


def downgrade():
    # Remove anrede and kommunikation_stil columns from kunde
    with op.batch_alter_table('kunde', schema=None) as batch_op:
        batch_op.drop_column('kommunikation_stil')
        batch_op.drop_column('anrede')

    # Drop LookupWert table
    op.drop_index(op.f('ix_lookup_wert_kategorie'), table_name='lookup_wert')
    op.drop_table('lookup_wert')
