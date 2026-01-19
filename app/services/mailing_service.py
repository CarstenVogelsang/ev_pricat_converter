"""Mailing Service for marketing email management (PRD-013).

Handles:
- Mailing CRUD operations
- Empfaenger (recipient) management
- Sektionen (section) management
- E-Mail rendering with personalization
- Fragebogen integration
- Versand (sending) with batch support
- Klick-Tracking
- Abmeldung (opt-out) handling
"""
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from flask import url_for, render_template
from jinja2 import Template
from urllib.parse import quote
import markdown

from app import db
from app.services.email_service import EmailResult
from app.models import (
    Mailing, MailingEmpfaenger, MailingKlick, MailingZielgruppe,
    MailingStatus, EmpfaengerStatus,
    Kunde, Fragebogen, FragebogenTeilnahme
)


# Valid section types for the Mailing-Editor (PRD-013 Phase 5)
VALID_SEKTION_TYPEN = [
    'header',        # Logo, Telefon, Kontakt-Links
    'hero',          # Headline, Subline, Bild
    'text_bild',     # Freitext mit optionalem Bild
    'cta_button',    # CTA mit Fragebogen oder externer URL
    'fragebogen_cta',  # Legacy: wird zu cta_button migriert
    'footer',        # Impressum, Abmelden, Weiterempfehlen
]

# Personalization placeholders available in email content
PERSONALISIERUNG_FELDER = {
    'briefanrede': 'Anrede des Kunden (z.B. "Sehr geehrter Herr Müller")',
    'firmenname': 'Firmierung des Kunden',
    'vorname': 'Vorname des Kontakts',
    'nachname': 'Nachname des Kontakts',
    'email': 'E-Mail-Adresse',
    'fragebogen_link': 'Magic-Link zum Fragebogen (auto-generiert)',
    'abmelde_link': 'Link zur Abmeldung (auto-generiert)',
}


@dataclass
class VersandResult:
    """Result of sending a mailing batch."""
    success: bool
    sent_count: int = 0
    failed_count: int = 0
    pending_count: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class BatchInfo:
    """Information about batch requirements for a mailing."""
    total_empfaenger: int
    daily_remaining: int
    batch_size: int
    batches_needed: int
    can_send_all: bool


