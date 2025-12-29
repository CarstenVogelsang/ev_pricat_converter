"""Add ProduktLookup and Attributgruppe tables for PRD-009

Revision ID: ffa7e6fe81a2
Revises: f1219a5748fd
Create Date: 2025-12-28 19:21:15.160330

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ffa7e6fe81a2'
down_revision = 'f1219a5748fd'
branch_labels = None
depends_on = None


def upgrade():
    # === ProduktLookup table ===
    op.create_table(
        'produkt_lookup',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('kategorie', sa.String(length=50), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('bezeichnung', sa.String(length=255), nullable=False),
        sa.Column('zusatz_1', sa.String(length=100), nullable=True),
        sa.Column('zusatz_2', sa.String(length=100), nullable=True),
        sa.Column('zusatz_3', sa.String(length=100), nullable=True),
        sa.Column('sortierung', sa.Integer(), nullable=True, default=0),
        sa.Column('aktiv', sa.Boolean(), nullable=False, default=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('kategorie', 'code', name='uq_produkt_lookup_kategorie_code')
    )
    op.create_index(op.f('ix_produkt_lookup_kategorie'), 'produkt_lookup', ['kategorie'], unique=False)

    # === Attributgruppe table ===
    op.create_table(
        'attributgruppe',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ntg_schluessel', sa.String(length=15), nullable=True),
        sa.Column('ebene_1_code', sa.String(length=2), nullable=True),
        sa.Column('ebene_1_name', sa.String(length=100), nullable=True),
        sa.Column('ebene_2_code', sa.String(length=3), nullable=True),
        sa.Column('ebene_2_name', sa.String(length=100), nullable=True),
        sa.Column('ebene_3_code', sa.String(length=3), nullable=True),
        sa.Column('ebene_3_name', sa.String(length=100), nullable=True),
        sa.Column('ebene_4_code', sa.String(length=3), nullable=True),
        sa.Column('ebene_4_name', sa.String(length=100), nullable=True),
        sa.Column('ebene_5_code', sa.String(length=3), nullable=True),
        sa.Column('ebene_5_name', sa.String(length=100), nullable=True),
        sa.Column('aktiv', sa.Boolean(), nullable=False, default=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ntg_schluessel', name='uq_attributgruppe_ntg_schluessel')
    )
    op.create_index(op.f('ix_attributgruppe_ntg_schluessel'), 'attributgruppe', ['ntg_schluessel'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_attributgruppe_ntg_schluessel'), table_name='attributgruppe')
    op.drop_table('attributgruppe')
    op.drop_index(op.f('ix_produkt_lookup_kategorie'), table_name='produkt_lookup')
    op.drop_table('produkt_lookup')
