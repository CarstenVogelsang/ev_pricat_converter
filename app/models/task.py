"""Task model for project management (PRD-011).

A Task represents a work item within a component.
Tasks have a status (Kanban columns) and can be assigned to users.
"""
from datetime import datetime
from enum import Enum
from app import db


class TaskStatus(str, Enum):
    """Task status representing Kanban columns."""
    BACKLOG = 'backlog'        # Not yet planned
    GEPLANT = 'geplant'        # Planned for implementation
    IN_ARBEIT = 'in_arbeit'    # Currently being worked on
    REVIEW = 'review'          # In review
    ERLEDIGT = 'erledigt'      # Completed

    @classmethod
    def choices(cls):
        """Return list of (value, label) tuples for form selects."""
        labels = {
            cls.BACKLOG: 'Backlog',
            cls.GEPLANT: 'Geplant',
            cls.IN_ARBEIT: 'In Arbeit',
            cls.REVIEW: 'Review',
            cls.ERLEDIGT: 'Erledigt',
        }
        return [(t.value, labels[t]) for t in cls]

    @classmethod
    def kanban_order(cls):
        """Return status values in Kanban board order."""
        return [cls.BACKLOG, cls.GEPLANT, cls.IN_ARBEIT, cls.REVIEW, cls.ERLEDIGT]


class TaskPrioritaet(str, Enum):
    """Task priority levels."""
    NIEDRIG = 'niedrig'
    MITTEL = 'mittel'
    HOCH = 'hoch'
    KRITISCH = 'kritisch'

    @classmethod
    def choices(cls):
        """Return list of (value, label) tuples for form selects."""
        labels = {
            cls.NIEDRIG: 'Niedrig',
            cls.MITTEL: 'Mittel',
            cls.HOCH: 'Hoch',
            cls.KRITISCH: 'Kritisch',
        }
        return [(t.value, labels[t]) for t in cls]

    @classmethod
    def color_map(cls):
        """Return Bootstrap color classes for each priority."""
        return {
            cls.NIEDRIG.value: 'secondary',
            cls.MITTEL.value: 'info',
            cls.HOCH.value: 'warning',
            cls.KRITISCH.value: 'danger',
        }


class TaskPhase(str, Enum):
    """Development phase for tasks."""
    POC = 'poc'
    MVP = 'mvp'
    V1 = 'v1'
    V2 = 'v2'
    V3 = 'v3'

    @classmethod
    def choices(cls):
        """Return list of (value, label) tuples for form selects."""
        labels = {
            cls.POC: 'POC',
            cls.MVP: 'MVP',
            cls.V1: 'V1',
            cls.V2: 'V2',
            cls.V3: 'V3',
        }
        return [(t.value, labels[t]) for t in cls]


