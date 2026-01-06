"""TaskKommentar model for task comments (PRD011-T055).

TaskKommentar represents comments on tasks, enabling an iterative review workflow.
Comments can have different types (review, frage, hinweis, kommentar) and can be
marked as completed. Only non-completed review comments are included in the
review prompt generation.
"""
from datetime import datetime
from enum import Enum
from app import db


class KommentarTyp(str, Enum):
    """Types of task comments."""
    REVIEW = 'review'        # Review feedback - used for prompt generation
    FRAGE = 'frage'          # Questions
    HINWEIS = 'hinweis'      # General notes/hints
    KOMMENTAR = 'kommentar'  # Default comment

    @classmethod
    def choices(cls):
        """Return list of (value, label) tuples for form selects."""
        labels = {
            cls.REVIEW: 'Review',
            cls.FRAGE: 'Frage',
            cls.HINWEIS: 'Hinweis',
            cls.KOMMENTAR: 'Kommentar',
        }
        return [(t.value, labels[t]) for t in cls]


class TaskKommentar(db.Model):
    """A comment on a task.

    Comments support an iterative review workflow where users can add
    review feedback that is then processed and marked as completed.
    """
    __tablename__ = 'task_kommentar'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Comment content
    typ = db.Column(db.String(20), default=KommentarTyp.KOMMENTAR.value, nullable=False)
    inhalt = db.Column(db.Text, nullable=False)

    # V1: Completion status for review workflow
    erledigt = db.Column(db.Boolean, default=False, nullable=False)
    erledigt_am = db.Column(db.DateTime, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='task_kommentare')

    def __repr__(self):
        return f'<TaskKommentar {self.id} ({self.typ})>'

    @property
    def typ_icon(self):
        """Return Tabler icon for comment type."""
        icons = {
            'review': 'ti-eye-check',
            'frage': 'ti-help-circle',
            'hinweis': 'ti-bulb',
            'kommentar': 'ti-message',
        }
        return icons.get(self.typ, 'ti-message')

    @property
    def typ_farbe(self):
        """Return Bootstrap color for comment type."""
        colors = {
            'review': 'warning',
            'frage': 'info',
            'hinweis': 'secondary',
            'kommentar': 'light',
        }
        return colors.get(self.typ, 'light')

    @property
    def typ_label(self):
        """Return display label for comment type."""
        for value, label in KommentarTyp.choices():
            if value == self.typ:
                return label
        return self.typ

    def toggle_erledigt(self):
        """Toggle the completion status."""
        self.erledigt = not self.erledigt
        self.erledigt_am = datetime.utcnow() if self.erledigt else None

    def to_dict(self):
        """Return dictionary representation."""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'user_id': self.user_id,
            'user_name': self.user.vorname if self.user else 'System',
            'typ': self.typ,
            'typ_icon': self.typ_icon,
            'typ_farbe': self.typ_farbe,
            'typ_label': self.typ_label,
            'inhalt': self.inhalt,
            'erledigt': self.erledigt,
            'erledigt_am': self.erledigt_am.isoformat() if self.erledigt_am else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
