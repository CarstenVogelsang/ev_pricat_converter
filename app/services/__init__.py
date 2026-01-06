"""Service modules for pricat-converter."""
from app.services.pricat_parser import PricatParser, PricatData, ArticleData
from app.services.elena_exporter import ElenaExporter, ExportResult, generate_elena_filename
from app.services.image_downloader import ImageDownloader, DownloadResult, get_image_target_dir
from app.services.xlsx_exporter import XlsxExporter, XlsxExportResult, generate_xlsx_filename
from app.services.ftp_service import FTPService, FTPConfig, FTPResult
from app.services.import_trigger import ImportTrigger, ImportResult
from app.services.processor import Processor, ProcessingResult, ProcessingStep
from app.services.storage_service import StorageService, S3Storage, LocalStorage, S3Config
from app.services.branding_service import BrandingService, BrandingConfig
from app.services.firecrawl_service import FirecrawlService, FirecrawlResult
from app.services.logging_service import log_event, log_kritisch, log_hoch, log_mittel

# Kunden-Dialog Module (PRD-006)
from app.services.email_service import BrevoService, EmailResult, get_brevo_service, QuotaExceededError
from app.services.email_template_service import (
    EmailTemplateService, get_email_template_service
)
from app.services.password_service import (
    PasswordService, UserCreationResult, CredentialsSendResult, get_password_service
)
from app.services.fragebogen_service import (
    FragebogenService, ValidationResult, EinladungResult, get_fragebogen_service
)

# Anwender-Support Module (PRD-007)
from app.services.support_service import SupportService, get_support_service

# Schulungen Module (PRD-010)
from app.services.schulung_service import (
    SchulungService, BuchungResult, StornoResult, get_schulung_service
)

__all__ = [
    # Parser
    'PricatParser', 'PricatData', 'ArticleData',
    # Elena Exporter
    'ElenaExporter', 'ExportResult', 'generate_elena_filename',
    # Image Downloader
    'ImageDownloader', 'DownloadResult', 'get_image_target_dir',
    # XLSX Exporter
    'XlsxExporter', 'XlsxExportResult', 'generate_xlsx_filename',
    # FTP Service
    'FTPService', 'FTPConfig', 'FTPResult',
    # Import Trigger
    'ImportTrigger', 'ImportResult',
    # Processor
    'Processor', 'ProcessingResult', 'ProcessingStep',
    # Storage Service
    'StorageService', 'S3Storage', 'LocalStorage', 'S3Config',
    # Branding Service
    'BrandingService', 'BrandingConfig',
    # Firecrawl Service
    'FirecrawlService', 'FirecrawlResult',
    # Logging Service
    'log_event', 'log_kritisch', 'log_hoch', 'log_mittel',
    # Kunden-Dialog Module (PRD-006)
    'BrevoService', 'EmailResult', 'get_brevo_service', 'QuotaExceededError',
    'EmailTemplateService', 'get_email_template_service',
    'PasswordService', 'UserCreationResult', 'CredentialsSendResult', 'get_password_service',
    'FragebogenService', 'ValidationResult', 'EinladungResult', 'get_fragebogen_service',
    # Anwender-Support Module (PRD-007)
    'SupportService', 'get_support_service',
    # Schulungen Module (PRD-010)
    'SchulungService', 'BuchungResult', 'StornoResult', 'get_schulung_service',
]
