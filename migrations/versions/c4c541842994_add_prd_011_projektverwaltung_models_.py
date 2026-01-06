"""Add PRD-011 Projektverwaltung models (Projekt, Komponente, Task, ChangelogEintrag, user_typ)

Revision ID: c4c541842994
Revises: 46224706c611
Create Date: 2025-12-29 20:38:12.126994

Note: The tables projekt, komponente, task, changelog_eintrag may already exist
from init-db. This migration handles both cases gracefully.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'c4c541842994'
down_revision = '46224706c611'
branch_labels = None
depends_on = None


def table_exists(table_name):
    """Check if a table exists in the database."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def column_exists(table_name, column_name):
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade():
    # ### PRD-011: Projektverwaltung Tables ###
    # Tables may already exist from init-db, so we check first

    # Create projekt table if not exists
    if not table_exists('projekt'):
        op.create_table('projekt',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('beschreibung', sa.Text(), nullable=True),
            sa.Column('typ', sa.String(length=20), nullable=False, server_default='intern'),
            sa.Column('kunde_id', sa.Integer(), nullable=True),
            sa.Column('aktiv', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['kunde_id'], ['kunde.id'], ),
            sa.PrimaryKeyConstraint('id')
        )

    # Create komponente table if not exists
    if not table_exists('komponente'):
        op.create_table('komponente',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('projekt_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('prd_nummer', sa.String(length=10), nullable=True),
            sa.Column('typ', sa.String(length=20), nullable=False, server_default='modul'),
            sa.Column('modul_id', sa.Integer(), nullable=True),
            sa.Column('prd_inhalt', sa.Text(), nullable=True),
            sa.Column('aktuelle_phase', sa.String(length=10), server_default='poc'),
            sa.Column('status', sa.String(length=20), server_default='aktiv'),
            sa.Column('icon', sa.String(length=50), server_default='ti-package'),
            sa.Column('sortierung', sa.Integer(), server_default='0'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['projekt_id'], ['projekt.id'], ),
            sa.ForeignKeyConstraint(['modul_id'], ['modul.id'], ),
            sa.PrimaryKeyConstraint('id')
        )

    # Create task table if not exists
    if not table_exists('task'):
        op.create_table('task',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('komponente_id', sa.Integer(), nullable=False),
            sa.Column('titel', sa.String(length=200), nullable=False),
            sa.Column('beschreibung', sa.Text(), nullable=True),
            sa.Column('phase', sa.String(length=10), nullable=False, server_default='poc'),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='backlog'),
            sa.Column('prioritaet', sa.String(length=20), nullable=False, server_default='mittel'),
            sa.Column('zugewiesen_an', sa.Integer(), nullable=True),
            sa.Column('sortierung', sa.Integer(), server_default='0'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.Column('erledigt_am', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['komponente_id'], ['komponente.id'], ),
            sa.ForeignKeyConstraint(['zugewiesen_an'], ['user.id'], ),
            sa.PrimaryKeyConstraint('id')
        )

    # Create changelog_eintrag table if not exists
    if not table_exists('changelog_eintrag'):
        op.create_table('changelog_eintrag',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('komponente_id', sa.Integer(), nullable=False),
            sa.Column('task_id', sa.Integer(), nullable=True),
            sa.Column('version', sa.String(length=20), nullable=False),
            sa.Column('kategorie', sa.String(length=20), nullable=False, server_default='added'),
            sa.Column('beschreibung', sa.Text(), nullable=False),
            sa.Column('sichtbarkeit', sa.String(length=20), nullable=False, server_default='intern'),
            sa.Column('erstellt_am', sa.DateTime(), nullable=True),
            sa.Column('erstellt_von', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['komponente_id'], ['komponente.id'], ),
            sa.ForeignKeyConstraint(['task_id'], ['task.id'], ),
            sa.ForeignKeyConstraint(['erstellt_von'], ['user.id'], ),
            sa.PrimaryKeyConstraint('id')
        )

    # Add user_typ column to user table if not exists
    if not column_exists('user', 'user_typ'):
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.add_column(sa.Column('user_typ', sa.String(length=20), nullable=False, server_default='mensch'))


def downgrade():
    # Remove user_typ column
    if column_exists('user', 'user_typ'):
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.drop_column('user_typ')

    # Drop tables in reverse order (respect foreign keys)
    # Note: Only drop if they were created by this migration
    if table_exists('changelog_eintrag'):
        op.drop_table('changelog_eintrag')
    if table_exists('task'):
        op.drop_table('task')
    if table_exists('komponente'):
        op.drop_table('komponente')
    if table_exists('projekt'):
        op.drop_table('projekt')
