"""ChangelogEintrag model for project management (PRD-011).

A ChangelogEintrag documents a change to a component.
It can be automatically generated when a task is completed.
"""
from datetime import datetime
from enum import Enum
from app import db


class ChangelogKategorie(str, Enum):
    """Changelog categories following Keep a Changelog convention."""
    ADDED = 'added'        # New features
    CHANGED = 'changed'    # Changes to existing features
    FIXED = 'fixed'        # Bug fixes
    REMOVED = 'removed'    # Removed features

    @classmethod
    def choices(cls):
        """Return list of (value, label) tuples for form selects."""
        labels = {
            cls.ADDED: 'Added (Neu)',
            cls.CHANGED: 'Changed (Geändert)',
            cls.FIXED: 'Fixed (Behoben)',
            cls.REMOVED: 'Removed (Entfernt)',
        }
        return [(t.value, labels[t]) for t in cls]

    @classmethod
    def color_map(cls):
        """Return Bootstrap color classes for each category."""
        return {
            cls.ADDED.value: 'success',
            cls.CHANGED.value: 'info',
            cls.FIXED.value: 'warning',
            cls.REMOVED.value: 'danger',
        }


class ChangelogSichtbarkeit(str, Enum):
    """Visibility of changelog entries.

    INTERN: Only visible to admin/mitarbeiter
    OEFFENTLICH: Visible to customers (if component allows)
    """
    INTERN = 'intern'
    OEFFENTLICH = 'oeffentlich'

    @classmethod
    def choices(cls):
        """Return list of (value, label) tuples for form selects."""
        labels = {
            cls.INTERN: 'Intern (nur Mitarbeiter)',
            cls.OEFFENTLICH: 'Öffentlich (auch Kunden)',
        }
        return [(t.value, labels[t]) for t in cls]


class ChangelogEintrag(db.Model):
    """Represents a changelog entry for a component.

    Changelog entries document changes to components and can be:
    - Automatically generated when tasks are completed
    - Manually created for documentation purposes

    Visibility is determined by:
    1. Explicit sichtbarkeit field (override)
    2. Component's module access (if type='modul' and kunde has access)
    3. Default: intern
    """
    __tablename__ = 'changelog_eintrag'

    id = db.Column(db.Integer, primary_key=True)
    komponente_id = db.Column(db.Integer, db.ForeignKey('komponente.id'), nullable=False)

    # Optional link to triggering task
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)

    # Content
    version = db.Column(db.String(20), nullable=False)  # e.g., "POC", "MVP", "1.0.0"
    kategorie = db.Column(db.String(20), default=ChangelogKategorie.ADDED.value, nullable=False)
    beschreibung = db.Column(db.Text, nullable=False)

    # Visibility control
    sichtbarkeit = db.Column(
        db.String(20),
        default=ChangelogSichtbarkeit.INTERN.value,
        nullable=False
    )

    # Timestamps and author
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)
    erstellt_von = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Relationships
    erstellt_user = db.relationship('User', backref=db.backref('changelog_eintraege', lazy='dynamic'))

    def __repr__(self):
        return f'<ChangelogEintrag {self.version}: {self.beschreibung[:30]}>'

    @property
    def kategorie_color(self):
        """Return Bootstrap color class for category."""
        return ChangelogKategorie.color_map().get(self.kategorie, 'secondary')

    @property
    def ist_oeffentlich(self):
        """Check if entry should be publicly visible.

        Returns True if:
        - sichtbarkeit is 'oeffentlich' (explicit override), OR
        - Component is a module with customer access
        """
        if self.sichtbarkeit == ChangelogSichtbarkeit.OEFFENTLICH.value:
            return True

        # Check if component allows customer access
        if self.komponente and self.komponente.hat_kunde_zugriff():
            return True

        return False

    @property
    def erstellt_von_name(self):
        """Return name of creator or None."""
        if self.erstellt_user:
            return self.erstellt_user.full_name
        return None

    @classmethod
    def create_from_task(cls, task, kategorie=None, beschreibung=None, user_id=None):
        """Create a changelog entry from a completed task.

        Args:
            task: The completed Task object
            kategorie: Optional category override (default: ADDED)
            beschreibung: Optional description override (default: task title)
            user_id: ID of user creating the entry

        Returns:
            New ChangelogEintrag instance (not yet committed)
        """
        return cls(
            komponente_id=task.komponente_id,
            task_id=task.id,
            version=task.phase.upper(),  # Use phase as version
            kategorie=kategorie or ChangelogKategorie.ADDED.value,
            beschreibung=beschreibung or task.titel,
            sichtbarkeit=ChangelogSichtbarkeit.INTERN.value,  # Default to internal
            erstellt_von=user_id,
        )

    def to_dict(self):
        """Return dictionary representation."""
        return {
            'id': self.id,
            'komponente_id': self.komponente_id,
            'task_id': self.task_id,
            'version': self.version,
            'kategorie': self.kategorie,
            'kategorie_color': self.kategorie_color,
            'beschreibung': self.beschreibung,
            'sichtbarkeit': self.sichtbarkeit,
            'ist_oeffentlich': self.ist_oeffentlich,
            'erstellt_am': self.erstellt_am.isoformat() if self.erstellt_am else None,
            'erstellt_von': self.erstellt_von,
            'erstellt_von_name': self.erstellt_von_name,
        }

    def to_markdown(self):
        """Return entry as Markdown list item."""
        kategorie_prefix = {
            ChangelogKategorie.ADDED.value: '✨',
            ChangelogKategorie.CHANGED.value: '🔄',
            ChangelogKategorie.FIXED.value: '🐛',
            ChangelogKategorie.REMOVED.value: '🗑️',
        }
        prefix = kategorie_prefix.get(self.kategorie, '•')
        return f'- {prefix} {self.beschreibung}'
