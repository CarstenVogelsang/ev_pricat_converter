"""Add EmailTemplate and Kunde email settings

Revision ID: f5898ef9f836
Revises: dd224207bda2
Create Date: 2025-12-23 19:00:48.416874

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f5898ef9f836'
down_revision = 'dd224207bda2'
branch_labels = None
depends_on = None


def upgrade():
    # Create EmailTemplate table (skip if already exists via init-db)
    from sqlalchemy import inspect
    from alembic import op

    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()

    if 'email_template' not in tables:
        op.create_table('email_template',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('schluessel', sa.String(50), nullable=False),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('beschreibung', sa.Text(), nullable=True),
            sa.Column('betreff', sa.String(200), nullable=False),
            sa.Column('body_html', sa.Text(), nullable=False),
            sa.Column('body_text', sa.Text(), nullable=True),
            sa.Column('aktiv', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('erstellt_am', sa.DateTime(), nullable=True),
            sa.Column('aktualisiert_am', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_email_template_schluessel', 'email_template', ['schluessel'], unique=True)

    # Add email settings to Kunde
    with op.batch_alter_table('kunde', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email_footer', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('ist_systemkunde', sa.Boolean(), nullable=False, server_default='0'))


def downgrade():
    # Remove email settings from Kunde
    with op.batch_alter_table('kunde', schema=None) as batch_op:
        batch_op.drop_column('ist_systemkunde')
        batch_op.drop_column('email_footer')

    # Drop EmailTemplate table
    op.drop_index('ix_email_template_schluessel', table_name='email_template')
    op.drop_table('email_template')
