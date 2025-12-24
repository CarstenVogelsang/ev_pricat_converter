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


# Valid question types (V1 + V2)
VALID_FRAGE_TYPEN_V1 = ['single_choice', 'multiple_choice', 'skala', 'text', 'ja_nein']
VALID_FRAGE_TYPEN_V2 = VALID_FRAGE_TYPEN_V1 + ['dropdown', 'date', 'number', 'group', 'table', 'url']

# Alias for backwards compatibility
VALID_FRAGE_TYPEN = VALID_FRAGE_TYPEN_V1

# Valid prefill fields mapping to Kunde/User model attributes
# Format: 'kunde.<field>' - Maps to Kunde model or Kunde.user model
VALID_PREFILL_FIELDS = [
    # Kunde model fields
    'kunde.firmierung',
    'kunde.strasse',
    'kunde.plz',
    'kunde.ort',
    'kunde.land',
    'kunde.website_url',
    'kunde.shop_url',
    'kunde.telefon',
    'kunde.email',
    # User model fields (via kunde.user)
    'kunde.user.vorname',
    'kunde.user.nachname',
    'kunde.user.email',
]

# Mapping of prefill keys to their extraction logic
# Key: prefill key from JSON
# Value: tuple of (model_path, attribute_name)
PREFILL_FIELD_MAP = {
    'kunde.firmierung': ('kunde', 'firmierung'),
    'kunde.strasse': ('kunde', 'strasse'),
    'kunde.plz': ('kunde', 'plz'),
    'kunde.ort': ('kunde', 'ort'),
    'kunde.land': ('kunde', 'land'),
    'kunde.website_url': ('kunde', 'website_url'),
    'kunde.shop_url': ('kunde', 'shop_url'),
    'kunde.telefon': ('kunde', 'telefon'),
    'kunde.email': ('kunde', 'email'),
    'kunde.user.vorname': ('user', 'vorname'),
    'kunde.user.nachname': ('user', 'nachname'),
    'kunde.user.email': ('user', 'email'),
}