class Task(db.Model):
    """Represents a task/work item within a component.

    Tasks are displayed on a Kanban board and can be filtered by phase.
    Completing a task can automatically generate a changelog entry.
    """
    __tablename__ = 'task'

    id = db.Column(db.Integer, primary_key=True)
    komponente_id = db.Column(db.Integer, db.ForeignKey('komponente.id'), nullable=False)

    # Content
    titel = db.Column(db.String(200), nullable=False)
    beschreibung = db.Column(db.Text, nullable=True)

    # Classification
    phase = db.Column(db.String(10), default=TaskPhase.POC.value, nullable=False)
    status = db.Column(db.String(20), default=TaskStatus.BACKLOG.value, nullable=False)
    prioritaet = db.Column(db.String(20), default=TaskPrioritaet.MITTEL.value, nullable=False)
    typ = db.Column(db.String(30), default='funktion', nullable=False)  # Task type from LookupWert

    # Assignment (optional)
    zugewiesen_an = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Kanban ordering
    sortierung = db.Column(db.Integer, default=0)

    # Changelog settings
    create_changelog_on_complete = db.Column(db.Boolean, default=True)

    # Archivierung (PRD011-T030)
    ist_archiviert = db.Column(db.Boolean, default=False, nullable=False)

    # Referenz auf Ursprungs-Task bei Task-Splitting (PRD011-T041)
    entstanden_aus_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    erledigt_am = db.Column(db.DateTime, nullable=True)

    # Relationships
    zugewiesen_user = db.relationship('User', backref=db.backref('zugewiesene_tasks', lazy='dynamic'))
    changelog_eintraege = db.relationship(
        'ChangelogEintrag',
        backref='task',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    # Task-Kommentare für Review-Workflow (PRD011-T055)
    kommentare = db.relationship(
        'TaskKommentar',
        backref='task',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='TaskKommentar.created_at.desc()'
    )
    # Self-referential relationship für Task-Splitting (PRD011-T041)
    entstanden_aus = db.relationship(
        'Task',
        remote_side=[id],
        backref=db.backref('abgeleitete_tasks', lazy='dynamic'),
        foreign_keys=[entstanden_aus_id]
    )

    def __repr__(self):
        return f'<Task {self.id}: {self.titel[:30]}>'

    @property
    def ist_erledigt(self):
        """Check if task is completed."""
        return self.status == TaskStatus.ERLEDIGT.value

    @property
    def prioritaet_color(self):
        """Return Bootstrap color class for priority."""
        return TaskPrioritaet.color_map().get(self.prioritaet, 'secondary')

    @property
    def prioritaet_badge(self):
        """Return full Bootstrap badge class for priority."""
        color = self.prioritaet_color
        if color == 'warning':
            return f'bg-{color} text-dark'
        return f'bg-{color}'

    @property
    def zugewiesen(self):
        """Return assigned user (alias for zugewiesen_user)."""
        return self.zugewiesen_user

    @property
    def zugewiesen_name(self):
        """Return name of assigned user or None."""
        if self.zugewiesen_user:
            return self.zugewiesen_user.full_name
        return None

    @property
    def typ_icon(self):
        """Return Tabler icon for task type from LookupWert."""
        from app.models import LookupWert
        return LookupWert.get_icon('task_typ', self.typ, 'ti-help')

    @property
    def typ_farbe(self):
        """Return Bootstrap color for task type from LookupWert."""
        from app.models import LookupWert
        return LookupWert.get_farbe('task_typ', self.typ, 'secondary')

    @property
    def typ_label(self):
        """Return display label for task type from LookupWert."""
        from app.models import LookupWert
        label = LookupWert.get_wert('task_typ', self.typ)
        return label if label else self.typ

    @property
    def typ_beschreibung(self):
        """Return description for task type (PRD011-T032).

        Used for generating AI prompts with context about the task type.
        """
        beschreibungen = {
            'funktion': 'Neuentwicklung einer fachlichen oder technischen Funktion',
            'verbesserung': 'Optimierung bestehender Funktionen (UX, Performance)',
            'fehlerbehebung': 'Behebung eines reproduzierbaren Fehlers',
            'technisch': 'Refactoring, Architektur, Infrastruktur',
            'sicherheit': 'Zugriffskontrolle, Datenschutz, Sicherheitslücken',
            'recherche': 'Analyse- oder Evaluierungsaufgabe',
            'dokumentation': 'Benutzer- oder Entwickler-Dokumentation',
            'test': 'Tests, Testkonzepte, manuelle Prüfungen',
        }
        return beschreibungen.get(self.typ, '')

    @property
    def task_nummer(self):
        """Return readable task ID in format PRD{prd_nummer}-T{id:03d}.

        Example: PRD011-T023 for task 23 in component PRD-011.
        Falls back to T{id:03d} if component has no PRD number.
        """
        if self.komponente and self.komponente.prd_nummer:
            return f"PRD{self.komponente.prd_nummer}-T{self.id:03d}"
        return f"T{self.id:03d}"

    @property
    def entstanden_aus_nummer(self):
        """Return task_nummer of parent task if exists (PRD011-T041)."""
        if self.entstanden_aus:
            return self.entstanden_aus.task_nummer
        return None

    @property
    def anzahl_abgeleitete(self):
        """Return count of derived tasks (PRD011-T041)."""
        return self.abgeleitete_tasks.count()

    @property
    def review_kommentare(self):
        """Return only NON-COMPLETED review comments for prompt generation (PRD011-T055)."""
        return self.kommentare.filter_by(typ='review', erledigt=False).all()

    @property
    def offene_review_kommentare(self):
        """Return count of open review comments (PRD011-T055)."""
        return self.kommentare.filter_by(typ='review', erledigt=False).count()

    @property
    def anzahl_kommentare(self):
        """Return total comment count (PRD011-T055)."""
        return self.kommentare.count()

    def erledigen(self, user_id=None):
        """Mark task as completed and set completion timestamp.

        Args:
            user_id: Optional user ID who completed the task

        Returns:
            True if status was changed, False if already completed
        """
        if self.ist_erledigt:
            return False

        self.status = TaskStatus.ERLEDIGT.value
        self.erledigt_am = datetime.utcnow()
        return True

    def to_dict(self, include_beschreibung=False):
        """Return dictionary representation.

        Args:
            include_beschreibung: If True, include full description
        """
        result = {
            'id': self.id,
            'task_nummer': self.task_nummer,
            'komponente_id': self.komponente_id,
            'titel': self.titel,
            'phase': self.phase,
            'status': self.status,
            'prioritaet': self.prioritaet,
            'prioritaet_color': self.prioritaet_color,
            'prioritaet_badge': self.prioritaet_badge,
            'typ': self.typ,
            'typ_icon': self.typ_icon,
            'typ_farbe': self.typ_farbe,
            'typ_label': self.typ_label,
            'zugewiesen_an': self.zugewiesen_an,
            'zugewiesen_name': self.zugewiesen_name,
            'sortierung': self.sortierung,
            'ist_erledigt': self.ist_erledigt,
            'ist_archiviert': self.ist_archiviert,
            'entstanden_aus_id': self.entstanden_aus_id,
            'entstanden_aus_nummer': self.entstanden_aus_nummer,
            'anzahl_abgeleitete': self.anzahl_abgeleitete,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'erledigt_am': self.erledigt_am.isoformat() if self.erledigt_am else None,
        }
        if include_beschreibung:
            result['beschreibung'] = self.beschreibung
        return result
