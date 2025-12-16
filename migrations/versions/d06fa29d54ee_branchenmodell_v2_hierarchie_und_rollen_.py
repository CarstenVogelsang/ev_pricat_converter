"""Branchenmodell V2: Hierarchie und Rollen-System

Diese Migration fuehrt das 2-stufige Branchenmodell mit Rollen ein:
1. Neue Tabellen: branchenrolle, branche_branchenrolle, kunde_branchenrolle
2. Erweiterung branche: uuid, parent_id (Hierarchie), slug
3. Datenmigration: HANDEL-Oberkategorie anlegen, bestehende Branchen einordnen
4. Datenmigration: Namen bereinigen (z.B. "Einzelhandel Spielwaren" -> "Spielwaren")
5. Initiale Rollen anlegen und Zulaessigkeitsmatrix befuellen

Revision ID: d06fa29d54ee
Revises: 18e97dddcbd2
Create Date: 2025-12-12 13:24:08.339509
"""
from uuid import uuid4
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd06fa29d54ee'
down_revision = '18e97dddcbd2'
branch_labels = None
depends_on = None


# Mapping fuer Namensbereinigung: alter Name -> neuer Name
NAME_BEREINIGUNG = {
    'Einzelhandel Spielwaren': 'Spielwaren',
    'Einzelhandel Modellbahn': 'Modellbahn',
    'Einzelhandel Fahrrad': 'Fahrrad',
    'Einzelhandel Buchhandel': 'Buchhandel',
    'Einzelhandel Baby': 'Baby',
    'Einzelhandel Schreibwaren': 'Schreibwaren',
    'Einzelhandel (allgemein)': 'Allgemein',
    'Großhandel (allgemein)': 'Großhandel',
    'Hersteller IT Software': 'IT Software',
}

# Initiale BranchenRollen
INITIALE_ROLLEN = [
    ('HERSTELLER', 'Hersteller', 'building-factory', 'Produziert eigene Produkte', 10),
    ('GROSSHAENDLER', 'Großhändler', 'truck-delivery', 'Vertreibt an Wiederverkäufer', 20),
    ('FILIALIST', 'Filialist', 'buildings', 'Betreibt mehrere Filialen', 30),
    ('EINZELHANDEL_STATIONAER', 'Einzelhandel (stationär)', 'building-store', 'Ladengeschäft', 40),
    ('EINZELHANDEL_ONLINE', 'Einzelhandel (online)', 'shopping-cart', 'Reiner Online-Shop', 50),
    ('EINZELHANDEL_OMNICHANNEL', 'Einzelhandel (omnichannel)', 'device-desktop', 'Stationär + Online', 60),
]


