"""Add ErpModul table and erp_modul_id FK PRD011-T052

Revision ID: 7539af78f623
Revises: fcba451f5404
Create Date: 2025-12-31 16:57:55.987853

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7539af78f623'
down_revision = 'fcba451f5404'
branch_labels = None
depends_on = None


def upgrade():
    # PRD011-T052: Add ErpModul table for ERP/Shop module references
    op.create_table('erp_modul',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('artikelnummer', sa.String(length=50), nullable=False),
        sa.Column('bezeichnung', sa.String(length=200), nullable=False),
        sa.Column('kontext', sa.String(length=20), nullable=False),
        sa.Column('beschreibung', sa.Text(), nullable=True),
        sa.Column('aktiv', sa.Boolean(), nullable=False),
        sa.Column('sortierung', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('artikelnummer')
    )

    # Add FK to Komponente for ERP module reference
    with op.batch_alter_table('komponente', schema=None) as batch_op:
        batch_op.add_column(sa.Column('erp_modul_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_komponente_erp_modul', 'erp_modul', ['erp_modul_id'], ['id'])


def downgrade():
    with op.batch_alter_table('komponente', schema=None) as batch_op:
        batch_op.drop_constraint('fk_komponente_erp_modul', type_='foreignkey')
        batch_op.drop_column('erp_modul_id')

    op.drop_table('erp_modul')
