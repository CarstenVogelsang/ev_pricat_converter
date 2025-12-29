"""Add support ticket system (PRD-007)

Revision ID: b168587a39b0
Revises: 941599ad1756
Create Date: 2025-12-28 08:36:11.182564

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b168587a39b0'
down_revision = '941599ad1756'
branch_labels = None
depends_on = None


def upgrade():
    # ### Support Team ###
    op.create_table('support_team',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('beschreibung', sa.Text(), nullable=True),
        sa.Column('email', sa.String(length=120), nullable=True),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('aktiv', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # ### Support Team Mitglied ###
    op.create_table('support_team_mitglied',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('ist_teamleiter', sa.Boolean(), nullable=True),
        sa.Column('benachrichtigung_aktiv', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['support_team.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_id', 'user_id', name='uq_support_team_user')
    )

    # ### Support Ticket ###
    op.create_table('support_ticket',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nummer', sa.String(length=20), nullable=False),
        sa.Column('titel', sa.String(length=200), nullable=False),
        sa.Column('beschreibung', sa.Text(), nullable=False),
        sa.Column('typ', sa.String(length=30), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=True),
        sa.Column('prioritaet', sa.String(length=20), nullable=True),
        sa.Column('modul_id', sa.Integer(), nullable=True),
        sa.Column('hilfetext_schluessel', sa.String(length=100), nullable=True),
        sa.Column('seiten_url', sa.String(length=500), nullable=True),
        sa.Column('erstellt_von_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('bearbeiter_id', sa.Integer(), nullable=True),
        sa.Column('kunde_id', sa.Integer(), nullable=True),
        sa.Column('erstellt_am', sa.DateTime(), nullable=True),
        sa.Column('aktualisiert_am', sa.DateTime(), nullable=True),
        sa.Column('geloest_am', sa.DateTime(), nullable=True),
        sa.Column('geschlossen_am', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['bearbeiter_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['erstellt_von_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['kunde_id'], ['kunde.id'], ),
        sa.ForeignKeyConstraint(['modul_id'], ['modul.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['support_team.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_support_ticket_nummer', 'support_ticket', ['nummer'], unique=True)
    op.create_index('ix_support_ticket_status', 'support_ticket', ['status'], unique=False)

    # ### Ticket Kommentar ###
    op.create_table('ticket_kommentar',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('inhalt', sa.Text(), nullable=False),
        sa.Column('ist_intern', sa.Boolean(), nullable=True),
        sa.Column('ist_status_aenderung', sa.Boolean(), nullable=True),
        sa.Column('erstellt_am', sa.DateTime(), nullable=True),
        sa.Column('aktualisiert_am', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['ticket_id'], ['support_ticket.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # ### Kunde table changes (detected by Alembic) ###
    with op.batch_alter_table('kunde', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_kunde_user_id'))
        batch_op.create_unique_constraint(None, ['user_id'])


def downgrade():
    # ### Kunde table changes ###
    with op.batch_alter_table('kunde', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='unique')
        batch_op.create_index(batch_op.f('ix_kunde_user_id'), ['user_id'], unique=1)

    # ### Drop Support tables ###
    op.drop_table('ticket_kommentar')
    op.drop_index('ix_support_ticket_status', table_name='support_ticket')
    op.drop_index('ix_support_ticket_nummer', table_name='support_ticket')
    op.drop_table('support_ticket')
    op.drop_table('support_team_mitglied')
    op.drop_table('support_team')