def upgrade():
    # ==========================================================================
    # SCHRITT 1: Neue Tabellen erstellen
    # ==========================================================================

    # Tabelle branchenrolle (Rollen-Katalog)
    op.create_table('branchenrolle',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('beschreibung', sa.Text(), nullable=True),
        sa.Column('aktiv', sa.Boolean(), nullable=True),
        sa.Column('sortierung', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
        sa.UniqueConstraint('uuid')
    )

    # Tabelle branche_branchenrolle (Zulaessigkeitsmatrix)
    op.create_table('branche_branchenrolle',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('branche_id', sa.Integer(), nullable=False),
        sa.Column('branchenrolle_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['branche_id'], ['branche.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['branchenrolle_id'], ['branchenrolle.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('branche_id', 'branchenrolle_id', name='uq_branche_branchenrolle')
    )

    # Tabelle kunde_branchenrolle (Kunde-Branche-Rolle Zuordnung)
    op.create_table('kunde_branchenrolle',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('kunde_id', sa.Integer(), nullable=False),
        sa.Column('branche_id', sa.Integer(), nullable=False),
        sa.Column('branchenrolle_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['branche_id'], ['branche.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['branchenrolle_id'], ['branchenrolle.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['kunde_id'], ['kunde.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('kunde_id', 'branche_id', 'branchenrolle_id', name='uq_kunde_branche_branchenrolle')
    )

    # ==========================================================================
    # SCHRITT 2: branche-Tabelle erweitern (Spalten hinzufuegen)
    # ==========================================================================

    with op.batch_alter_table('branche', schema=None) as batch_op:
        # uuid erst als nullable, dann nach Datenmigration auf NOT NULL setzen
        batch_op.add_column(sa.Column('uuid', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('parent_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('slug', sa.String(length=100), nullable=True))

    # ==========================================================================
    # SCHRITT 3: Datenmigration - UUIDs fuer bestehende Branchen generieren
    # ==========================================================================

    connection = op.get_bind()

    # Alle bestehenden Branchen holen
    branchen = connection.execute(sa.text("SELECT id FROM branche")).fetchall()

    # UUID fuer jede Branche generieren
    for branche in branchen:
        connection.execute(
            sa.text("UPDATE branche SET uuid = :uuid WHERE id = :id"),
            {'uuid': str(uuid4()), 'id': branche[0]}
        )

    # ==========================================================================
    # SCHRITT 4: Datenmigration - Oberkategorie HANDEL anlegen
    # ==========================================================================

    # HANDEL-Oberkategorie anlegen
    handel_uuid = str(uuid4())
    connection.execute(
        sa.text("""
            INSERT INTO branche (name, icon, aktiv, sortierung, uuid, parent_id, slug)
            VALUES ('HANDEL', 'building-store', 1, 0, :uuid, NULL, 'handel')
        """),
        {'uuid': handel_uuid}
    )

    # ID der HANDEL-Oberkategorie ermitteln
    handel_id = connection.execute(
        sa.text("SELECT id FROM branche WHERE name = 'HANDEL' AND parent_id IS NULL")
    ).fetchone()[0]

    # ==========================================================================
    # SCHRITT 5: Datenmigration - Bestehende Branchen unter HANDEL einordnen
    # ==========================================================================

    # Alle Branchen (ausser HANDEL) der HANDEL-Oberkategorie zuordnen
    connection.execute(
        sa.text("""
            UPDATE branche
            SET parent_id = :handel_id
            WHERE parent_id IS NULL AND name != 'HANDEL'
        """),
        {'handel_id': handel_id}
    )

    # ==========================================================================
    # SCHRITT 6: Datenmigration - Namen bereinigen
    # ==========================================================================

    for alter_name, neuer_name in NAME_BEREINIGUNG.items():
        connection.execute(
            sa.text("UPDATE branche SET name = :neuer_name WHERE name = :alter_name"),
            {'neuer_name': neuer_name, 'alter_name': alter_name}
        )

    # Slugs fuer alle Unterbranchen generieren
    unterbranchen = connection.execute(
        sa.text("SELECT id, name FROM branche WHERE parent_id IS NOT NULL")
    ).fetchall()

    for branche in unterbranchen:
        slug = 'handel-' + branche[1].lower().replace(' ', '-').replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
        connection.execute(
            sa.text("UPDATE branche SET slug = :slug WHERE id = :id"),
            {'slug': slug, 'id': branche[0]}
        )

    # ==========================================================================
    # SCHRITT 7: Constraints setzen (uuid NOT NULL, unique parent+name)
    # ==========================================================================

    with op.batch_alter_table('branche', schema=None) as batch_op:
        # uuid auf NOT NULL setzen (da jetzt alle Daten haben)
        batch_op.alter_column('uuid', nullable=False)
        # Unique Constraints
        batch_op.create_unique_constraint('uq_branche_uuid', ['uuid'])
        batch_op.create_unique_constraint('uq_branche_parent_name', ['parent_id', 'name'])
        # Foreign Key fuer Self-Reference
        batch_op.create_foreign_key('fk_branche_parent', 'branche', ['parent_id'], ['id'])

    # SQLite: Da der urspruengliche UNIQUE-Constraint auf 'name' keinen Namen hat,
    # wird er automatisch durch batch_alter_table entfernt, wenn wir die Tabelle
    # neu erstellen. Der neue Constraint uq_branche_parent_name ersetzt ihn.

    # ==========================================================================
    # SCHRITT 8: Initiale BranchenRollen anlegen
    # ==========================================================================

    for code, name, icon, beschreibung, sortierung in INITIALE_ROLLEN:
        connection.execute(
            sa.text("""
                INSERT INTO branchenrolle (uuid, code, name, icon, beschreibung, aktiv, sortierung)
                VALUES (:uuid, :code, :name, :icon, :beschreibung, 1, :sortierung)
            """),
            {
                'uuid': str(uuid4()),
                'code': code,
                'name': name,
                'icon': icon,
                'beschreibung': beschreibung,
                'sortierung': sortierung
            }
        )

    # ==========================================================================
    # SCHRITT 9: Zulaessigkeitsmatrix befuellen (alle Rollen fuer alle Unterbranchen)
    # ==========================================================================

    # Alle Unterbranche-IDs (parent_id != NULL)
    unterbranchen = connection.execute(
        sa.text("SELECT id FROM branche WHERE parent_id IS NOT NULL")
    ).fetchall()

    # Alle Rollen-IDs
    rollen = connection.execute(
        sa.text("SELECT id FROM branchenrolle")
    ).fetchall()

    # Fuer jede Unterbranche alle Rollen als zulaessig markieren
    for branche in unterbranchen:
        for rolle in rollen:
            connection.execute(
                sa.text("""
                    INSERT INTO branche_branchenrolle (branche_id, branchenrolle_id)
                    VALUES (:branche_id, :rolle_id)
                """),
                {'branche_id': branche[0], 'rolle_id': rolle[0]}
            )


def downgrade():
    # ==========================================================================
    # ACHTUNG: Downgrade ist destruktiv! Datenmigration wird nicht rueckgaengig gemacht.
    # ==========================================================================

    # Tabellen loeschen
    op.drop_table('kunde_branchenrolle')
    op.drop_table('branche_branchenrolle')
    op.drop_table('branchenrolle')

    # branche-Spalten entfernen
    with op.batch_alter_table('branche', schema=None) as batch_op:
        batch_op.drop_constraint('fk_branche_parent', type_='foreignkey')
        batch_op.drop_constraint('uq_branche_uuid', type_='unique')
        batch_op.drop_constraint('uq_branche_parent_name', type_='unique')
        batch_op.drop_column('slug')
        batch_op.drop_column('parent_id')
        batch_op.drop_column('uuid')

    # Alten unique constraint auf name wiederherstellen
    with op.batch_alter_table('branche', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_branche_name', ['name'])
