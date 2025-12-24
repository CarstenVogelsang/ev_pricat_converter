"""Add versioning and archiving to Fragebogen

Revision ID: dd224207bda2
Revises: f6d68441123e
Create Date: 2025-12-23 18:51:06.148368

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dd224207bda2'
down_revision = 'f6d68441123e'
branch_labels = None
depends_on = None


def upgrade():
    # Add versioning and archiving fields to Fragebogen
    with op.batch_alter_table('fragebogen', schema=None) as batch_op:
        # Versioning: self-referential FK for version chain
        batch_op.add_column(sa.Column('vorgaenger_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('version_nummer', sa.Integer(), nullable=False, server_default='1'))
        # Archiving: soft-delete
        batch_op.add_column(sa.Column('archiviert', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('archiviert_am', sa.DateTime(), nullable=True))
        batch_op.create_foreign_key('fk_fragebogen_vorgaenger', 'fragebogen', ['vorgaenger_id'], ['id'])


def downgrade():
    # Remove versioning and archiving fields from Fragebogen
    with op.batch_alter_table('fragebogen', schema=None) as batch_op:
        batch_op.drop_constraint('fk_fragebogen_vorgaenger', type_='foreignkey')
        batch_op.drop_column('archiviert_am')
        batch_op.drop_column('archiviert')
        batch_op.drop_column('version_nummer')
        batch_op.drop_column('vorgaenger_id')
