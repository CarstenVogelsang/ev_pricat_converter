"""Storage service for file operations - S3 or local filesystem."""
import base64
import io
import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from flask import current_app
from PIL import Image
from werkzeug.utils import secure_filename

from app import db
from app.models import Config


# Markdown image upload settings
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_IMAGE_WIDTH = 1200
MAX_IMAGE_SIZE_MB = 5


@dataclass
class S3Config:
    """S3 configuration."""
    endpoint: str
    access_key: str
    secret_key: str
    bucket: str
    enabled: bool = False


class StorageBackend(ABC):
    """Abstract storage backend interface."""

    @abstractmethod
    def upload(self, key: str, data: bytes, content_type: str = 'application/octet-stream') -> str:
        """Upload file, return URL/path."""
        pass

    @abstractmethod
    def download(self, key: str) -> Optional[bytes]:
        """Download file content. Returns None if not found."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if file exists."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete file. Returns True if deleted."""
        pass

    @abstractmethod
    def list_files(self, prefix: str = '') -> list[str]:
        """List files with prefix."""
        pass


class LocalStorage(StorageBackend):
    """Local filesystem storage backend."""

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_path(self, key: str) -> Path:
        """Get full path for key."""
        return self.base_path / key

    def upload(self, key: str, data: bytes, content_type: str = 'application/octet-stream') -> str:
        """Upload file to local filesystem."""
        path = self._get_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    def download(self, key: str) -> Optional[bytes]:
        """Download file from local filesystem."""
        path = self._get_path(key)
        if path.exists():
            return path.read_bytes()
        return None

    def exists(self, key: str) -> bool:
        """Check if file exists locally."""
        return self._get_path(key).exists()

    def delete(self, key: str) -> bool:
        """Delete file from local filesystem."""
        path = self._get_path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_files(self, prefix: str = '') -> list[str]:
        """List files with prefix."""
        search_path = self.base_path / prefix if prefix else self.base_path
        if not search_path.exists():
            return []

        if search_path.is_file():
            return [prefix]

        results = []
        for path in search_path.rglob('*'):
            if path.is_file():
                relative = path.relative_to(self.base_path)
                results.append(str(relative))
        return results


