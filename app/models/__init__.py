"""Database models."""
from app.models.lieferant import Lieferant
from app.models.hersteller import Hersteller
from app.models.marke import Marke
from app.models.config import Config
from app.models.rolle import Rolle
from app.models.user import User, UserTyp
from app.models.kunde import Kunde, KundeCI, KundeTyp
from app.models.kunde_benutzer import KundeBenutzer
from app.models.api_nutzung import KundeApiNutzung
from app.models.branche import Branche
from app.models.verband import Verband
from app.models.kunde_branche import KundeBranche
from app.models.kunde_verband import KundeVerband
from app.models.lieferant_branche import LieferantBranche
from app.models.help_text import HelpText

# Branchenmodell V2: Rollen-System
from app.models.branchenrolle import BranchenRolle
from app.models.branche_branchenrolle import BrancheBranchenRolle
from app.models.kunde_branchenrolle import KundeBranchenRolle

# Audit-Log System & Module Management
from app.models.modul import Modul, ModulZugriff, ModulTyp
from app.models.audit_log import AuditLog

# Kunden-Dialog Module (PRD-006)
from app.models.password_token import PasswordToken
from app.models.fragebogen import (
    Fragebogen, FragebogenTeilnahme, FragebogenAntwort,
    FragebogenStatus, TeilnahmeStatus
)

# Email Templates
from app.models.email_template import EmailTemplate

# Generic Key-Value Storage
from app.models.lookup_wert import LookupWert

# Anwender-Support Module (PRD-007)
from app.models.support_team import SupportTeam, SupportTeamMitglied
from app.models.support_ticket import (
    SupportTicket, TicketKommentar,
    TicketTyp, TicketStatus, TicketPrioritaet
)

# Produktdaten Module (PRD-009)
from app.models.produkt_lookup import ProduktLookup
from app.models.attributgruppe import Attributgruppe
from app.models.eigenschaft_definition import EigenschaftDefinition, DatenTyp
from app.models.produkt import Produkt, ProduktStatus
from app.models.eigenschaft_wert import EigenschaftWert

# Schulungen Module (PRD-010)
from app.models.schulungsthema import Schulungsthema
from app.models.schulung import Schulung, SchulungThema
from app.models.schulungsdurchfuehrung import (
    Schulungsdurchfuehrung, Schulungstermin, DurchfuehrungStatus
)
from app.models.schulungsbuchung import Schulungsbuchung, BuchungStatus

# Projektverwaltung Module (PRD-011)
from app.models.projekt import Projekt, ProjektTyp
from app.models.komponente import (
    Komponente, KomponenteTyp, KomponentePhase, KomponenteStatus
)
from app.models.task import Task, TaskStatus, TaskPrioritaet, TaskPhase
from app.models.changelog_eintrag import (
    ChangelogEintrag, ChangelogKategorie, ChangelogSichtbarkeit
)
from app.models.modul_erp import ModulErp, ModulErpKontext
from app.models.task_kommentar import TaskKommentar, KommentarTyp

# Kunden-Mailing Module (PRD-013)
from app.models.mailing import (
    Mailing, MailingEmpfaenger, MailingKlick, MailingZielgruppe,
    MailingStatus, EmpfaengerStatus
)

# Global Media Library
from app.models.medium import Medium, MediumTyp

# Admin Page Visit Tracking
from app.models.page_visit import AdminPageVisit

__all__ = [
    'Lieferant', 'Hersteller', 'Marke', 'Config',
    'Rolle', 'User', 'UserTyp',
    'Kunde', 'KundeCI', 'KundeTyp', 'KundeBenutzer',
    'KundeApiNutzung',
    'Branche', 'Verband',
    'KundeBranche', 'KundeVerband', 'LieferantBranche',
    'HelpText',
    # Branchenmodell V2
    'BranchenRolle', 'BrancheBranchenRolle', 'KundeBranchenRolle',
    # Audit-Log System & Module Management
    'Modul', 'ModulZugriff', 'ModulTyp', 'AuditLog',
    # Kunden-Dialog Module (PRD-006)
    'PasswordToken',
    'Fragebogen', 'FragebogenTeilnahme', 'FragebogenAntwort',
    'FragebogenStatus', 'TeilnahmeStatus',
    # Email Templates
    'EmailTemplate',
    # Generic Key-Value Storage
    'LookupWert',
    # Anwender-Support Module (PRD-007)
    'SupportTeam', 'SupportTeamMitglied',
    'SupportTicket', 'TicketKommentar',
    'TicketTyp', 'TicketStatus', 'TicketPrioritaet',
    # Produktdaten Module (PRD-009)
    'ProduktLookup', 'Attributgruppe',
    'EigenschaftDefinition', 'DatenTyp',
    'Produkt', 'ProduktStatus',
    'EigenschaftWert',
    # Schulungen Module (PRD-010)
    'Schulungsthema',
    'Schulung', 'SchulungThema',
    'Schulungsdurchfuehrung', 'Schulungstermin', 'DurchfuehrungStatus',
    'Schulungsbuchung', 'BuchungStatus',
    # Projektverwaltung Module (PRD-011)
    'Projekt', 'ProjektTyp',
    'Komponente', 'KomponenteTyp', 'KomponentePhase', 'KomponenteStatus',
    'Task', 'TaskStatus', 'TaskPrioritaet', 'TaskPhase',
    'ChangelogEintrag', 'ChangelogKategorie', 'ChangelogSichtbarkeit',
    'ModulErp', 'ModulErpKontext',
    'TaskKommentar', 'KommentarTyp',
    # Kunden-Mailing Module (PRD-013)
    'Mailing', 'MailingEmpfaenger', 'MailingKlick', 'MailingZielgruppe',
    'MailingStatus', 'EmpfaengerStatus',
    # Global Media Library
    'Medium', 'MediumTyp',
    # Admin Page Visit Tracking
    'AdminPageVisit',
]
