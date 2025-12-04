"""End-to-end Processing Orchestrator.

Coordinates the complete PRICAT to Elena conversion workflow:
1. Download PRICAT from VEDES FTP (or use local file)
2. Parse PRICAT CSV
3. Extract entities (Lieferant, Hersteller, Marken)
4. Download product images
5. Generate Elena CSV
6. Generate XLSX report
7. Upload to target FTP
8. Trigger Elena import
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from flask import current_app

from app import db
from app.models import Lieferant, Hersteller, Marke
from app.services.pricat_parser import PricatParser, PricatData
from app.services.elena_exporter import ElenaExporter, generate_elena_filename
from app.services.image_downloader import ImageDownloader, get_image_target_dir
from app.services.xlsx_exporter import XlsxExporter, generate_xlsx_filename
from app.services.ftp_service import FTPService
from app.services.import_trigger import ImportTrigger


class ProcessingStep(Enum):
    """Processing workflow steps."""
    DOWNLOAD_PRICAT = 1
    PARSE_PRICAT = 2
    EXTRACT_ENTITIES = 3
    DOWNLOAD_IMAGES = 4
    EXPORT_ELENA = 5
    EXPORT_XLSX = 6
    UPLOAD_FTP = 7
    TRIGGER_IMPORT = 8
    COMPLETED = 9


@dataclass
class StepResult:
    """Result of a single processing step."""
    step: ProcessingStep
    success: bool
    message: str = ''
    details: dict = field(default_factory=dict)


@dataclass
class ProcessingResult:
    """Complete processing result."""
    success: bool
    lieferant_id: int = 0
    current_step: ProcessingStep = ProcessingStep.DOWNLOAD_PRICAT
    steps: list = field(default_factory=list)  # list[StepResult]
    errors: list = field(default_factory=list)

    # Output paths
    pricat_path: Optional[Path] = None
    elena_csv_path: Optional[Path] = None
    xlsx_path: Optional[Path] = None
    images_dir: Optional[Path] = None

    # Statistics
    articles_count: int = 0
    hersteller_count: int = 0
    marken_count: int = 0
    images_downloaded: int = 0

    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def add_step(self, step_result: StepResult):
        """Add a step result."""
        self.steps.append(step_result)
        self.current_step = step_result.step
        if not step_result.success:
            self.errors.append(f"{step_result.step.name}: {step_result.message}")

    @property
    def progress_percent(self) -> int:
        """Calculate progress percentage."""
        total_steps = len(ProcessingStep) - 1  # Exclude COMPLETED
        current = self.current_step.value
        return min(int((current / total_steps) * 100), 100)


# Type alias for progress callback
ProgressCallback = Callable[[ProcessingStep, str, int], None]


class Processor:
    """Orchestrates the complete PRICAT to Elena conversion."""

    def __init__(
        self,
        skip_ftp_download: bool = False,
        skip_image_download: bool = False,
        skip_ftp_upload: bool = False,
        skip_import_trigger: bool = False,
        progress_callback: ProgressCallback = None
    ):
        """
        Initialize processor.

        Args:
            skip_ftp_download: Use local PRICAT file instead of FTP download
            skip_image_download: Skip image downloading
            skip_ftp_upload: Skip uploading to target FTP
            skip_import_trigger: Skip triggering Elena import
            progress_callback: Optional callback for progress updates
        """
        self.skip_ftp_download = skip_ftp_download
        self.skip_image_download = skip_image_download
        self.skip_ftp_upload = skip_ftp_upload
        self.skip_import_trigger = skip_import_trigger
        self.progress_callback = progress_callback

        # Services
        self.parser = PricatParser()
        self.elena_exporter = ElenaExporter()
        self.xlsx_exporter = XlsxExporter()
        self.image_downloader = ImageDownloader()
        self.ftp_service = FTPService()
        self.import_trigger = ImportTrigger()

    def _notify_progress(self, step: ProcessingStep, message: str, percent: int = None):
        """Notify progress callback if set."""
        if self.progress_callback:
            if percent is None:
                total_steps = len(ProcessingStep) - 1
                percent = int((step.value / total_steps) * 100)
            self.progress_callback(step, message, percent)

    def process(
        self,
        lieferant: Lieferant,
        local_pricat_path: Path = None
    ) -> ProcessingResult:
        """
        Execute complete processing workflow.

        Args:
            lieferant: Supplier to process
            local_pricat_path: Optional local PRICAT file (skips FTP download)

        Returns:
            ProcessingResult with complete status
        """
        result = ProcessingResult(success=False, lieferant_id=lieferant.id)

        # Get config paths
        imports_dir = current_app.config['IMPORTS_DIR']
        exports_dir = current_app.config['EXPORTS_DIR']
        images_base_dir = current_app.config['IMAGES_DIR']

        pricat_data = None
        marke_lookup = {}

        try:
            # Step 1: Download or load PRICAT
            self._notify_progress(ProcessingStep.DOWNLOAD_PRICAT, "PRICAT laden...")

            if local_pricat_path and local_pricat_path.exists():
                result.pricat_path = local_pricat_path
                step_result = StepResult(
                    step=ProcessingStep.DOWNLOAD_PRICAT,
                    success=True,
                    message=f"Lokale Datei verwendet: {local_pricat_path.name}"
                )
            elif self.skip_ftp_download:
                # Try to find existing PRICAT in imports
                existing = list(imports_dir.glob(f"pricat_{lieferant.vedes_id}_*.csv"))
                if existing:
                    result.pricat_path = sorted(existing)[-1]  # Latest
                    step_result = StepResult(
                        step=ProcessingStep.DOWNLOAD_PRICAT,
                        success=True,
                        message=f"Existierende Datei: {result.pricat_path.name}"
                    )
                else:
                    step_result = StepResult(
                        step=ProcessingStep.DOWNLOAD_PRICAT,
                        success=False,
                        message="Keine lokale PRICAT-Datei gefunden"
                    )
            else:
                ftp_result = self.ftp_service.download_pricat(lieferant, imports_dir)
                if ftp_result.success:
                    result.pricat_path = ftp_result.local_path
                    step_result = StepResult(
                        step=ProcessingStep.DOWNLOAD_PRICAT,
                        success=True,
                        message=f"Heruntergeladen: {ftp_result.bytes_transferred:,} Bytes",
                        details={'bytes': ftp_result.bytes_transferred}
                    )
                else:
                    step_result = StepResult(
                        step=ProcessingStep.DOWNLOAD_PRICAT,
                        success=False,
                        message=ftp_result.message
                    )

            result.add_step(step_result)
            if not step_result.success:
                return result

            # Step 2: Parse PRICAT
            self._notify_progress(ProcessingStep.PARSE_PRICAT, "PRICAT parsen...")

            pricat_data = self.parser.parse(result.pricat_path)
            result.articles_count = len(pricat_data.articles)

            if pricat_data.errors:
                step_result = StepResult(
                    step=ProcessingStep.PARSE_PRICAT,
                    success=len(pricat_data.articles) > 0,
                    message=f"{result.articles_count} Artikel, {len(pricat_data.errors)} Fehler",
                    details={'errors': pricat_data.errors[:5]}
                )
            else:
                step_result = StepResult(
                    step=ProcessingStep.PARSE_PRICAT,
                    success=True,
                    message=f"{result.articles_count} Artikel geparst"
                )

            result.add_step(step_result)
            if not step_result.success:
                return result

            # Step 3: Extract entities
            self._notify_progress(ProcessingStep.EXTRACT_ENTITIES, "Entitäten extrahieren...")

            lieferant_updated, hersteller_list, marken_list = self.parser.extract_entities(pricat_data)
            result.hersteller_count = len(hersteller_list)
            result.marken_count = len(marken_list)

            # Build marke lookup for Elena export
            for m in marken_list:
                h = m.hersteller
                marke_lookup[(h.gln, m.kurzbezeichnung)] = m.gln_evendo

            step_result = StepResult(
                step=ProcessingStep.EXTRACT_ENTITIES,
                success=True,
                message=f"{result.hersteller_count} Hersteller, {result.marken_count} Marken"
            )
            result.add_step(step_result)

            # Step 4: Download images
            self._notify_progress(ProcessingStep.DOWNLOAD_IMAGES, "Bilder herunterladen...")

            if self.skip_image_download:
                step_result = StepResult(
                    step=ProcessingStep.DOWNLOAD_IMAGES,
                    success=True,
                    message="Übersprungen"
                )
            else:
                image_urls = self.parser.get_image_urls(pricat_data)
                result.images_dir = get_image_target_dir(
                    images_base_dir,
                    lieferant.vedes_id,
                    lieferant.kurzbezeichnung
                )

                dl_result = self.image_downloader.download_all(image_urls, result.images_dir)
                result.images_downloaded = dl_result.stats.success

                step_result = StepResult(
                    step=ProcessingStep.DOWNLOAD_IMAGES,
                    success=True,  # Partial success is OK
                    message=f"{dl_result.stats.success}/{dl_result.stats.total} Bilder",
                    details={
                        'success': dl_result.stats.success,
                        'failed': dl_result.stats.failed,
                        'skipped': dl_result.stats.skipped
                    }
                )

            result.add_step(step_result)

            # Step 5: Export Elena CSV
            self._notify_progress(ProcessingStep.EXPORT_ELENA, "Elena-CSV generieren...")

            elena_filename = generate_elena_filename(lieferant.vedes_id)
            result.elena_csv_path = exports_dir / elena_filename

            export_result = self.elena_exporter.export(
                pricat_data,
                result.elena_csv_path,
                marke_lookup
            )

            step_result = StepResult(
                step=ProcessingStep.EXPORT_ELENA,
                success=export_result.success,
                message=f"{export_result.rows_exported} Zeilen exportiert" if export_result.success else export_result.errors[0] if export_result.errors else "Export fehlgeschlagen"
            )
            result.add_step(step_result)
            if not step_result.success:
                return result

            # Step 6: Export XLSX
            self._notify_progress(ProcessingStep.EXPORT_XLSX, "XLSX erstellen...")

            xlsx_filename = generate_xlsx_filename(lieferant.vedes_id)
            result.xlsx_path = exports_dir / xlsx_filename

            xlsx_result = self.xlsx_exporter.export_entities(
                lieferant,
                hersteller_list,
                marken_list,
                result.xlsx_path,
                article_count=result.articles_count
            )

            step_result = StepResult(
                step=ProcessingStep.EXPORT_XLSX,
                success=xlsx_result.success,
                message=f"{xlsx_result.sheets_created} Sheets erstellt" if xlsx_result.success else xlsx_result.errors[0] if xlsx_result.errors else "Export fehlgeschlagen"
            )
            result.add_step(step_result)

            # Step 7: Upload to FTP
            self._notify_progress(ProcessingStep.UPLOAD_FTP, "FTP-Upload...")

            if self.skip_ftp_upload:
                step_result = StepResult(
                    step=ProcessingStep.UPLOAD_FTP,
                    success=True,
                    message="Übersprungen"
                )
            else:
                upload_result = self.ftp_service.upload_elena_package(
                    lieferant,
                    result.elena_csv_path,
                    result.images_dir
                )
                step_result = StepResult(
                    step=ProcessingStep.UPLOAD_FTP,
                    success=upload_result.success,
                    message=upload_result.message
                )

            result.add_step(step_result)
            if not step_result.success and not self.skip_ftp_upload:
                return result

            # Step 8: Trigger import
            self._notify_progress(ProcessingStep.TRIGGER_IMPORT, "Import auslösen...")

            if self.skip_import_trigger:
                step_result = StepResult(
                    step=ProcessingStep.TRIGGER_IMPORT,
                    success=True,
                    message="Übersprungen"
                )
            else:
                import_result = self.import_trigger.trigger_for_lieferant(
                    lieferant,
                    result.elena_csv_path.name
                )
                step_result = StepResult(
                    step=ProcessingStep.TRIGGER_IMPORT,
                    success=import_result.success,
                    message=f"HTTP {import_result.status_code}" if import_result.status_code else import_result.errors[0] if import_result.errors else "Unbekannter Fehler",
                    details={'url': import_result.url, 'status': import_result.status_code}
                )

            result.add_step(step_result)

            # Update lieferant
            lieferant.letzte_konvertierung = datetime.now()
            db.session.commit()

            # Mark as completed
            result.success = True
            result.current_step = ProcessingStep.COMPLETED
            result.completed_at = datetime.now()

            self._notify_progress(ProcessingStep.COMPLETED, "Abgeschlossen", 100)

        except Exception as e:
            result.errors.append(f"Unerwarteter Fehler: {str(e)}")
            step_result = StepResult(
                step=result.current_step,
                success=False,
                message=str(e)
            )
            result.add_step(step_result)

        return result

    def process_local(
        self,
        lieferant: Lieferant,
        pricat_path: Path
    ) -> ProcessingResult:
        """
        Process using a local PRICAT file (no FTP operations).

        Args:
            lieferant: Supplier to process
            pricat_path: Path to local PRICAT file

        Returns:
            ProcessingResult
        """
        # Disable all network operations
        self.skip_ftp_download = True
        self.skip_ftp_upload = True
        self.skip_import_trigger = True
        self.skip_image_download = True

        return self.process(lieferant, local_pricat_path=pricat_path)