class S3Storage(StorageBackend):
    """S3-compatible storage backend (Hetzner Object Storage, AWS S3, MinIO)."""

    def __init__(self, config: S3Config):
        self.config = config
        self.client = boto3.client(
            's3',
            endpoint_url=config.endpoint,
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.secret_key,
        )
        self.bucket = config.bucket

    def upload(self, key: str, data: bytes, content_type: str = 'application/octet-stream') -> str:
        """Upload file to S3."""
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type
        )
        return f"s3://{self.bucket}/{key}"

    def download(self, key: str) -> Optional[bytes]:
        """Download file from S3."""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            raise

    def exists(self, key: str) -> bool:
        """Check if file exists in S3."""
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise

    def delete(self, key: str) -> bool:
        """Delete file from S3."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False

    def list_files(self, prefix: str = '') -> list[str]:
        """List files with prefix in S3."""
        results = []
        paginator = self.client.get_paginator('list_objects_v2')

        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            if 'Contents' in page:
                for obj in page['Contents']:
                    results.append(obj['Key'])

        return results


class StorageService:
    """
    Storage service with automatic backend selection.

    Uses S3 if configured and enabled, otherwise falls back to local filesystem.
    """

    def __init__(self):
        self._backend: Optional[StorageBackend] = None
        self._config: Optional[S3Config] = None

    def _load_config(self) -> S3Config:
        """Load S3 config from database."""
        def get_config(key: str, default: str = '') -> str:
            config = Config.query.filter_by(key=key).first()
            return config.value if config and config.value else default

        def decode_password(password_b64: str) -> str:
            """Decode Base64 password (FileZilla compatible)."""
            if not password_b64:
                return ''
            try:
                return base64.b64decode(password_b64).decode('utf-8')
            except Exception:
                return password_b64

        return S3Config(
            endpoint=get_config('s3_endpoint'),
            access_key=get_config('s3_access_key'),
            secret_key=decode_password(get_config('s3_secret_key')),
            bucket=get_config('s3_bucket', 'pricat-converter'),
            enabled=get_config('s3_enabled', 'false').lower() == 'true'
        )

    def _get_backend(self) -> StorageBackend:
        """Get or create storage backend."""
        if self._backend is None:
            self._config = self._load_config()

            if self._config.enabled and self._config.endpoint and self._config.access_key:
                try:
                    self._backend = S3Storage(self._config)
                    # Test connection
                    self._backend.client.head_bucket(Bucket=self._config.bucket)
                except Exception as e:
                    current_app.logger.warning(f"S3 connection failed, falling back to local: {e}")
                    self._backend = self._get_local_backend()
            else:
                self._backend = self._get_local_backend()

        return self._backend

    def _get_local_backend(self) -> LocalStorage:
        """Get local storage backend."""
        # Use instance directory (same as SQLite DB location)
        base_path = Path(current_app.instance_path) / 'storage'
        return LocalStorage(base_path)

    @property
    def is_s3(self) -> bool:
        """Check if using S3 backend."""
        return isinstance(self._get_backend(), S3Storage)

    # Delegate methods to backend

    def upload(self, key: str, data: bytes, content_type: str = 'application/octet-stream') -> str:
        """Upload file."""
        return self._get_backend().upload(key, data, content_type)

    def upload_file(self, key: str, file_path: Path, content_type: str = 'application/octet-stream') -> str:
        """Upload file from path."""
        data = file_path.read_bytes()
        return self.upload(key, data, content_type)

    def download(self, key: str) -> Optional[bytes]:
        """Download file content."""
        return self._get_backend().download(key)

    def download_to_file(self, key: str, file_path: Path) -> bool:
        """Download file to local path."""
        data = self.download(key)
        if data is not None:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(data)
            return True
        return False

    def exists(self, key: str) -> bool:
        """Check if file exists."""
        return self._get_backend().exists(key)

    def delete(self, key: str) -> bool:
        """Delete file."""
        return self._get_backend().delete(key)

    def list_files(self, prefix: str = '') -> list[str]:
        """List files with prefix."""
        return self._get_backend().list_files(prefix)

    def get_import_key(self, filename: str) -> str:
        """Get storage key for import file."""
        return f"imports/{filename}"

    def get_export_key(self, filename: str) -> str:
        """Get storage key for export file."""
        return f"exports/{filename}"

    def get_image_key(self, supplier_id: str, filename: str) -> str:
        """Get storage key for image file."""
        return f"images/{supplier_id}/{filename}"

    def get_markdown_image_key(self, filename: str) -> str:
        """Get storage key for markdown image file."""
        return f"markdown/{filename}"

    # =========================================================================
    # Markdown Image Upload Methods
    # =========================================================================

    def upload_markdown_image(self, file) -> dict:
        """Upload an image for use in Markdown content.

        Validates, resizes (if needed), and stores the image.

        Args:
            file: File-like object from request.files

        Returns:
            dict with 'url' (public URL) and 'markdown' (ready-to-use syntax)

        Raises:
            ValueError: If file is invalid, too large, or wrong format
        """
        # Validate file
        if not file or not file.filename:
            raise ValueError('Keine Datei ausgewählt')

        filename = file.filename.lower()
        ext = filename.rsplit('.', 1)[-1] if '.' in filename else ''

        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise ValueError(
                f'Ungültiges Dateiformat. Erlaubt: {", ".join(ALLOWED_IMAGE_EXTENSIONS)}'
            )

        # Check file size
        file.seek(0, 2)
        size = file.tell()
        file.seek(0)

        max_size = MAX_IMAGE_SIZE_MB * 1024 * 1024
        if size > max_size:
            raise ValueError(f'Datei zu groß. Maximum: {MAX_IMAGE_SIZE_MB} MB')

        # Process image (resize if needed)
        processed_data, final_ext = self._process_markdown_image(file)

        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = uuid.uuid4().hex[:8]
        new_filename = f'{timestamp}_{unique_id}.{final_ext}'

        # Upload
        key = self.get_markdown_image_key(new_filename)
        content_type = f'image/{final_ext}' if final_ext != 'jpg' else 'image/jpeg'

        if self.is_s3:
            # Upload to S3
            self.upload(key, processed_data, content_type)
            url = f'{self._config.endpoint}/{self._config.bucket}/{key}'
        else:
            # For local: write directly to static/uploads for web access
            static_path = Path(current_app.static_folder) / 'uploads' / 'markdown'
            static_path.mkdir(parents=True, exist_ok=True)
            file_path = static_path / new_filename
            file_path.write_bytes(processed_data)
            url = f'/static/uploads/markdown/{new_filename}'

        return {
            'url': url,
            'markdown': f'![Bild]({url})',
            'filename': new_filename,
            'key': key
        }

    def _process_markdown_image(self, file) -> tuple:
        """Process image: resize if needed, compress.

        Args:
            file: File-like object

        Returns:
            tuple (bytes data, extension string)
        """
        img = Image.open(file)

        # Determine output format
        original_format = img.format or 'PNG'
        if original_format.upper() in ('JPEG', 'JPG'):
            output_format = 'JPEG'
            ext = 'jpg'
        else:
            output_format = 'PNG'
            ext = 'png'

        # Convert RGBA to RGB for JPEG
        if output_format == 'JPEG' and img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background

        # Resize if too wide
        if img.width > MAX_IMAGE_WIDTH:
            ratio = MAX_IMAGE_WIDTH / img.width
            new_height = int(img.height * ratio)
            img = img.resize((MAX_IMAGE_WIDTH, new_height), Image.Resampling.LANCZOS)

        # Save to buffer
        buffer = BytesIO()
        if output_format == 'JPEG':
            img.save(buffer, format='JPEG', quality=85, optimize=True)
        else:
            img.save(buffer, format='PNG', optimize=True)

        return buffer.getvalue(), ext

    def delete_markdown_image(self, url: str) -> bool:
        """Delete a markdown image by its URL.

        Args:
            url: The URL returned from upload_markdown_image

        Returns:
            True if deleted, False if not found
        """
        if '/static/uploads/markdown/' in url:
            # Local file
            filename = url.split('/static/uploads/markdown/')[-1]
            file_path = Path(current_app.static_folder) / 'uploads' / 'markdown' / filename
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        elif self._config and self._config.bucket and self._config.bucket in url:
            # S3 file
            key = url.split(f'{self._config.bucket}/')[-1]
            return self.delete(key)
        else:
            return False
