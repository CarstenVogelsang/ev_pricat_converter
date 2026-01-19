"""Medium model for global media management.

Part of the global media library that can be used by all modules.
Supports both uploaded files and external URLs.
"""
from datetime import datetime
from enum import Enum
import os

from app import db


class MediumTyp(Enum):
    """Type of medium."""
    BANNER = 'banner'      # Banner images for mailings/headers
    BILD = 'bild'          # General images
    LOGO = 'logo'          # Logo images
    DOKUMENT = 'dokument'  # PDF, etc.


class Medium(db.Model):
    """A media file in the global media library.

    Media can be:
    - Uploaded files (stored in static/uploads/medien/)
    - External URLs (e.g., Unsplash images)

    Attributes:
        id: Primary key
        titel: Display title for the medium
        beschreibung: Optional description
        typ: Type of medium (banner, bild, logo, dokument)
        dateiname: Original filename (for uploads)
        dateipfad: Relative path to file (for uploads)
        externe_url: External URL (for linked media)
        thumbnail_url: Optional thumbnail URL
        dateigroesse: File size in bytes
        mime_type: MIME type (e.g., 'image/jpeg')
        breite: Image width in pixels
        hoehe: Image height in pixels
        erstellt_am: Creation timestamp
        erstellt_von_id: User who uploaded/created
        aktiv: Whether medium is active
    """
    __tablename__ = 'medium'

    id = db.Column(db.Integer, primary_key=True)
    titel = db.Column(db.String(200), nullable=False)
    beschreibung = db.Column(db.Text)
    typ = db.Column(db.String(50), default=MediumTyp.BILD.value)
    dateiname = db.Column(db.String(255))
    dateipfad = db.Column(db.String(500))
    externe_url = db.Column(db.String(1000))
    thumbnail_url = db.Column(db.String(1000))
    dateigroesse = db.Column(db.Integer, default=0)
    mime_type = db.Column(db.String(100))
    breite = db.Column(db.Integer)
    hoehe = db.Column(db.Integer)
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)
    erstellt_von_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    aktiv = db.Column(db.Boolean, default=True)

    # Relationships
    erstellt_von = db.relationship('User', foreign_keys=[erstellt_von_id])

    @property
    def url(self) -> str:
        """Get the URL to access this medium.

        Returns external_url if set, otherwise the local file path.
        """
        if self.externe_url:
            return self.externe_url
        if self.dateipfad:
            return f'/static/uploads/medien/{self.dateipfad}'
        return '/static/placeholder-image.svg'

    @property
    def is_external(self) -> bool:
        """Check if this is an external URL."""
        return bool(self.externe_url)

    @property
    def is_image(self) -> bool:
        """Check if this is an image file."""
        if self.mime_type:
            return self.mime_type.startswith('image/')
        return self.typ in [MediumTyp.BANNER.value, MediumTyp.BILD.value, MediumTyp.LOGO.value]

    @classmethod
    def create_from_upload(
        cls,
        file,
        titel: str,
        typ: str = MediumTyp.BILD.value,
        erstellt_von_id: int = None,
        beschreibung: str = None
    ) -> 'Medium':
        """Create a Medium from an uploaded file.

        Args:
            file: Werkzeug FileStorage object
            titel: Display title
            typ: Medium type
            erstellt_von_id: User ID
            beschreibung: Optional description

        Returns:
            Created Medium instance (not yet committed)
        """
        from werkzeug.utils import secure_filename

        # Generate safe filename with timestamp
        original_filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{timestamp}_{original_filename}'

        # Determine subdirectory based on type
        subdir = typ if typ in ['banner', 'bild', 'logo'] else 'sonstige'

        # Save file
        upload_dir = os.path.join('app', 'static', 'uploads', 'medien', subdir)
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        # Get file info
        file_size = os.path.getsize(filepath)

        # Create Medium instance
        medium = cls(
            titel=titel,
            beschreibung=beschreibung,
            typ=typ,
            dateiname=original_filename,
            dateipfad=f'{subdir}/{filename}',
            dateigroesse=file_size,
            mime_type=file.content_type,
            erstellt_von_id=erstellt_von_id
        )

        return medium

    @classmethod
    def create_from_url(
        cls,
        url: str,
        titel: str,
        typ: str = MediumTyp.BILD.value,
        erstellt_von_id: int = None,
        beschreibung: str = None,
        thumbnail_url: str = None
    ) -> 'Medium':
        """Create a Medium from an external URL.

        Args:
            url: External URL to the media
            titel: Display title
            typ: Medium type
            erstellt_von_id: User ID
            beschreibung: Optional description
            thumbnail_url: Optional thumbnail URL

        Returns:
            Created Medium instance (not yet committed)
        """
        return cls(
            titel=titel,
            beschreibung=beschreibung,
            typ=typ,
            externe_url=url,
            thumbnail_url=thumbnail_url,
            erstellt_von_id=erstellt_von_id
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON responses."""
        return {
            'id': self.id,
            'titel': self.titel,
            'beschreibung': self.beschreibung,
            'typ': self.typ,
            'url': self.url,
            'thumbnail_url': self.thumbnail_url or self.url,
            'dateiname': self.dateiname,
            'dateigroesse': self.dateigroesse,
            'mime_type': self.mime_type,
            'breite': self.breite,
            'hoehe': self.hoehe,
            'is_external': self.is_external,
            'is_image': self.is_image,
            'erstellt_am': self.erstellt_am.isoformat() if self.erstellt_am else None,
        }

    def __repr__(self):
        return f'<Medium {self.id}: {self.titel}>'