class MailingService:
    """Service for managing Mailings (marketing emails)."""

    # ========== CRUD Operations ==========

    def create_mailing(
        self,
        titel: str,
        betreff: str,
        erstellt_von_id: int,
        fragebogen_id: int = None
    ) -> Mailing:
        """Create a new Mailing in draft status.

        Args:
            titel: Internal title for the mailing
            betreff: Email subject line
            erstellt_von_id: User ID of the creator
            fragebogen_id: Optional linked Fragebogen ID

        Returns:
            Created Mailing instance
        """
        mailing = Mailing(
            titel=titel,
            betreff=betreff,
            erstellt_von_id=erstellt_von_id,
            fragebogen_id=fragebogen_id,
            status=MailingStatus.ENTWURF.value,
            sektionen_json={'sektionen': []}
        )
        db.session.add(mailing)
        db.session.commit()
        return mailing

    def update_mailing(
        self,
        mailing: Mailing,
        titel: str = None,
        betreff: str = None,
        fragebogen_id: int = None
    ) -> Mailing:
        """Update mailing properties (only in ENTWURF status).

        Args:
            mailing: Mailing to update
            titel: New title (optional)
            betreff: New subject (optional)
            fragebogen_id: New linked Fragebogen ID (optional, use -1 to remove)

        Returns:
            Updated Mailing

        Raises:
            ValueError: If mailing is not in ENTWURF status
        """
        if not mailing.is_entwurf:
            raise ValueError('Nur Mailings im Entwurf-Status können bearbeitet werden')

        if titel is not None:
            mailing.titel = titel
        if betreff is not None:
            mailing.betreff = betreff
        if fragebogen_id is not None:
            mailing.fragebogen_id = fragebogen_id if fragebogen_id > 0 else None

        db.session.commit()
        return mailing

    def delete_mailing(self, mailing: Mailing) -> bool:
        """Delete a mailing (only in ENTWURF status with no sent emails).

        Args:
            mailing: Mailing to delete

        Returns:
            True if deleted

        Raises:
            ValueError: If mailing cannot be deleted
        """
        if not mailing.is_entwurf:
            raise ValueError('Nur Mailings im Entwurf-Status können gelöscht werden')

        if mailing.anzahl_versendet > 0:
            raise ValueError('Mailings mit versendeten E-Mails können nicht gelöscht werden')

        db.session.delete(mailing)
        db.session.commit()
        return True

    def get_mailing_by_id(self, mailing_id: int) -> Optional[Mailing]:
        """Get a Mailing by ID."""
        return Mailing.query.get(mailing_id)

    def get_all_mailings(self) -> List[Mailing]:
        """Get all Mailings ordered by creation date."""
        return Mailing.query.order_by(Mailing.erstellt_am.desc()).all()

    def get_mailings_by_status(self, status: MailingStatus) -> List[Mailing]:
        """Get Mailings filtered by status."""
        return Mailing.query.filter_by(status=status.value).order_by(
            Mailing.erstellt_am.desc()
        ).all()

    # ========== Sektionen Management ==========

    def add_sektion(
        self,
        mailing: Mailing,
        typ: str,
        config: Dict[str, Any] = None
    ) -> str:
        """Add a new section to the mailing.

        Args:
            mailing: Mailing to add section to
            typ: Section type (header, text_bild, fragebogen_cta, footer)
            config: Section configuration

        Returns:
            ID of the created section

        Raises:
            ValueError: If mailing is not editable or type is invalid
        """
        if not mailing.is_entwurf:
            raise ValueError('Nur Mailings im Entwurf-Status können bearbeitet werden')

        if typ not in VALID_SEKTION_TYPEN:
            raise ValueError(f'Ungültiger Sektions-Typ: {typ}')

        sektion_id = mailing.add_sektion(typ, config or {})
        db.session.commit()
        return sektion_id

    def update_sektion(
        self,
        mailing: Mailing,
        sektion_id: str,
        config: Dict[str, Any]
    ) -> bool:
        """Update a section's configuration.

        Args:
            mailing: Mailing containing the section
            sektion_id: ID of the section to update
            config: New configuration

        Returns:
            True if updated

        Raises:
            ValueError: If section not found or mailing not editable
        """
        if not mailing.is_entwurf:
            raise ValueError('Nur Mailings im Entwurf-Status können bearbeitet werden')

        sektionen = mailing.sektionen
        for sektion in sektionen:
            if sektion.get('id') == sektion_id:
                sektion['config'] = config
                mailing.update_sektionen(sektionen)
                db.session.commit()
                return True

        raise ValueError(f'Sektion {sektion_id} nicht gefunden')

    def remove_sektion(self, mailing: Mailing, sektion_id: str) -> bool:
        """Remove a section from the mailing.

        Args:
            mailing: Mailing to remove section from
            sektion_id: ID of the section to remove

        Returns:
            True if removed

        Raises:
            ValueError: If section not found or mailing not editable
        """
        if not mailing.is_entwurf:
            raise ValueError('Nur Mailings im Entwurf-Status können bearbeitet werden')

        sektionen = [s for s in mailing.sektionen if s.get('id') != sektion_id]
        if len(sektionen) == len(mailing.sektionen):
            raise ValueError(f'Sektion {sektion_id} nicht gefunden')

        mailing.update_sektionen(sektionen)
        db.session.commit()
        return True

    def reorder_sektionen(self, mailing: Mailing, sektion_ids: List[str]) -> bool:
        """Reorder sections by providing new order of IDs.

        Args:
            mailing: Mailing to reorder
            sektion_ids: List of section IDs in desired order

        Returns:
            True if reordered

        Raises:
            ValueError: If IDs don't match or mailing not editable
        """
        if not mailing.is_entwurf:
            raise ValueError('Nur Mailings im Entwurf-Status können bearbeitet werden')

        current_ids = {s.get('id') for s in mailing.sektionen}
        if set(sektion_ids) != current_ids:
            raise ValueError('Sektions-IDs stimmen nicht überein')

        # Build new ordered list
        sektionen_map = {s.get('id'): s for s in mailing.sektionen}
        new_sektionen = [sektionen_map[sid] for sid in sektion_ids]

        mailing.update_sektionen(new_sektionen)
        db.session.commit()
        return True

    # ========== Empfaenger Management ==========

    def add_empfaenger(self, mailing: Mailing, kunde: Kunde) -> Optional[MailingEmpfaenger]:
        """Add a single recipient to the mailing.

        Args:
            mailing: Mailing to add recipient to
            kunde: Kunde to add as recipient

        Returns:
            Created MailingEmpfaenger or None if already exists

        Raises:
            ValueError: If kunde cannot receive mailings
        """
        if not kunde.kann_mailing_erhalten():
            raise ValueError(f'Kunde {kunde.firmierung} kann keine Mailings empfangen')

        # Check if already added
        existing = MailingEmpfaenger.query.filter_by(
            mailing_id=mailing.id,
            kunde_id=kunde.id
        ).first()
        if existing:
            return None

        empfaenger = MailingEmpfaenger.create_for_kunde(mailing.id, kunde.id)
        db.session.add(empfaenger)
        mailing.update_statistik()
        db.session.commit()
        return empfaenger

    def add_empfaenger_bulk(
        self,
        mailing: Mailing,
        kunde_ids: List[int]
    ) -> int:
        """Add multiple recipients to the mailing.

        Args:
            mailing: Mailing to add recipients to
            kunde_ids: List of Kunde IDs to add

        Returns:
            Number of recipients actually added (excluding duplicates/invalid)
        """
        added = 0
        for kunde_id in kunde_ids:
            kunde = Kunde.query.get(kunde_id)
            if kunde and kunde.kann_mailing_erhalten():
                try:
                    if self.add_empfaenger(mailing, kunde):
                        added += 1
                except ValueError:
                    continue

        return added

    def remove_empfaenger(self, mailing: Mailing, kunde_id: int) -> bool:
        """Remove a recipient from the mailing.

        Args:
            mailing: Mailing to remove recipient from
            kunde_id: Kunde ID to remove

        Returns:
            True if removed

        Raises:
            ValueError: If recipient not found or already sent
        """
        empfaenger = MailingEmpfaenger.query.filter_by(
            mailing_id=mailing.id,
            kunde_id=kunde_id
        ).first()

        if not empfaenger:
            raise ValueError('Empfänger nicht gefunden')

        if empfaenger.is_versendet:
            raise ValueError('Bereits versendete Empfänger können nicht entfernt werden')

        db.session.delete(empfaenger)
        mailing.update_statistik()
        db.session.commit()
        return True

    def get_verfuegbare_empfaenger(self, mailing: Mailing) -> List[Kunde]:
        """Get all Kunden that can be added as recipients.

        Filters out:
        - Kunden already added to this mailing
        - Kunden who opted out of mailings
        - Kunden without contact email
        """
        # Get IDs of already added empfaenger
        existing_ids = {e.kunde_id for e in mailing.empfaenger}

        # Query all eligible Kunden
        return Kunde.query.filter(
            Kunde.id.notin_(existing_ids),
            Kunde.mailing_abgemeldet == False,  # noqa
            Kunde.aktiv == True  # noqa
        ).order_by(Kunde.firmierung).all()

    # ========== Personalisierung & Rendering ==========

    def get_personalisierung_context(self, kunde: Kunde) -> Dict[str, Any]:
        """Build personalization context for a Kunde.

        Args:
            kunde: Kunde to build context for

        Returns:
            Dict with all available personalization values
        """
        user = kunde.hauptbenutzer

        return {
            'briefanrede': kunde.briefanrede,
            'firmenname': kunde.firmierung,
            'vorname': user.vorname if user else '',
            'nachname': user.nachname if user else '',
            'email': kunde.kontakt_email or '',
        }

    def render_sektion(
        self,
        sektion: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Render a single section with personalization.

        Args:
            sektion: Section definition from sektionen_json
            context: Personalization context

        Returns:
            Rendered HTML string
        """
        typ = sektion.get('typ')
        config = sektion.get('config', {}).copy()

        # Markdown → HTML Konvertierung für text_bild Sektionen (PRD-013 Phase 5c)
        if typ == 'text_bild' and config.get('inhalt_html'):
            md = markdown.Markdown(extensions=['nl2br', 'extra'])
            config['inhalt_html'] = md.convert(config['inhalt_html'])

        template_name = f'mailing/email/sektion_{typ}.html'

        try:
            return render_template(
                template_name,
                config=config,
                **context
            )
        except Exception:
            # Fallback for missing templates during development
            return f'<!-- Sektion {typ} -->'

    def get_or_create_preview_empfaenger(self, mailing: Mailing) -> Optional[MailingEmpfaenger]:
        """Get or create a preview empfaenger for the mailing.

        Uses the Betreiber (Systemkunde) as the preview recipient.
        This allows preview links to function properly.

        Args:
            mailing: Mailing to create preview for

        Returns:
            MailingEmpfaenger for preview, or None if no Betreiber exists
        """
        # Get Betreiber (Systemkunde)
        betreiber = Kunde.query.filter_by(ist_systemkunde=True).first()
        if not betreiber:
            return None

        # Check if preview empfaenger already exists
        preview = MailingEmpfaenger.query.filter_by(
            mailing_id=mailing.id,
            kunde_id=betreiber.id
        ).first()

        if not preview:
            # Create preview empfaenger
            preview = MailingEmpfaenger.create_for_kunde(mailing.id, betreiber.id)
            db.session.add(preview)
            db.session.commit()

        return preview

    def get_sample_context(self, mailing: Mailing = None) -> Dict[str, Any]:
        """Get sample data for email preview.

        Args:
            mailing: Optional mailing to create preview empfaenger for

        Returns:
            Dict with sample personalization values
        """
        from app.services import get_branding_service

        branding_service = get_branding_service()
        branding = branding_service.get_branding_dict()

        # Get Betreiber (Systemkunde)
        betreiber = Kunde.query.filter_by(ist_systemkunde=True).first()

        # Get or create preview empfaenger for working links
        preview_links = {
            'fragebogen_link': '#preview-fragebogen',
            'abmelde_link': '#preview-abmelden',
            'profil_link': '#preview-profil',
            'empfehlen_link': '#preview-empfehlen',
            'browser_link': '#preview-browser',
            'cta_link': '#preview-cta',
        }

        if mailing:
            preview = self.get_or_create_preview_empfaenger(mailing)
            if preview:
                # Generate real URLs with the preview token
                preview_links['abmelde_link'] = url_for('mailing.abmelden',
                                                         token=preview.tracking_token,
                                                         _external=True)
                preview_links['profil_link'] = url_for('mailing.profil',
                                                        token=preview.tracking_token,
                                                        _external=True)
                preview_links['empfehlen_link'] = url_for('mailing.empfehlen',
                                                           token=preview.tracking_token,
                                                           _external=True)
                preview_links['browser_link'] = url_for('mailing.browser_ansicht',
                                                         token=preview.tracking_token,
                                                         _external=True)

                # Fragebogen link (if linked)
                if mailing.fragebogen_id:
                    self.ensure_fragebogen_teilnahme(mailing, preview)
                    if preview.fragebogen_teilnahme:
                        preview_links['fragebogen_link'] = self.generate_tracking_url(
                            preview, 'fragebogen'
                        )
                        preview_links['cta_link'] = preview_links['fragebogen_link']

        return {
            'briefanrede': 'Sehr geehrter Herr Mustermann',
            'firmenname': 'Musterfirma GmbH',
            'vorname': 'Max',
            'nachname': 'Mustermann',
            'email': 'max@musterfirma.de',
            # Tracking links (real if mailing provided, else placeholders)
            **preview_links,
            # Context
            'portal_name': branding.get('app_title', 'ev247'),
            'jahr': str(datetime.now().year),
            'betreiber': betreiber,
            'branding': branding,
        }

    def render_mailing_html(
        self,
        mailing: Mailing,
        kunde: Kunde = None,
        empfaenger: 'MailingEmpfaenger' = None,
        fragebogen_link: str = None,
        abmelde_link: str = None,
        preview_mode: bool = False
    ) -> str:
        """Render complete mailing HTML for a recipient.

        Args:
            mailing: Mailing to render
            kunde: Recipient Kunde (None for preview mode)
            empfaenger: MailingEmpfaenger for tracking token (optional)
            fragebogen_link: Optional pre-generated fragebogen magic-link
            abmelde_link: Optional pre-generated opt-out link
            preview_mode: If True, use sample data instead of kunde

        Returns:
            Complete rendered HTML email
        """
        from app.services import get_branding_service

        branding_service = get_branding_service()
        branding = branding_service.get_branding_dict()

        # Get Betreiber (Systemkunde)
        betreiber = Kunde.query.filter_by(ist_systemkunde=True).first()

        # Build personalization context
        if preview_mode or not kunde:
            context = self.get_sample_context()
        else:
            context = self.get_personalisierung_context(kunde)
            context['fragebogen_link'] = fragebogen_link or '#'
            context['abmelde_link'] = abmelde_link or '#'
            context['betreiber'] = betreiber
            context['branding'] = branding

            # Generate additional tracking URLs if empfaenger provided
            if empfaenger:
                context['profil_link'] = url_for('mailing.profil',
                                                  token=empfaenger.tracking_token,
                                                  _external=True)
                context['empfehlen_link'] = url_for('mailing.empfehlen',
                                                     token=empfaenger.tracking_token,
                                                     _external=True)
                context['browser_link'] = url_for('mailing.browser_ansicht',
                                                   token=empfaenger.tracking_token,
                                                   _external=True)
            else:
                context['profil_link'] = '#'
                context['empfehlen_link'] = '#'
                context['browser_link'] = '#'

        # Add portal info
        context['portal_name'] = branding.get('app_title', 'ev247')
        context['jahr'] = str(datetime.now().year)
        context['betreff'] = mailing.betreff

        # Render each section with section-specific context
        rendered_sektionen = []
        for sektion in mailing.sektionen:
            sektion_context = context.copy()

            # Calculate CTA link based on section config (for cta_button type)
            if sektion.get('typ') == 'cta_button':
                sektion_context['cta_link'] = self._get_cta_link(
                    sektion.get('config', {}),
                    mailing,
                    context.get('fragebogen_link')
                )
            elif sektion.get('typ') == 'fragebogen_cta':
                # Legacy: Use fragebogen_link
                sektion_context['cta_link'] = context.get('fragebogen_link', '#')

            rendered = self.render_sektion(sektion, sektion_context)
            rendered_sektionen.append(rendered)

        # Combine all sections into content
        content = '\n'.join(rendered_sektionen)

        # Wrap in base template
        try:
            return render_template(
                'mailing/email/base.html',
                content=content,
                betreff=mailing.betreff,
                **context
            )
        except Exception:
            # Fallback during development
            return content

    def _get_cta_link(
        self,
        config: Dict[str, Any],
        mailing: Mailing,
        fragebogen_link: str
    ) -> str:
        """Calculate the CTA link based on config.

        Args:
            config: CTA section config
            mailing: Mailing for fragebogen lookup
            fragebogen_link: Pre-generated fragebogen link

        Returns:
            URL for the CTA button
        """
        link_typ = config.get('link_typ', 'fragebogen')

        if link_typ == 'extern':
            return config.get('externe_url', '#')

        # Fragebogen link
        fragebogen_id = config.get('fragebogen_id')
        if fragebogen_id and fragebogen_link:
            return fragebogen_link
        elif mailing.fragebogen_id and fragebogen_link:
            return fragebogen_link

        return '#'

    # ========== Fragebogen Integration ==========

    def ensure_fragebogen_teilnahme(
        self,
        mailing: Mailing,
        empfaenger: MailingEmpfaenger
    ) -> Optional[FragebogenTeilnahme]:
        """Ensure a FragebogenTeilnahme exists for the recipient.

        If the mailing has a linked Fragebogen, this creates or retrieves
        the existing Teilnahme for the Kunde.

        Args:
            mailing: Mailing with optional fragebogen_id
            empfaenger: Recipient to create Teilnahme for

        Returns:
            FragebogenTeilnahme if mailing has linked Fragebogen, else None
        """
        if not mailing.fragebogen_id:
            return None

        # Check for existing Teilnahme
        teilnahme = FragebogenTeilnahme.query.filter_by(
            fragebogen_id=mailing.fragebogen_id,
            kunde_id=empfaenger.kunde_id
        ).first()

        if not teilnahme:
            # Create new Teilnahme
            teilnahme = FragebogenTeilnahme.create_for_kunde(
                mailing.fragebogen_id,
                empfaenger.kunde_id
            )
            db.session.add(teilnahme)
            db.session.flush()

        # Link to empfaenger
        empfaenger.fragebogen_teilnahme_id = teilnahme.id
        db.session.commit()

        return teilnahme

    # ========== Tracking ==========

    def get_empfaenger_by_token(self, token: str) -> Optional[MailingEmpfaenger]:
        """Get a MailingEmpfaenger by tracking token."""
        return MailingEmpfaenger.query.filter_by(tracking_token=token).first()

    def track_klick(
        self,
        token: str,
        link_typ: str,
        url: str = None
    ) -> Optional[MailingKlick]:
        """Record a click on a tracked link.

        Args:
            token: Empfaenger tracking token
            link_typ: Type of link clicked ('fragebogen', 'abmelden', 'custom')
            url: Optional original URL

        Returns:
            Created MailingKlick or None if token invalid
        """
        empfaenger = self.get_empfaenger_by_token(token)
        if not empfaenger:
            return None

        klick = MailingKlick(
            empfaenger_id=empfaenger.id,
            link_typ=link_typ,
            url=url
        )
        db.session.add(klick)
        db.session.commit()
        return klick

    # ========== Abmeldung ==========

    def handle_abmeldung(self, token: str) -> bool:
        """Handle opt-out request from tracking token.

        Args:
            token: Empfaenger tracking token

        Returns:
            True if opt-out was processed

        Raises:
            ValueError: If token is invalid
        """
        empfaenger = self.get_empfaenger_by_token(token)
        if not empfaenger:
            raise ValueError('Ungültiger Abmelde-Link')

        kunde = empfaenger.kunde
        kunde.mailing_abmelden()

        # Track the click
        self.track_klick(token, 'abmelden')

        db.session.commit()
        return True

    # ========== Batch/Quota Info ==========

    def get_batch_info(self, mailing: Mailing, daily_limit: int = 300) -> BatchInfo:
        """Get batch information for sending.

        Args:
            mailing: Mailing to check
            daily_limit: Daily email limit (default 300 for Brevo free)

        Returns:
            BatchInfo with batch calculations
        """
        pending = mailing.anzahl_ausstehend
        batches_needed = (pending + daily_limit - 1) // daily_limit if pending > 0 else 0

        return BatchInfo(
            total_empfaenger=len(mailing.empfaenger),
            daily_remaining=daily_limit,  # Could integrate with Brevo API
            batch_size=min(pending, daily_limit),
            batches_needed=batches_needed,
            can_send_all=pending <= daily_limit
        )

    # ========== Versand ==========

    def generate_tracking_url(
        self,
        empfaenger: MailingEmpfaenger,
        link_typ: str,
        target_url: str = None
    ) -> str:
        """Generate a tracking URL for click tracking.

        Args:
            empfaenger: Recipient with tracking_token
            link_typ: Type of link ('fragebogen', 'abmelden', 'custom')
            target_url: Target URL for custom links

        Returns:
            Tracking URL that will redirect to target after recording click
        """
        base_url = url_for('mailing.track_click',
                           token=empfaenger.tracking_token,
                           _external=True)

        if link_typ == 'fragebogen':
            return f"{base_url}?typ=fragebogen"
        elif link_typ == 'abmelden':
            return f"{base_url}?typ=abmelden"
        else:
            encoded_url = quote(target_url, safe='')
            return f"{base_url}?typ=custom&url={encoded_url}"

    def send_test_email(
        self,
        mailing: Mailing,
        to_email: str,
        kunde: 'Kunde' = None,
        to_name: str = None
    ) -> EmailResult:
        """Send a test email to a specified address.

        Args:
            mailing: Mailing to test
            to_email: Email address to send test to
            kunde: Optional Kunde for real placeholder resolution
            to_name: Optional recipient name

        Returns:
            EmailResult with success/failure info

        If kunde is provided, placeholders like {{ briefanrede }} and
        {{ firmenname }} are resolved with real data. Otherwise,
        sample data is used (preview_mode=True).
        """
        from app.services import get_brevo_service

        brevo = get_brevo_service()

        # Render with real kunde data or sample context
        if kunde:
            # Use real kunde data for placeholder resolution
            html_content = self.render_mailing_html(
                mailing,
                kunde=kunde,
                preview_mode=False
            )
            recipient_name = to_name or kunde.kontakt_name
        else:
            # Fallback to sample data
            html_content = self.render_mailing_html(mailing, preview_mode=True)
            recipient_name = to_name or 'Test-Empfänger'

        # Send via Brevo
        return brevo._send_email(
            to_email=to_email,
            to_name=recipient_name,
            subject=f'[TEST] {mailing.betreff}',
            html_content=html_content
        )

    def send_to_empfaenger(
        self,
        mailing: Mailing,
        empfaenger: MailingEmpfaenger
    ) -> EmailResult:
        """Send mailing to a single recipient.

        Steps:
        1. Ensure FragebogenTeilnahme exists (if linked)
        2. Generate tracking URLs
        3. Render personalized email
        4. Send via BrevoService
        5. Update empfaenger status

        Args:
            mailing: Mailing to send
            empfaenger: Recipient to send to

        Returns:
            EmailResult with success/failure info
        """
        from app.services import get_brevo_service

        brevo = get_brevo_service()
        kunde = empfaenger.kunde

        # 1. Ensure FragebogenTeilnahme if mailing has linked fragebogen
        if mailing.fragebogen_id:
            self.ensure_fragebogen_teilnahme(mailing, empfaenger)

        # 2. Generate tracking URLs
        if mailing.fragebogen_id and empfaenger.fragebogen_teilnahme:
            fragebogen_link = self.generate_tracking_url(empfaenger, 'fragebogen')
        else:
            fragebogen_link = '#'

        abmelde_link = self.generate_tracking_url(empfaenger, 'abmelden')

        # 3. Render personalized email
        html_content = self.render_mailing_html(
            mailing,
            kunde=kunde,
            empfaenger=empfaenger,
            fragebogen_link=fragebogen_link,
            abmelde_link=abmelde_link,
            preview_mode=False
        )

        # 4. Send via Brevo
        if kunde.hauptbenutzer:
            to_name = f'{kunde.hauptbenutzer.vorname} {kunde.hauptbenutzer.nachname}'
        else:
            to_name = kunde.firmierung

        result = brevo._send_email(
            to_email=kunde.kontakt_email,
            to_name=to_name,
            subject=mailing.betreff,
            html_content=html_content
        )

        # 5. Update empfaenger status
        if result.success:
            empfaenger.status = EmpfaengerStatus.VERSENDET.value
            empfaenger.versendet_am = datetime.utcnow()
        else:
            empfaenger.status = EmpfaengerStatus.FEHLGESCHLAGEN.value
            empfaenger.fehler_nachricht = result.error

        db.session.commit()
        return result

    def send_batch(
        self,
        mailing: Mailing,
        max_count: int = None
    ) -> VersandResult:
        """Send mailing to all pending recipients.

        Respects quota limits and stops when quota is exhausted.

        Args:
            mailing: Mailing to send
            max_count: Maximum number to send (None = all pending up to quota)

        Returns:
            VersandResult with counts and any errors
        """
        from app.services import get_brevo_service

        brevo = get_brevo_service()

        # Get pending empfaenger
        pending = [e for e in mailing.empfaenger
                   if e.status == EmpfaengerStatus.AUSSTEHEND.value]

        if max_count:
            pending = pending[:max_count]

        # Check quota
        remaining_quota = brevo.get_remaining_quota()
        to_send = pending[:remaining_quota]

        sent_count = 0
        failed_count = 0
        errors = []

        for empfaenger in to_send:
            try:
                result = self.send_to_empfaenger(mailing, empfaenger)
                if result.success:
                    sent_count += 1
                else:
                    failed_count += 1
                    errors.append(f'{empfaenger.kunde.firmierung}: {result.error}')
            except Exception as e:
                failed_count += 1
                errors.append(f'{empfaenger.kunde.firmierung}: {str(e)}')

        # Update mailing statistics
        mailing.update_statistik()

        # Update mailing status if any sent
        if mailing.anzahl_ausstehend == 0:
            mailing.status = MailingStatus.VERSENDET.value
        elif sent_count > 0 and mailing.status == MailingStatus.ENTWURF.value:
            mailing.status = MailingStatus.VERSENDET.value

        db.session.commit()

        return VersandResult(
            success=failed_count == 0,
            sent_count=sent_count,
            failed_count=failed_count,
            pending_count=mailing.anzahl_ausstehend,
            errors=errors
        )

    # ========== Zielgruppen ==========

    def create_zielgruppe(
        self,
        name: str,
        filter_json: Dict[str, Any],
        erstellt_von_id: int,
        beschreibung: str = None
    ) -> MailingZielgruppe:
        """Create a new saved target group."""
        zielgruppe = MailingZielgruppe(
            name=name,
            filter_json=filter_json,
            beschreibung=beschreibung,
            erstellt_von_id=erstellt_von_id
        )
        db.session.add(zielgruppe)
        db.session.commit()
        return zielgruppe

    def get_all_zielgruppen(self) -> List[MailingZielgruppe]:
        """Get all saved target groups."""
        return MailingZielgruppe.query.order_by(MailingZielgruppe.name).all()


# Factory function for service instantiation
_mailing_service = None


def get_mailing_service() -> MailingService:
    """Get or create the MailingService singleton."""
    global _mailing_service
    if _mailing_service is None:
        _mailing_service = MailingService()
    return _mailing_service
