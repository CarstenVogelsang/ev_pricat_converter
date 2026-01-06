"""Rename erp_modul table to modul_erp

Revision ID: 2516b7931ee1
Revises: 7539af78f623
Create Date: 2026-01-01 10:31:45.561189

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2516b7931ee1'
down_revision = '7539af78f623'
branch_labels = None
depends_on = None


def upgrade():
    # Rename table erp_modul -> modul_erp
    op.rename_table('erp_modul', 'modul_erp')

    # Update FK constraint on komponente to point to new table name
    with op.batch_alter_table('komponente', schema=None) as batch_op:
        batch_op.drop_constraint('fk_komponente_erp_modul', type_='foreignkey')
        batch_op.create_foreign_key(
            'fk_komponente_modul_erp',
            'modul_erp',
            ['erp_modul_id'],
            ['id']
        )


def downgrade():
    # Revert FK constraint
    with op.batch_alter_table('komponente', schema=None) as batch_op:
        batch_op.drop_constraint('fk_komponente_modul_erp', type_='foreignkey')
        batch_op.create_foreign_key(
            'fk_komponente_erp_modul',
            'erp_modul',
            ['erp_modul_id'],
            ['id']
        )

    # Rename table back
    op.rename_table('modul_erp', 'erp_modul')