# Valid show_if operators
VALID_SHOW_IF_OPERATORS = ['equals', 'not_equals', 'is_set', 'is_not_set']


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
        """Validate a Fragebogen JSON definition (V1 or V2 schema).

        V1 Schema (flache Liste):
        {
            "fragen": [
                {"id": "q1", "typ": "single_choice", ...}
            ]
        }

        V2 Schema (mit Seiten):
        {
            "version": 2,
            "seiten": [
                {
                    "id": "s1",
                    "titel": "Abschnitt 1",
                    "hilfetext": "Optional",
                    "fragen": [
                        {"id": "q1", "typ": "dropdown", "prefill": "kunde.firmierung", ...}
                    ]
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

        # Determine version
        version = definition.get('version', 1)

        if version == 2:
            return self._validate_definition_v2(definition)
        else:
            return self._validate_definition_v1(definition)

    def _validate_definition_v1(self, definition: Dict[str, Any]) -> ValidationResult:
        """Validate V1 schema (flat question list)."""
        errors = []

        if 'fragen' not in definition:
            return ValidationResult(valid=False, errors=['Feld "fragen" fehlt'])

        fragen = definition['fragen']
        if not isinstance(fragen, list):
            return ValidationResult(valid=False, errors=['"fragen" muss eine Liste sein'])

        if len(fragen) == 0:
            return ValidationResult(valid=False, errors=['Mindestens eine Frage erforderlich'])

        seen_ids = set()
        for i, frage in enumerate(fragen):
            frage_errors = self._validate_frage(frage, f'Frage {i + 1}', seen_ids, is_v2=False)
            errors.extend(frage_errors)

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def _validate_definition_v2(self, definition: Dict[str, Any]) -> ValidationResult:
        """Validate V2 schema (page-based with extended features)."""
        errors = []

        if 'seiten' not in definition:
            return ValidationResult(valid=False, errors=['V2-Schema: Feld "seiten" fehlt'])

        seiten = definition['seiten']
        if not isinstance(seiten, list):
            return ValidationResult(valid=False, errors=['"seiten" muss eine Liste sein'])

        if len(seiten) == 0:
            return ValidationResult(valid=False, errors=['Mindestens eine Seite erforderlich'])

        seen_ids = set()  # Global across all pages
        seen_seiten_ids = set()
        total_fragen = 0

        for si, seite in enumerate(seiten):
            seite_prefix = f'Seite {si + 1}'

            if not isinstance(seite, dict):
                errors.append(f'{seite_prefix}: Muss ein Objekt sein')
                continue

            # Validate seite fields
            if 'id' not in seite:
                errors.append(f'{seite_prefix}: Feld "id" fehlt')
            elif seite['id'] in seen_seiten_ids:
                errors.append(f'{seite_prefix}: ID "{seite["id"]}" ist doppelt')
            else:
                seen_seiten_ids.add(seite['id'])

            if 'titel' not in seite:
                errors.append(f'{seite_prefix}: Feld "titel" fehlt')

            # Validate fragen within seite
            fragen = seite.get('fragen', [])
            if not isinstance(fragen, list):
                errors.append(f'{seite_prefix}: "fragen" muss eine Liste sein')
                continue

            for fi, frage in enumerate(fragen):
                frage_prefix = f'{seite_prefix}, Frage {fi + 1}'
                frage_errors = self._validate_frage(frage, frage_prefix, seen_ids, is_v2=True)
                errors.extend(frage_errors)
                total_fragen += 1

        if total_fragen == 0:
            errors.append('Mindestens eine Frage erforderlich')

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def _validate_frage(self, frage: Dict[str, Any], prefix: str,
                        seen_ids: set, is_v2: bool = False) -> List[str]:
        """Validate a single question.

        Args:
            frage: The question dict
            prefix: Error message prefix
            seen_ids: Set of already seen IDs (modified in place)
            is_v2: Whether V2 features are allowed

        Returns:
            List of error messages
        """
        errors = []
        valid_types = VALID_FRAGE_TYPEN_V2 if is_v2 else VALID_FRAGE_TYPEN_V1

        if not isinstance(frage, dict):
            return [f'{prefix}: Muss ein Objekt sein']

        # Required fields
        if 'id' not in frage:
            errors.append(f'{prefix}: Feld "id" fehlt')
        elif frage['id'] in seen_ids:
            errors.append(f'{prefix}: ID "{frage["id"]}" ist doppelt')
        else:
            seen_ids.add(frage['id'])

        if 'typ' not in frage:
            errors.append(f'{prefix}: Feld "typ" fehlt')
        elif frage['typ'] not in valid_types:
            errors.append(f'{prefix}: Ungültiger Typ "{frage["typ"]}"')

        # "frage" field is optional for group type (label can come from fields)
        typ = frage.get('typ')
        if typ != 'group' and 'frage' not in frage:
            errors.append(f'{prefix}: Feld "frage" (Fragetext) fehlt')

        # Type-specific validation
        errors.extend(self._validate_frage_type_specific(frage, prefix, typ, is_v2))

        # V2-specific validations
        if is_v2:
            errors.extend(self._validate_frage_v2_features(frage, prefix))

        return errors

    def _validate_frage_type_specific(self, frage: Dict[str, Any], prefix: str,
                                      typ: str, is_v2: bool) -> List[str]:
        """Validate type-specific fields."""
        errors = []

        if typ in ['single_choice', 'multiple_choice', 'dropdown']:
            if 'optionen' not in frage:
                errors.append(f'{prefix}: Feld "optionen" fehlt für {typ}')
            elif not isinstance(frage['optionen'], list) or len(frage['optionen']) < 2:
                errors.append(f'{prefix}: Mindestens 2 Optionen erforderlich')

        elif typ == 'skala':
            if 'min' not in frage or 'max' not in frage:
                errors.append(f'{prefix}: Felder "min" und "max" erforderlich für Skala')
            elif not isinstance(frage.get('min'), int) or not isinstance(frage.get('max'), int):
                errors.append(f'{prefix}: "min" und "max" müssen Zahlen sein')
            elif frage['min'] >= frage['max']:
                errors.append(f'{prefix}: "min" muss kleiner als "max" sein')

        elif typ == 'number' and is_v2:
            # min/max are optional for number type
            if 'min' in frage and not isinstance(frage['min'], (int, float)):
                errors.append(f'{prefix}: "min" muss eine Zahl sein')
            if 'max' in frage and not isinstance(frage['max'], (int, float)):
                errors.append(f'{prefix}: "max" muss eine Zahl sein')

        elif typ == 'group' and is_v2:
            if 'fields' not in frage:
                errors.append(f'{prefix}: Feld "fields" fehlt für group')
            elif not isinstance(frage['fields'], list) or len(frage['fields']) == 0:
                errors.append(f'{prefix}: Mindestens ein Feld in "fields" erforderlich')
            else:
                for fi, field in enumerate(frage['fields']):
                    if not isinstance(field, dict):
                        errors.append(f'{prefix}, Feld {fi + 1}: Muss ein Objekt sein')
                        continue
                    if 'id' not in field:
                        errors.append(f'{prefix}, Feld {fi + 1}: "id" fehlt')
                    if 'label' not in field:
                        errors.append(f'{prefix}, Feld {fi + 1}: "label" fehlt')
                    if 'typ' not in field:
                        errors.append(f'{prefix}, Feld {fi + 1}: "typ" fehlt')

        elif typ == 'table' and is_v2:
            if 'columns' not in frage:
                errors.append(f'{prefix}: Feld "columns" fehlt für table')
            elif not isinstance(frage['columns'], list) or len(frage['columns']) == 0:
                errors.append(f'{prefix}: Mindestens eine Spalte in "columns" erforderlich')
            # rows are optional - can be single-row table

        return errors

    def _validate_frage_v2_features(self, frage: Dict[str, Any], prefix: str) -> List[str]:
        """Validate V2-specific features like prefill and show_if."""
        errors = []

        # Validate prefill
        if 'prefill' in frage:
            prefill = frage['prefill']
            if not isinstance(prefill, str):
                errors.append(f'{prefix}: "prefill" muss ein String sein')
            elif prefill not in VALID_PREFILL_FIELDS:
                errors.append(f'{prefix}: Ungültiges prefill-Feld "{prefill}"')

        # Validate show_if
        if 'show_if' in frage:
            show_if = frage['show_if']
            if not isinstance(show_if, dict):
                errors.append(f'{prefix}: "show_if" muss ein Objekt sein')
            else:
                if 'frage_id' not in show_if:
                    errors.append(f'{prefix}: "show_if.frage_id" fehlt')

                # Check operator
                has_operator = False
                for op in VALID_SHOW_IF_OPERATORS:
                    if op in show_if:
                        has_operator = True
                        break
                if not has_operator:
                    errors.append(f'{prefix}: "show_if" braucht einen Operator (equals, not_equals, is_set, is_not_set)')

        return errors

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
                         teilnahmen: List[FragebogenTeilnahme] = None,
                         is_resend: bool = False) -> EinladungResult:
        """Send invitation emails to participants.

        Args:
            fragebogen: The Fragebogen
            teilnahmen: Specific participations to send to (optional, defaults to all unsent)
            is_resend: If True, allows resending to participants who already received an invitation

        Returns:
            EinladungResult with counts
        """
        from app.services.logging_service import log_mittel

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

                # Audit-Log für erfolgreichen E-Mail-Versand
                aktion = 'einladung_erneut_gesendet' if is_resend else 'einladung_gesendet'
                log_mittel(
                    modul='dialog',
                    aktion=aktion,
                    details=f'Einladung zu "{fragebogen.titel}" an {user.email} ({kunde.firmierung}) gesendet. Message-ID: {result.message_id or "n/a"}',
                    entity_type='FragebogenTeilnahme',
                    entity_id=teilnahme.id
                )
            else:
                errors.append(f'{kunde.firmierung}: {result.error}')
                failed_count += 1

                # Audit-Log für fehlgeschlagenen E-Mail-Versand
                log_mittel(
                    modul='dialog',
                    aktion='einladung_fehlgeschlagen',
                    details=f'Einladung zu "{fragebogen.titel}" an {user.email} ({kunde.firmierung}) fehlgeschlagen: {result.error}',
                    entity_type='FragebogenTeilnahme',
                    entity_id=teilnahme.id
                )

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

    def get_prefill_values(self, fragebogen: Fragebogen,
                           kunde: Kunde) -> Dict[str, Any]:
        """Extract prefill values for a Fragebogen from Kunde data.

        This extracts values for all fields that have 'prefill' configured
        in the fragebogen definition.

        Args:
            fragebogen: The Fragebogen with prefill definitions
            kunde: The Kunde to extract data from

        Returns:
            Dict mapping prefill keys to their values
        """
        prefill_values = {}

        for frage in fragebogen.fragen_mit_prefill:
            prefill_key = frage.get('prefill')
            if not prefill_key or prefill_key not in PREFILL_FIELD_MAP:
                continue

            model_type, attr_name = PREFILL_FIELD_MAP[prefill_key]

            try:
                if model_type == 'kunde':
                    value = getattr(kunde, attr_name, None)
                elif model_type == 'user' and kunde.user:
                    value = getattr(kunde.user, attr_name, None)
                else:
                    value = None

                prefill_values[prefill_key] = value
            except Exception:
                prefill_values[prefill_key] = None

        return prefill_values

    def get_prefill_for_frage(self, frage: Dict[str, Any],
                              kunde: Kunde) -> Optional[Any]:
        """Get the prefill value for a single question.

        Args:
            frage: The question dict with 'prefill' field
            kunde: The Kunde to extract data from

        Returns:
            The prefill value or None
        """
        prefill_key = frage.get('prefill')
        if not prefill_key or prefill_key not in PREFILL_FIELD_MAP:
            return None

        model_type, attr_name = PREFILL_FIELD_MAP[prefill_key]

        try:
            if model_type == 'kunde':
                return getattr(kunde, attr_name, None)
            elif model_type == 'user' and kunde.user:
                return getattr(kunde.user, attr_name, None)
        except Exception:
            pass

        return None

    def create_prefill_snapshot(self, teilnahme: FragebogenTeilnahme) -> Dict[str, Any]:
        """Create and save a snapshot of prefill values for change detection.

        Called when a participation starts. Stores the current values of all
        prefill fields so we can later detect what the customer changed.

        Args:
            teilnahme: The participation to create snapshot for

        Returns:
            The snapshot dict (also saved to teilnahme.prefill_snapshot_json)
        """
        fragebogen = teilnahme.fragebogen
        kunde = teilnahme.kunde

        # Only create snapshot for V2 frageboegen with prefill
        if not fragebogen.is_v2 or not fragebogen.fragen_mit_prefill:
            return {}

        snapshot = self.get_prefill_values(fragebogen, kunde)
        teilnahme.prefill_snapshot_json = snapshot
        db.session.commit()

        return snapshot

    def get_initial_antworten(self, fragebogen: Fragebogen,
                              kunde: Kunde) -> Dict[str, Dict[str, Any]]:
        """Get initial answer values for form pre-population.

        For V2 frageboegen, this returns prefill values as answer dicts.
        For V1, returns empty dict.

        Args:
            fragebogen: The Fragebogen
            kunde: The Kunde

        Returns:
            Dict mapping frage_id to answer dict (e.g., {"value": "..."})
        """
        if not fragebogen.is_v2:
            return {}

        initial = {}
        for frage in fragebogen.fragen_mit_prefill:
            frage_id = frage.get('id')
            prefill_value = self.get_prefill_for_frage(frage, kunde)

            if prefill_value is not None:
                initial[frage_id] = {'value': prefill_value}

        return initial

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
            # Create prefill snapshot for V2 frageboegen (for change detection later)
            if teilnahme.fragebogen.is_v2 and not teilnahme.prefill_snapshot_json:
                self.create_prefill_snapshot(teilnahme)

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
        For V2: Considers show_if conditions (hidden questions are not required).

        Args:
            teilnahme: The participation to complete

        Returns:
            True if completed successfully

        Raises:
            ValueError: If required questions are not answered
        """
        fragebogen = teilnahme.fragebogen

        # Build answer lookup for show_if evaluation
        antworten = {a.frage_id: a.value for a in teilnahme.antworten}

        # Check required questions
        missing = []
        for frage in fragebogen.fragen:
            if not frage.get('pflicht', False):
                continue

            # V2: Check if question is visible (show_if condition met)
            if not self._is_frage_visible(frage, antworten):
                continue  # Hidden questions are not required

            antwort = teilnahme.get_antwort(frage['id'])
            if not antwort or not antwort.value:
                missing.append(frage.get('frage', frage['id']))

        if missing:
            raise ValueError(f'Pflichtfragen nicht beantwortet: {", ".join(missing[:3])}...')

        teilnahme.abschliessen()
        db.session.commit()
        return True

    def _is_frage_visible(self, frage: Dict[str, Any],
                           antworten: Dict[str, Any]) -> bool:
        """Check if a question should be visible based on show_if condition.

        Args:
            frage: The question dict
            antworten: Dict of frage_id -> answer value

        Returns:
            True if question should be visible
        """
        show_if = frage.get('show_if')
        if not show_if:
            return True  # No condition = always visible

        ref_frage_id = show_if.get('frage_id')
        if not ref_frage_id:
            return True  # Invalid condition = show

        ref_value = antworten.get(ref_frage_id)

        # Check each operator
        if 'equals' in show_if:
            expected = show_if['equals']
            return ref_value == expected

        if 'not_equals' in show_if:
            expected = show_if['not_equals']
            return ref_value != expected

        if 'is_set' in show_if:
            return ref_value is not None and ref_value != ''

        if 'is_not_set' in show_if:
            return ref_value is None or ref_value == ''

        return True  # Unknown operator = show

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

        # V2: Add change detection info for prefilled fields
        if fragebogen.is_v2 and fragebogen.fragen_mit_prefill:
            auswertung['aenderungen'] = self._get_aenderungen_summary(fragebogen, abgeschlossene)

        return auswertung

    def _get_aenderungen_summary(self, fragebogen: Fragebogen,
                                  abgeschlossene: List[FragebogenTeilnahme]) -> Dict[str, Any]:
        """Get summary of changes to prefilled fields.

        Args:
            fragebogen: The Fragebogen
            abgeschlossene: List of completed participations

        Returns:
            Dict with change statistics per prefill field
        """
        summary = {
            'total_mit_aenderungen': 0,
            'felder': {}
        }

        # Initialize counters for each prefill field
        for frage in fragebogen.fragen_mit_prefill:
            frage_id = frage['id']
            summary['felder'][frage_id] = {
                'frage': frage.get('frage', frage_id),
                'prefill_key': frage.get('prefill'),
                'anzahl_geaendert': 0,
                'beispiele': []  # First 3 changes as examples
            }

        # Collect changes from each completed participation
        for teilnahme in abgeschlossene:
            changes = teilnahme.get_geaenderte_felder()
            if changes:
                summary['total_mit_aenderungen'] += 1

            for change in changes:
                frage_id = change['frage_id']
                if frage_id in summary['felder']:
                    summary['felder'][frage_id]['anzahl_geaendert'] += 1
                    # Store first 3 examples
                    if len(summary['felder'][frage_id]['beispiele']) < 3:
                        summary['felder'][frage_id]['beispiele'].append({
                            'kunde': teilnahme.kunde.firmierung,
                            'original': change['original'],
                            'neu': change['neu']
                        })

        return summary

    def get_teilnehmer_auswertung(self, teilnahme: FragebogenTeilnahme) -> Dict[str, Any]:
        """Get detailed evaluation for a single participant.

        Returns all answers with prefill change detection for V2 frageboegen.

        Args:
            teilnahme: The participation to evaluate

        Returns:
            Dict with kunde info, status, all answers, and change count
        """
        fragebogen = teilnahme.fragebogen
        kunde = teilnahme.kunde

        # Get geänderte felder for quick lookup
        geaenderte_ids = set()
        geaenderte_map = {}
        if fragebogen.is_v2 and teilnahme.prefill_snapshot_json:
            for change in teilnahme.get_geaenderte_felder():
                geaenderte_ids.add(change['frage_id'])
                geaenderte_map[change['frage_id']] = change['original']

        antworten = []
        for frage in fragebogen.fragen:
            frage_id = frage['id']
            antwort_obj = teilnahme.get_antwort(frage_id)
            antwort_value = antwort_obj.value if antwort_obj else None

            # Format answer for display
            display_value = antwort_value
            if isinstance(antwort_value, list):
                display_value = ', '.join(str(v) for v in antwort_value)
            elif antwort_value is None:
                display_value = '—'

            # Check if this was a prefilled field that was changed
            wurde_geaendert = frage_id in geaenderte_ids
            prefill_original = geaenderte_map.get(frage_id) if wurde_geaendert else None

            antworten.append({
                'frage_id': frage_id,
                'frage': frage.get('frage', frage_id),
                'typ': frage['typ'],
                'antwort': display_value,
                'antwort_raw': antwort_value,
                'prefill_original': prefill_original,
                'wurde_geaendert': wurde_geaendert,
                'hat_prefill': 'prefill' in frage
            })

        return {
            'teilnahme_id': teilnahme.id,
            'kunde': {
                'id': kunde.id,
                'firmierung': kunde.firmierung
            },
            'status': teilnahme.status,
            'abgeschlossen_am': teilnahme.abgeschlossen_am,
            'antworten': antworten,
            'aenderungen_count': len(geaenderte_ids)
        }

    def duplicate_fragebogen(self, fragebogen: Fragebogen, user_id: int,
                              new_titel: str = None) -> Fragebogen:
        """Create a new version of a Fragebogen in ENTWURF status.

        Creates a version chain: V1 → V2 → V3, etc.
        Only the newest version can be duplicated.

        Copies: titel, beschreibung, definition_json
        Does NOT copy: participants, answers, status (always ENTWURF)

        Args:
            fragebogen: Source fragebogen to copy (must be newest version)
            user_id: ID of user creating the copy
            new_titel: Optional custom title (default: same as original)

        Returns:
            New Fragebogen in ENTWURF status with incremented version

        Raises:
            ValueError: If trying to duplicate a non-newest version
        """
        import copy

        # Only the newest version can be duplicated
        if not fragebogen.ist_neueste_version:
            newest = fragebogen.nachfolger.first()
            raise ValueError(
                f"Nur die neueste Version kann dupliziert werden. "
                f"Bitte Version {newest.version_nummer} verwenden."
            )

        titel = new_titel or fragebogen.titel

        # Deep copy the JSON definition to avoid reference issues
        definition_copy = copy.deepcopy(fragebogen.definition_json)

        new_fragebogen = Fragebogen(
            titel=titel,
            beschreibung=fragebogen.beschreibung,
            definition_json=definition_copy,
            status=FragebogenStatus.ENTWURF.value,
            erstellt_von_id=user_id,
            # Version chain: link to predecessor and increment version
            vorgaenger_id=fragebogen.id,
            version_nummer=fragebogen.version_nummer + 1
        )
        db.session.add(new_fragebogen)
        db.session.commit()

        return new_fragebogen

    def archiviere_fragebogen(self, fragebogen: Fragebogen) -> None:
        """Archive a Fragebogen (soft-delete).

        Archived Fragebögen are hidden from the default list view
        but can be shown with a filter.

        Args:
            fragebogen: The fragebogen to archive
        """
        fragebogen.archivieren()
        db.session.commit()

    def dearchiviere_fragebogen(self, fragebogen: Fragebogen) -> None:
        """Restore an archived Fragebogen.

        Args:
            fragebogen: The fragebogen to restore
        """
        fragebogen.dearchivieren()
        db.session.commit()


# Singleton instance
_fragebogen_service = None


def get_fragebogen_service() -> FragebogenService:
    """Get the fragebogen service singleton."""
    global _fragebogen_service
    if _fragebogen_service is None:
        _fragebogen_service = FragebogenService()
    return _fragebogen_service
