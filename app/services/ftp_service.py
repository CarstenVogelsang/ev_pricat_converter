"""FTP Service for PRICAT download and Elena upload.

Handles FTP connections to:
- VEDES FTP server (download PRICAT files)
- Target FTP server (upload Elena CSV + images)
"""
import ftplib
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from app import db
from app.models import Lieferant, Config
from app.utils import parse_pricat_filename


@dataclass
class FTPResult:
    """Result of FTP operation."""
    success: bool
    message: str = ''
    local_path: Optional[Path] = None
    remote_path: Optional[str] = None
    bytes_transferred: int = 0
    errors: list = field(default_factory=list)


@dataclass
class FTPConfig:
    """FTP connection configuration."""
    host: str
    user: str
    password: str
    basepath: str = '/'
    port: int = 21
    timeout: int = 30
    passive: bool = True


class FTPService:
    """Service for FTP operations."""

    def __init__(self, config: FTPConfig = None):
        """
        Initialize FTP service.

        Args:
            config: Optional FTPConfig, otherwise loaded from database
        """
        self.config = config
        self._ftp = None

    def _get_config_value(self, key: str) -> str:
        """Get configuration value from database."""
        config_entry = Config.query.filter_by(key=key).first()
        return config_entry.value if config_entry else ''

    def _load_vedes_config(self) -> FTPConfig:
        """Load VEDES FTP configuration from database."""
        port_str = self._get_config_value('vedes_ftp_port')
        port = int(port_str) if port_str and port_str.isdigit() else 21
        return FTPConfig(
            host=self._get_config_value('vedes_ftp_host'),
            user=self._get_config_value('vedes_ftp_user'),
            password=self._get_config_value('vedes_ftp_pass'),
            basepath=self._get_config_value('vedes_ftp_basepath') or '/pricat/',
            port=port
        )

    def _load_elena_config(self) -> FTPConfig:
        """Load Elena/Target FTP configuration from database."""
        port_str = self._get_config_value('elena_ftp_port')
        port = int(port_str) if port_str and port_str.isdigit() else 21
        return FTPConfig(
            host=self._get_config_value('elena_ftp_host'),
            user=self._get_config_value('elena_ftp_user'),
            password=self._get_config_value('elena_ftp_pass'),
            basepath='/',
            port=port
        )

    def _connect(self, config: FTPConfig) -> ftplib.FTP:
        """
        Establish FTP connection.

        Args:
            config: FTP configuration

        Returns:
            Connected FTP object

        Raises:
            ftplib.error_perm: Authentication failed
            ConnectionError: Connection failed
        """
        if not config.host:
            raise ValueError("FTP host not configured")

        ftp = ftplib.FTP()
        ftp.set_pasv(config.passive)

        try:
            ftp.connect(config.host, config.port, config.timeout)
            ftp.login(config.user, config.password)
            return ftp
        except ftplib.error_perm as e:
            raise ConnectionError(f"FTP authentication failed: {e}")
        except Exception as e:
            raise ConnectionError(f"FTP connection failed: {e}")

    def _disconnect(self, ftp: ftplib.FTP) -> None:
        """Safely disconnect FTP."""
        try:
            ftp.quit()
        except Exception:
            try:
                ftp.close()
            except Exception:
                pass

    def download_pricat(
        self,
        lieferant: Lieferant,
        target_dir: Path,
        config: FTPConfig = None
    ) -> FTPResult:
        """
        Download PRICAT file for a supplier from VEDES FTP.

        Args:
            lieferant: Supplier entity with ftp_pfad_quelle
            target_dir: Local directory to save file
            config: Optional FTP config, otherwise loaded from DB

        Returns:
            FTPResult with download status
        """
        result = FTPResult(success=False)

        # Get FTP config
        ftp_config = config or self._load_vedes_config()

        if not ftp_config.host:
            result.message = "VEDES FTP not configured"
            result.errors.append(result.message)
            return result

        # Determine remote path from ftp_quelldatei (just filename)
        if lieferant.ftp_quelldatei:
            # Combine basepath with filename
            remote_path = f"{ftp_config.basepath.rstrip('/')}/{lieferant.ftp_quelldatei}"
        else:
            result.message = "No FTP source file configured for supplier"
            result.errors.append(result.message)
            return result

        # Generate local filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"pricat_{lieferant.vedes_id}_{timestamp}.csv"
        local_path = target_dir / filename

        # Ensure target directory exists
        target_dir.mkdir(parents=True, exist_ok=True)

        ftp = None
        try:
            # Connect
            ftp = self._connect(ftp_config)

            # Download file
            with open(local_path, 'wb') as f:
                def callback(data):
                    f.write(data)
                    result.bytes_transferred += len(data)

                ftp.retrbinary(f'RETR {remote_path}', callback)

            result.success = True
            result.local_path = local_path
            result.remote_path = remote_path
            result.message = f"Downloaded {result.bytes_transferred:,} bytes"

        except ftplib.error_perm as e:
            result.message = f"FTP permission error: {e}"
            result.errors.append(result.message)
            # Clean up partial file
            if local_path.exists():
                local_path.unlink()
        except Exception as e:
            result.message = f"Download failed: {e}"
            result.errors.append(result.message)
            if local_path.exists():
                local_path.unlink()
        finally:
            if ftp:
                self._disconnect(ftp)

        return result

    def upload_file(
        self,
        local_path: Path,
        remote_dir: str,
        config: FTPConfig = None,
        remote_filename: str = None
    ) -> FTPResult:
        """
        Upload a single file to target FTP.

        Args:
            local_path: Local file path
            remote_dir: Remote directory
            config: Optional FTP config
            remote_filename: Optional remote filename (defaults to local filename)

        Returns:
            FTPResult with upload status
        """
        result = FTPResult(success=False)

        ftp_config = config or self._load_elena_config()

        if not ftp_config.host:
            result.message = "Target FTP not configured"
            result.errors.append(result.message)
            return result

        if not local_path.exists():
            result.message = f"Local file not found: {local_path}"
            result.errors.append(result.message)
            return result

        filename = remote_filename or local_path.name
        remote_path = f"{remote_dir.rstrip('/')}/{filename}"

        ftp = None
        try:
            ftp = self._connect(ftp_config)

            # Create remote directory if needed
            self._ensure_remote_dir(ftp, remote_dir)

            # Upload file
            with open(local_path, 'rb') as f:
                ftp.storbinary(f'STOR {remote_path}', f)

            result.success = True
            result.local_path = local_path
            result.remote_path = remote_path
            result.bytes_transferred = local_path.stat().st_size
            result.message = f"Uploaded {result.bytes_transferred:,} bytes"

        except ftplib.error_perm as e:
            result.message = f"FTP permission error: {e}"
            result.errors.append(result.message)
        except Exception as e:
            result.message = f"Upload failed: {e}"
            result.errors.append(result.message)
        finally:
            if ftp:
                self._disconnect(ftp)

        return result

    def _ensure_remote_dir(self, ftp: ftplib.FTP, remote_dir: str) -> None:
        """Create remote directory if it doesn't exist."""
        dirs = remote_dir.strip('/').split('/')
        current = ''

        for d in dirs:
            if not d:
                continue
            current = f"{current}/{d}"
            try:
                ftp.cwd(current)
            except ftplib.error_perm:
                try:
                    ftp.mkd(current)
                except ftplib.error_perm:
                    pass  # Directory might already exist

        # Return to root
        ftp.cwd('/')

    def upload_elena_package(
        self,
        lieferant: Lieferant,
        csv_path: Path,
        images_dir: Path = None,
        config: FTPConfig = None
    ) -> FTPResult:
        """
        Upload Elena CSV and optionally images to target FTP.

        Args:
            lieferant: Supplier entity with ftp_pfad_ziel
            csv_path: Path to Elena CSV file
            images_dir: Optional directory with images to upload
            config: Optional FTP config

        Returns:
            FTPResult with upload status
        """
        result = FTPResult(success=False)

        ftp_config = config or self._load_elena_config()

        if not ftp_config.host:
            result.message = "Target FTP not configured"
            result.errors.append(result.message)
            return result

        # Determine remote directory
        remote_dir = lieferant.ftp_pfad_ziel or f"/{lieferant.elena_startdir or lieferant.vedes_id}"

        ftp = None
        try:
            ftp = self._connect(ftp_config)

            # Ensure remote directory exists
            self._ensure_remote_dir(ftp, remote_dir)

            # Upload CSV
            csv_remote = f"{remote_dir.rstrip('/')}/{csv_path.name}"
            with open(csv_path, 'rb') as f:
                ftp.storbinary(f'STOR {csv_remote}', f)
            result.bytes_transferred += csv_path.stat().st_size

            # Upload images if provided
            images_uploaded = 0
            if images_dir and images_dir.exists():
                images_remote_dir = f"{remote_dir.rstrip('/')}/images"
                self._ensure_remote_dir(ftp, images_remote_dir)

                for img_file in images_dir.glob('*'):
                    if img_file.is_file() and img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                        img_remote = f"{images_remote_dir}/{img_file.name}"
                        try:
                            with open(img_file, 'rb') as f:
                                ftp.storbinary(f'STOR {img_remote}', f)
                            result.bytes_transferred += img_file.stat().st_size
                            images_uploaded += 1
                        except Exception as e:
                            result.errors.append(f"Failed to upload {img_file.name}: {e}")

            result.success = True
            result.local_path = csv_path
            result.remote_path = csv_remote
            result.message = f"Uploaded CSV + {images_uploaded} images ({result.bytes_transferred:,} bytes)"

        except ftplib.error_perm as e:
            result.message = f"FTP permission error: {e}"
            result.errors.append(result.message)
        except Exception as e:
            result.message = f"Upload failed: {e}"
            result.errors.append(result.message)
        finally:
            if ftp:
                self._disconnect(ftp)

        return result

    def list_pricat_files(
        self,
        directory: str = None,
        config: FTPConfig = None
    ) -> list[str]:
        """
        List PRICAT files on VEDES FTP.

        Args:
            directory: Remote directory to list
            config: Optional FTP config

        Returns:
            List of filenames
        """
        ftp_config = config or self._load_vedes_config()

        if not ftp_config.host:
            return []

        remote_dir = directory or ftp_config.basepath

        ftp = None
        try:
            ftp = self._connect(ftp_config)
            ftp.cwd(remote_dir)

            files = []
            ftp.retrlines('NLST', files.append)

            # Filter for CSV files
            return [f for f in files if f.lower().endswith('.csv')]

        except Exception:
            return []
        finally:
            if ftp:
                self._disconnect(ftp)

    def test_connection(self, config: FTPConfig = None, target: str = 'vedes') -> FTPResult:
        """
        Test FTP connection.

        Args:
            config: Optional FTP config
            target: 'vedes' or 'elena'

        Returns:
            FTPResult with connection status
        """
        result = FTPResult(success=False)

        if config:
            ftp_config = config
        elif target == 'elena':
            ftp_config = self._load_elena_config()
        else:
            ftp_config = self._load_vedes_config()

        if not ftp_config.host:
            result.message = f"{target.upper()} FTP not configured"
            return result

        ftp = None
        try:
            ftp = self._connect(ftp_config)
            result.success = True
            result.message = f"Connected to {ftp_config.host}"
        except Exception as e:
            result.message = str(e)
            result.errors.append(result.message)
        finally:
            if ftp:
                self._disconnect(ftp)

        return result

    def sync_lieferanten(self, config: FTPConfig = None) -> dict:
        """
        Synchronize Lieferanten table with PRICAT files on VEDES FTP.

        Scans the PRICAT directory, parses filenames to extract VEDES_ID
        and supplier names, and creates missing Lieferanten entries (inactive).

        Args:
            config: Optional FTP config, otherwise loaded from DB

        Returns:
            dict with sync results:
            - success: bool
            - message: str
            - created: list of created supplier names
            - updated: list of updated supplier names
            - unchanged: list of unchanged supplier names
            - errors: list of error messages
        """
        sync_result = {
            'success': False,
            'message': '',
            'created': [],
            'updated': [],
            'unchanged': [],
            'errors': []
        }

        ftp_config = config or self._load_vedes_config()

        if not ftp_config.host:
            sync_result['message'] = "VEDES FTP not configured"
            sync_result['errors'].append(sync_result['message'])
            return sync_result

        ftp = None
        try:
            ftp = self._connect(ftp_config)
            ftp.cwd(ftp_config.basepath)

            # List all CSV files
            files = []
            ftp.retrlines('NLST', files.append)
            csv_files = [f for f in files if f.lower().endswith('.csv')]

            for filename in csv_files:
                parsed = parse_pricat_filename(filename)
                if not parsed:
                    sync_result['errors'].append(f"Could not parse filename: {filename}")
                    continue

                vedes_id, supplier_name = parsed

                # Check if supplier exists
                existing = Lieferant.query.filter_by(vedes_id=vedes_id).first()

                if existing:
                    # Update filename if changed
                    if existing.ftp_quelldatei != filename:
                        existing.ftp_quelldatei = filename
                        sync_result['updated'].append(f"{supplier_name} (ID: {vedes_id})")
                    else:
                        sync_result['unchanged'].append(f"{supplier_name} (ID: {vedes_id})")
                else:
                    # Create new inactive supplier
                    new_lieferant = Lieferant(
                        vedes_id=vedes_id,
                        gln=None,  # Will be filled from PRICAT later
                        kurzbezeichnung=supplier_name[:40],  # Max 40 chars
                        aktiv=False,
                        ftp_quelldatei=filename
                    )
                    db.session.add(new_lieferant)
                    sync_result['created'].append(f"{supplier_name} (ID: {vedes_id})")

            db.session.commit()
            sync_result['success'] = True
            sync_result['message'] = (
                f"Sync completed: {len(sync_result['created'])} created, "
                f"{len(sync_result['updated'])} updated, "
                f"{len(sync_result['unchanged'])} unchanged"
            )

        except Exception as e:
            sync_result['message'] = f"Sync failed: {e}"
            sync_result['errors'].append(sync_result['message'])
            db.session.rollback()
        finally:
            if ftp:
                self._disconnect(ftp)

        return sync_result
