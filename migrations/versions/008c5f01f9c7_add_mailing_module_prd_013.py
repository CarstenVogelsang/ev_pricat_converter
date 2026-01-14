"""Add Mailing module (PRD-013)

Revision ID: 008c5f01f9c7
Revises: fab8e85e156d
Create Date: 2026-01-13 19:57:29.508553

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008c5f01f9c7'
down_revision = 'fab8e85e156d'
branch_labels = None
depends_on = None


def upgrade():
    # Create Mailing table
    op.create_table('mailing',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('titel', sa.String(length=200), nullable=False),
        sa.Column('betreff', sa.String(length=200), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('sektionen_json', sa.JSON(), nullable=True),
        sa.Column('fragebogen_id', sa.Integer(), nullable=True),
        sa.Column('erstellt_von_id', sa.Integer(), nullable=False),
        sa.Column('erstellt_am', sa.DateTime(), nullable=True),
        sa.Column('gesendet_am', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('anzahl_empfaenger', sa.Integer(), nullable=True),
        sa.Column('anzahl_versendet', sa.Integer(), nullable=True),
        sa.Column('anzahl_fehlgeschlagen', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['erstellt_von_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['fragebogen_id'], ['fragebogen.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create MailingZielgruppe table
    op.create_table('mailing_zielgruppe',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('beschreibung', sa.Text(), nullable=True),
        sa.Column('filter_json', sa.JSON(), nullable=True),
        sa.Column('erstellt_von_id', sa.Integer(), nullable=False),
        sa.Column('erstellt_am', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['erstellt_von_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create MailingEmpfaenger table
    op.create_table('mailing_empfaenger',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('mailing_id', sa.Integer(), nullable=False),
        sa.Column('kunde_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('tracking_token', sa.String(length=100), nullable=True),
        sa.Column('hinzugefuegt_am', sa.DateTime(), nullable=True),
        sa.Column('versendet_am', sa.DateTime(), nullable=True),
        sa.Column('fehler_meldung', sa.Text(), nullable=True),
        sa.Column('fragebogen_teilnahme_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['fragebogen_teilnahme_id'], ['fragebogen_teilnahme.id'], ),
        sa.ForeignKeyConstraint(['kunde_id'], ['kunde.id'], ),
        sa.ForeignKeyConstraint(['mailing_id'], ['mailing.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('mailing_id', 'kunde_id', name='uq_mailing_kunde')
    )
    with op.batch_alter_table('mailing_empfaenger', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_mailing_empfaenger_tracking_token'), ['tracking_token'], unique=True)

    # Create MailingKlick table
    op.create_table('mailing_klick',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('empfaenger_id', sa.Integer(), nullable=False),
        sa.Column('link_typ', sa.String(length=50), nullable=False),
        sa.Column('geklickt_am', sa.DateTime(), nullable=True),
        sa.Column('url', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['empfaenger_id'], ['mailing_empfaenger.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Add mailing opt-out fields to Kunde
    with op.batch_alter_table('kunde', schema=None) as batch_op:
        batch_op.add_column(sa.Column('mailing_abgemeldet', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('mailing_abgemeldet_am', sa.DateTime(), nullable=True))


def downgrade():
    # Drop mailing opt-out fields from Kunde
    with op.batch_alter_table('kunde', schema=None) as batch_op:
        batch_op.drop_column('mailing_abgemeldet_am')
        batch_op.drop_column('mailing_abgemeldet')

    # Drop MailingKlick table
    op.drop_table('mailing_klick')

    # Drop MailingEmpfaenger table
    with op.batch_alter_table('mailing_empfaenger', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_mailing_empfaenger_tracking_token'))
    op.drop_table('mailing_empfaenger')

    # Drop MailingZielgruppe table
    op.drop_table('mailing_zielgruppe')

    # Drop Mailing table
    op.drop_table('mailing')
