"""LookupWert model for generic key-value configuration storage.

This model provides a flexible way to store configuration values that can be
extended without schema changes. Use cases:
- Email salutation patterns (anrede_foermlich, anrede_locker)
- Support ticket types, status, priorities with icons and colors
- Any enum-like values that should be admin-configurable
"""
from typing import Optional

from app import db


class LookupWert(db.Model):
    """Generic key-value storage for configuration values.

    Used for extensible configuration without schema changes.

    Attributes:
        kategorie: Category/namespace (e.g., 'support_typ', 'support_status')
        schluessel: Key within category (e.g., 'bug', 'offen')
        wert: Display label (e.g., 'Fehlermeldung', 'Offen')
        icon: Tabler icon class (e.g., 'ti-bug', 'ti-clock')
        farbe: Bootstrap color class (e.g., 'danger', 'warning')
        modul_id: Optional FK to modul table for filtering
        sortierung: Sort order within category
        aktiv: Whether this entry is active
    """
    __tablename__ = 'lookup_wert'

    id = db.Column(db.Integer, primary_key=True)
    kategorie = db.Column(db.String(50), nullable=False, index=True)
    schluessel = db.Column(db.String(50), nullable=False)
    wert = db.Column(db.String(255), nullable=False)
    icon = db.Column(db.String(50), nullable=True)  # Tabler icon class
    farbe = db.Column(db.String(20), nullable=True)  # Bootstrap color
    modul_id = db.Column(db.Integer, db.ForeignKey('modul.id'), nullable=True)
    sortierung = db.Column(db.Integer, default=0)
    aktiv = db.Column(db.Boolean, default=True, nullable=False)

    # Relationship
    modul = db.relationship('Modul', backref='lookup_werte')

    __table_args__ = (
        db.UniqueConstraint('kategorie', 'schluessel', name='uq_lookup_kategorie_schluessel'),
    )

    def __repr__(self) -> str:
        return f'<LookupWert {self.kategorie}.{self.schluessel}>'

    @classmethod
    def get_wert(cls, kategorie: str, schluessel: str) -> Optional[str]:
        """Get a single value by category and key.

        Args:
            kategorie: The category/namespace
            schluessel: The key within the category

        Returns:
            The value string, or None if not found or inactive
        """
        lw = cls.query.filter_by(
            kategorie=kategorie,
            schluessel=schluessel,
            aktiv=True
        ).first()
        return lw.wert if lw else None

    @classmethod
    def get_entry(cls, kategorie: str, schluessel: str) -> Optional['LookupWert']:
        """Get a single entry by category and key.

        Args:
            kategorie: The category/namespace
            schluessel: The key within the category

        Returns:
            The LookupWert entry, or None if not found or inactive
        """
        return cls.query.filter_by(
            kategorie=kategorie,
            schluessel=schluessel,
            aktiv=True
        ).first()

    @classmethod
    def get_icon(cls, kategorie: str, schluessel: str, default: str = 'ti-help') -> str:
        """Get icon for a category/key combination.

        Args:
            kategorie: The category/namespace
            schluessel: The key within the category
            default: Default icon if not found

        Returns:
            The icon class (always prefixed with 'ti ')
        """
        lw = cls.get_entry(kategorie, schluessel)
        icon = lw.icon if lw and lw.icon else default
        # Ensure 'ti ' prefix for Tabler icons
        if icon and not icon.startswith('ti '):
            icon = f'ti {icon}'
        return icon

    @classmethod
    def get_farbe(cls, kategorie: str, schluessel: str, default: str = 'secondary') -> str:
        """Get color for a category/key combination.

        Args:
            kategorie: The category/namespace
            schluessel: The key within the category
            default: Default color if not found

        Returns:
            The Bootstrap color class
        """
        lw = cls.get_entry(kategorie, schluessel)
        return lw.farbe if lw and lw.farbe else default

    @classmethod
    def get_by_kategorie(cls, kategorie: str) -> list['LookupWert']:
        """Get all active values for a category.

        Args:
            kategorie: The category/namespace

        Returns:
            List of LookupWert entries, sorted by sortierung
        """
        return cls.query.filter_by(
            kategorie=kategorie,
            aktiv=True
        ).order_by(cls.sortierung).all()

    @classmethod
    def get_choices(cls, kategorie: str) -> list[tuple[str, str]]:
        """Get choices for a form select field.

        Args:
            kategorie: The category/namespace

        Returns:
            List of (schluessel, wert) tuples for form selects
        """
        entries = cls.get_by_kategorie(kategorie)
        return [(e.schluessel, e.wert) for e in entries]

    @classmethod
    def get_kategorien(cls) -> list[str]:
        """Get all unique categories.

        Returns:
            List of unique category names
        """
        result = db.session.query(cls.kategorie).distinct().order_by(cls.kategorie).all()
        return [r[0] for r in result]
