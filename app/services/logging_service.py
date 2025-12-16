"""Audit-Log Service for tracking important events.

Documented in PRD_BASIS_LOGGING.md.
"""
from typing import Optional
from app import db
from app.models import Modul, AuditLog


def log_event(
    modul: str,
    aktion: str,
    details: str = None,
    wichtigkeit: str = 'niedrig',
    entity_type: str = None,
    entity_id: int = None,
    user_id: int = None
) -> AuditLog:
    """Create an audit log entry.

    This function should be called within an existing database transaction.
    The caller is responsible for calling db.session.commit() after this function.

    Args:
        modul: Module code (e.g. 'kunden', 'system', 'auth')
        aktion: Action code (e.g. 'hauptbranche_geloescht', 'user_angelegt')
        details: Optional detailed description (human-readable)
        wichtigkeit: Importance level - 'niedrig', 'mittel', 'hoch', 'kritisch'
        entity_type: Optional type of affected entity (e.g. 'Kunde', 'Branche')
        entity_id: Optional ID of affected entity
        user_id: Optional user ID. If None, uses current_user.id if authenticated

    Returns:
        AuditLog: The created log entry

    Raises:
        ValueError: If the module code is unknown

    Example:
        ```python
        from app.services.logging_service import log_event

        # Simple log entry
        log_event('kunden', 'kunde_angelegt', details='Neuer Kunde "Firma XY"')

        # Full log entry with entity reference
        log_event(
            modul='kunden',
            aktion='hauptbranche_geloescht',
            details='Hauptbranche "HANDEL" und 5 Unterbranchen entfernt',
            wichtigkeit='mittel',
            entity_type='Kunde',
            entity_id=123
        )

        db.session.commit()
        ```
    """
    # Validate importance level
    valid_levels = ('niedrig', 'mittel', 'hoch', 'kritisch')
    if wichtigkeit not in valid_levels:
        wichtigkeit = 'niedrig'

    # Get module by code
    modul_obj = Modul.query.filter_by(code=modul).first()
    if not modul_obj:
        raise ValueError(f"Unknown module: {modul}")

    # Get user ID from current_user if not provided
    if user_id is None:
        try:
            from flask_login import current_user
            if current_user.is_authenticated:
                user_id = current_user.id
        except RuntimeError:
            # Outside of request context
            pass

    # Get IP address from request if available
    ip_adresse = None
    try:
        from flask import request
        if request:
            ip_adresse = request.remote_addr
    except RuntimeError:
        # Outside of request context
        pass

    # Create log entry
    log_entry = AuditLog(
        user_id=user_id,
        modul_id=modul_obj.id,
        aktion=aktion,
        details=details,
        wichtigkeit=wichtigkeit,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_adresse=ip_adresse
    )

    db.session.add(log_entry)

    return log_entry


def log_kritisch(modul: str, aktion: str, details: str = None, **kwargs) -> AuditLog:
    """Shortcut for logging critical events."""
    return log_event(modul, aktion, details, wichtigkeit='kritisch', **kwargs)


def log_hoch(modul: str, aktion: str, details: str = None, **kwargs) -> AuditLog:
    """Shortcut for logging high-importance events."""
    return log_event(modul, aktion, details, wichtigkeit='hoch', **kwargs)


def log_mittel(modul: str, aktion: str, details: str = None, **kwargs) -> AuditLog:
    """Shortcut for logging medium-importance events."""
    return log_event(modul, aktion, details, wichtigkeit='mittel', **kwargs)
