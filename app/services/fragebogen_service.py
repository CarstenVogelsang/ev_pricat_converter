"""Fragebogen Service for questionnaire management.

Handles:
- Fragebogen CRUD operations
- JSON definition validation
- Teilnehmer (participant) management
- Einladungs-E-Mail sending
- Antwort (answer) storage
- Auswertung (statistics)
"""
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from app import db
from app.models import (
    Fragebogen, FragebogenTeilnahme, FragebogenAntwort,
    FragebogenStatus, TeilnahmeStatus, Kunde
)
from app.services.email_service import get_brevo_service, EmailResult


# Valid question types
VALID_FRAGE_TYPEN = ['single_choice', 'multiple_choice', 'skala', 'text', 'ja_nein']


@dataclass
class ValidationResult:
    """Result of JSON definition validation."""
    valid: bool
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@dataclass
class EinladungResult:
    """Result of sending invitations."""
    success: bool
    sent_count: int = 0
    failed_count: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class FragebogenService:
    """Service for managing Fragebögen (questionnaires)."""

    def validate_definition(self, definition: Dict[str, Any]) -> ValidationResult:
        """Validate a Fragebogen JSON definition.

        Expected schema:
        {
            "fragen": [
                {
                    "id": "q1",
                    "typ": "single_choice|multiple_choice|skala|text|ja_nein",
                    "frage": "Question text",
                    "optionen": [...],  # for choice types
                    "min": 1, "max": 5,  # for skala
                    "pflicht": true
                }
            ]
        }

        Args:
            definition: The JSON definition dict

        Returns:
            ValidationResult with valid flag and errors
        """
        errors = []

        if not isinstance(definition, dict):
            return ValidationResult(valid=False, errors=['Definition muss ein Objekt sein'])

        if 'fragen' not in definition:
            return ValidationResult(valid=False, errors=['Feld "fragen" fehlt'])

        fragen = definition['fragen']
        if not isinstance(fragen, list):
            return ValidationResult(valid=False, errors=['"fragen" muss eine Liste sein'])

        if len(fragen) == 0:
            return ValidationResult(valid=False, errors=['Mindestens eine Frage erforderlich'])

        seen_ids = set()

        for i, frage in enumerate(fragen):
            prefix = f'Frage {i + 1}'

            if not isinstance(frage, dict):
                errors.append(f'{prefix}: Muss ein Objekt sein')
                continue

            # Required fields
            if 'id' not in frage:
                errors.append(f'{prefix}: Feld "id" fehlt')
            elif frage['id'] in seen_ids:
                errors.append(f'{prefix}: ID "{frage["id"]}" ist doppelt')
            else:
                seen_ids.add(frage['id'])

            if 'typ' not in frage:
                errors.append(f'{prefix}: Feld "typ" fehlt')
            elif frage['typ'] not in VALID_FRAGE_TYPEN:
                errors.append(f'{prefix}: Ungültiger Typ "{frage["typ"]}"')

            if 'frage' not in frage:
                errors.append(f'{prefix}: Feld "frage" (Fragetext) fehlt')

            # Type-specific validation
            typ = frage.get('typ')

            if typ in ['single_choice', 'multiple_choice']:
                if 'optionen' not in frage:
                    errors.append(f'{prefix}: Feld "optionen" fehlt für {typ}')
                elif not isinstance(frage['optionen'], list) or len(frage['optionen']) < 2:
                    errors.append(f'{prefix}: Mindestens 2 Optionen erforderlich')

            if typ == 'skala':
                if 'min' not in frage or 'max' not in frage:
                    errors.append(f'{prefix}: Felder "min" und "max" erforderlich für Skala')
                elif not isinstance(frage.get('min'), int) or not isinstance(frage.get('max'), int):
                    errors.append(f'{prefix}: "min" und "max" müssen Zahlen sein')
                elif frage['min'] >= frage['max']:
                    errors.append(f'{prefix}: "min" muss kleiner als "max" sein')

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def create_fragebogen(self, titel: str, beschreibung: str,
                          definition: Dict[str, Any], erstellt_von_id: int) -> Fragebogen:
        """Create a new Fragebogen.

        Args:
            titel: Title of the questionnaire
            beschreibung: Description
            definition: JSON definition with questions
            erstellt_von_id: Creator user ID

        Returns:
            Created Fragebogen instance
        """
        fragebogen = Fragebogen(
            titel=titel,
            beschreibung=beschreibung,
            definition_json=definition,
            status=FragebogenStatus.ENTWURF.value,
            erstellt_von_id=erstellt_von_id
        )
        db.session.add(fragebogen)
        db.session.commit()
        return fragebogen

    def update_fragebogen(self, fragebogen: Fragebogen, titel: str = None,
                          beschreibung: str = None, definition: Dict[str, Any] = None) -> Fragebogen:
        """Update a Fragebogen (only in ENTWURF status).

        Args:
            fragebogen: The Fragebogen to update
            titel: New title (optional)
            beschreibung: New description (optional)
            definition: New JSON definition (optional)

        Returns:
            Updated Fragebogen

        Raises:
            ValueError: If Fragebogen is not in ENTWURF status
        """
        if not fragebogen.is_entwurf:
            raise ValueError('Fragebogen kann nur im Entwurf-Status bearbeitet werden')

        if titel is not None:
            fragebogen.titel = titel
        if beschreibung is not None:
            fragebogen.beschreibung = beschreibung
        if definition is not None:
            fragebogen.definition_json = definition

        db.session.commit()
        return fragebogen

    def add_teilnehmer(self, fragebogen: Fragebogen, kunde: Kunde) -> FragebogenTeilnahme:
        """Add a Kunde as participant to a Fragebogen.

        Args:
            fragebogen: The Fragebogen
            kunde: The Kunde to add

        Returns:
            Created FragebogenTeilnahme

        Raises:
            ValueError: If Kunde has no user or is already added
        """
        if not kunde.user_id:
            raise ValueError(f'Kunde "{kunde.firmierung}" hat keinen User-Account')

        # Check if already exists
        existing = FragebogenTeilnahme.query.filter_by(
            fragebogen_id=fragebogen.id,
            kunde_id=kunde.id
        ).first()

        if existing:
            raise ValueError(f'Kunde "{kunde.firmierung}" ist bereits Teilnehmer')

        teilnahme = FragebogenTeilnahme.create_for_kunde(
            fragebogen_id=fragebogen.id,
            kunde_id=kunde.id
        )
        db.session.add(teilnahme)
        db.session.commit()
        return teilnahme

    def remove_teilnehmer(self, teilnahme: FragebogenTeilnahme):
        """Remove a participant (only if EINGELADEN and no email sent).

        Args:
            teilnahme: The participation to remove

        Raises:
            ValueError: If participation cannot be removed
        """
        if teilnahme.einladung_gesendet_am:
            raise ValueError('Teilnehmer hat bereits eine Einladung erhalten')
        if not teilnahme.is_eingeladen:
            raise ValueError('Teilnehmer hat bereits begonnen')

        db.session.delete(teilnahme)
        db.session.commit()

    def send_einladungen(self, fragebogen: Fragebogen,
                         teilnahmen: List[FragebogenTeilnahme] = None) -> EinladungResult:
        """Send invitation emails to participants.

        Args:
            fragebogen: The Fragebogen
            teilnahmen: Specific participations to send to (optional, defaults to all unsent)

        Returns:
            EinladungResult with counts
        """
        if not fragebogen.is_aktiv:
            return EinladungResult(
                success=False,
                errors=['Fragebogen muss aktiv sein um Einladungen zu senden']
            )

        brevo = get_brevo_service()
        if not brevo.is_configured:
            return EinladungResult(
                success=False,
                errors=['E-Mail-Service (Brevo) ist nicht konfiguriert']
            )

        # Get participants to invite
        if teilnahmen is None:
            teilnahmen = [t for t in fragebogen.teilnahmen
                          if t.einladung_gesendet_am is None]

        if not teilnahmen:
            return EinladungResult(
                success=True,
                sent_count=0,
                errors=['Keine Teilnehmer zum Einladen gefunden']
            )

        sent_count = 0
        failed_count = 0
        errors = []

        for teilnahme in teilnahmen:
            kunde = teilnahme.kunde
            user = kunde.user

            if not user:
                errors.append(f'{kunde.firmierung}: Kein User-Account')
                failed_count += 1
                continue

            result = brevo.send_fragebogen_einladung(
                to_email=user.email,
                to_name=user.full_name,
                fragebogen_titel=fragebogen.titel,
                magic_token=teilnahme.token,
                kunde_firmierung=kunde.firmierung
            )

            if result.success:
                teilnahme.einladung_gesendet_am = datetime.utcnow()
                sent_count += 1
            else:
                errors.append(f'{kunde.firmierung}: {result.error}')
                failed_count += 1

        db.session.commit()

        return EinladungResult(
            success=failed_count == 0,
            sent_count=sent_count,
            failed_count=failed_count,
            errors=errors if errors else None
        )

    def get_teilnahme_by_token(self, token: str) -> Optional[FragebogenTeilnahme]:
        """Get a participation by its magic-link token.

        Args:
            token: The magic-link token

        Returns:
            FragebogenTeilnahme or None
        """
        return FragebogenTeilnahme.query.filter_by(token=token).first()

    def save_antwort(self, teilnahme: FragebogenTeilnahme,
                     frage_id: str, antwort_json: Dict[str, Any]) -> FragebogenAntwort:
        """Save or update an answer for a question.

        Args:
            teilnahme: The participation
            frage_id: The question ID
            antwort_json: The answer data

        Returns:
            The created/updated FragebogenAntwort

        Raises:
            ValueError: If Fragebogen is not active or already completed
        """
        if not teilnahme.fragebogen.is_aktiv:
            raise ValueError('Fragebogen ist nicht mehr aktiv')

        if teilnahme.is_abgeschlossen:
            raise ValueError('Teilnahme ist bereits abgeschlossen')

        # Start participation if not yet started
        if teilnahme.is_eingeladen:
            teilnahme.starten()

        # Check if answer exists
        antwort = FragebogenAntwort.query.filter_by(
            teilnahme_id=teilnahme.id,
            frage_id=frage_id
        ).first()

        if antwort:
            antwort.antwort_json = antwort_json
        else:
            antwort = FragebogenAntwort(
                teilnahme_id=teilnahme.id,
                frage_id=frage_id,
                antwort_json=antwort_json
            )
            db.session.add(antwort)

        db.session.commit()
        return antwort

    def complete_teilnahme(self, teilnahme: FragebogenTeilnahme) -> bool:
        """Mark a participation as completed.

        Validates that all required questions are answered.

        Args:
            teilnahme: The participation to complete

        Returns:
            True if completed successfully

        Raises:
            ValueError: If required questions are not answered
        """
        fragebogen = teilnahme.fragebogen

        # Check required questions
        missing = []
        for frage in fragebogen.fragen:
            if frage.get('pflicht', False):
                antwort = teilnahme.get_antwort(frage['id'])
                if not antwort or not antwort.value:
                    missing.append(frage.get('frage', frage['id']))

        if missing:
            raise ValueError(f'Pflichtfragen nicht beantwortet: {", ".join(missing[:3])}...')

        teilnahme.abschliessen()
        db.session.commit()
        return True

    def get_auswertung(self, fragebogen: Fragebogen) -> Dict[str, Any]:
        """Get statistics and summary for a Fragebogen.

        Args:
            fragebogen: The Fragebogen

        Returns:
            Dict with statistics per question
        """
        auswertung = {
            'fragebogen_id': fragebogen.id,
            'titel': fragebogen.titel,
            'status': fragebogen.status,
            'teilnehmer_gesamt': fragebogen.anzahl_teilnehmer,
            'teilnehmer_abgeschlossen': fragebogen.anzahl_abgeschlossen,
            'fragen': []
        }

        # Get all completed answers
        abgeschlossene = [t for t in fragebogen.teilnahmen if t.is_abgeschlossen]

        for frage in fragebogen.fragen:
            frage_stats = {
                'id': frage['id'],
                'typ': frage['typ'],
                'frage': frage['frage'],
                'antworten_count': 0,
                'statistik': {}
            }

            # Collect answers for this question
            answers = []
            for teilnahme in abgeschlossene:
                antwort = teilnahme.get_antwort(frage['id'])
                if antwort and antwort.value is not None:
                    answers.append(antwort.value)
                    frage_stats['antworten_count'] += 1

            # Calculate statistics based on type
            if frage['typ'] in ['single_choice', 'ja_nein']:
                # Count each option
                counts = {}
                for a in answers:
                    key = str(a)
                    counts[key] = counts.get(key, 0) + 1
                frage_stats['statistik'] = {
                    'typ': 'verteilung',
                    'werte': counts
                }

            elif frage['typ'] == 'multiple_choice':
                # Count each selected option
                counts = {}
                for a in answers:
                    if isinstance(a, list):
                        for item in a:
                            counts[item] = counts.get(item, 0) + 1
                frage_stats['statistik'] = {
                    'typ': 'verteilung_mehrfach',
                    'werte': counts
                }

            elif frage['typ'] == 'skala':
                # Calculate average and distribution
                if answers:
                    numeric = [int(a) for a in answers if isinstance(a, (int, float, str)) and str(a).isdigit()]
                    if numeric:
                        frage_stats['statistik'] = {
                            'typ': 'skala',
                            'durchschnitt': sum(numeric) / len(numeric),
                            'min': min(numeric),
                            'max': max(numeric),
                            'verteilung': {str(v): numeric.count(v) for v in set(numeric)}
                        }

            elif frage['typ'] == 'text':
                # Just list all text answers
                frage_stats['statistik'] = {
                    'typ': 'text',
                    'antworten': answers
                }

            auswertung['fragen'].append(frage_stats)

        return auswertung


# Singleton instance
_fragebogen_service = None


def get_fragebogen_service() -> FragebogenService:
    """Get the fragebogen service singleton."""
    global _fragebogen_service
    if _fragebogen_service is None:
        _fragebogen_service = FragebogenService()
    return _fragebogen_service
