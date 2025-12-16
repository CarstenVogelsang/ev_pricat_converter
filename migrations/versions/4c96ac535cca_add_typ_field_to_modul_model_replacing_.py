"""Add typ field to Modul model replacing ist_basis

Revision ID: 4c96ac535cca
Revises: 972d11ba691f
Create Date: 2025-12-12 17:23:06.391617

Migration steps:
1. Add typ column
2. Migrate ist_basis values: True -> 'basis', False -> 'premium' (placeholder, updated in seed)
3. Set default for typ
4. Drop ist_basis column
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4c96ac535cca'
down_revision = '972d11ba691f'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Add typ column (nullable initially for data migration)
    with op.batch_alter_table('modul', schema=None) as batch_op:
        batch_op.add_column(sa.Column('typ', sa.String(length=30), nullable=True))

    # Step 2: Migrate data from ist_basis to typ
    # Use raw SQL for SQLite compatibility
    connection = op.get_bind()

    # Set typ='basis' where ist_basis=1 (True)
    connection.execute(
        sa.text("UPDATE modul SET typ = 'basis' WHERE ist_basis = 1")
    )

    # Set typ='premium' for all others (will be updated by seed later)
    connection.execute(
        sa.text("UPDATE modul SET typ = 'premium' WHERE ist_basis = 0 OR ist_basis IS NULL")
    )

    # Step 3: Set default and drop ist_basis
    with op.batch_alter_table('modul', schema=None) as batch_op:
        batch_op.alter_column('typ', nullable=False, server_default='basis')
        batch_op.drop_column('ist_basis')


def downgrade():
    # Step 1: Add ist_basis column back
    with op.batch_alter_table('modul', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ist_basis', sa.BOOLEAN(), nullable=True))

    # Step 2: Migrate data back
    connection = op.get_bind()

    # Set ist_basis=1 where typ='basis'
    connection.execute(
        sa.text("UPDATE modul SET ist_basis = 1 WHERE typ = 'basis'")
    )

    # Set ist_basis=0 for all others
    connection.execute(
        sa.text("UPDATE modul SET ist_basis = 0 WHERE typ != 'basis' OR typ IS NULL")
    )

    # Step 3: Set defaults and drop typ
    with op.batch_alter_table('modul', schema=None) as batch_op:
        batch_op.alter_column('ist_basis', nullable=False, server_default='0')
        batch_op.drop_column('typ')
