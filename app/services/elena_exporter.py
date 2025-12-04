"""Elena CSV Exporter Service.

Transforms parsed PRICAT article data into Elena import format CSV.
"""
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.services.pricat_parser import ArticleData, PricatData


# Elena CSV column headers (based on musterlieferant_stammdaten.csv)
ELENA_HEADERS = [
    'Lieferant',
    'Lie-GLN',
    'Hersteller',
    'Hersteller-GLN',
    'Marke',
    'Marke-GLN',
    'Artikelnummer',
    'MPN',
    'Kurzbezeichnung',
    'GTIN/EAN',
    'Warenschlüssel',
    'Mindestbestellmenge',
    'Rabattgruppe',
    'MWST',
    'Grundnettopreis',
    'Verkaufspreis',
    'Staffel-EK1',
    'Staffel-EKMe1',
    'PA-Einheit',
    'PA-Inhalt',
    'Bez-Lang',
    'Beschreibung',
    'Zolltarifnummer',
    'Herkunftsland',
    'Gewicht',
    'Name Bild 1',
    'Name Bild 2',
    'Name Bild 3',
    'Name Bild 4',
    'Name Bild 5',
    'Name Bild 6',
    'Name Bild 7',
    'Name Bild 8',
    'Name Bild 9',
    'Name Bild 10',
    'Name Bild 11',
    'Name Bild 12',
    'Name Bild 13',
    'Name Bild 14',
    'Name Bild 15',
    'Ausführung',
    'Marke_1',
    'Produkt-Art',
    'Stromsystem',
    'Spurweite',
    'Maßstab',
    'Fahrzeug-Marke',
    'Fahrzeug-Typ',
    'Fahrzeug-Art',
    'Farbe',
    'Thema',
    'Bahnverwaltung',
    'Epoche',
    'Analog - Digital',
    'Schnittstelle',
    'Decoder',
    'Sound',
    'Stirnbeleuchtung',
    'Beleuchtung',
    'Kupplungssystem',
    'Mindestradius (mm)',
    'LüP (mm)',
    'Material',
    'Herstellungsland',
    'Verpackungsmenge (Verpackungseinheit/Los EK) LosEKAnzahl',
    'Einheitname der Verpackungsmenge (Verpackungseinheit/Los EK)',
    'Einheit der Verpackungsmenge (Verpackungseinheit/Los EK) LosEKEinheitNr',
    'Verpackungsmenge (Verpackungseinheit/Los VK) LosVKAnzahl',
    'Einheitname der Verpackungsmenge (Verpackungseinheit/Los VK',
    'Einheit der Verpackungsmenge (Verpackungseinheit/Los VK) LosVKEinheitNr',
    'Preis pro Menge (EK) Einheit BestellEinheitEK',
    'Preis pro Menge (EK) Kalkfaktor KalkfaktorEK',
    'Preis pro Menge (VK) Mindestbestellmenge',
    'Preis pro Menge (EK) Mindestbestellmenge',
    'Preis pro Menge (VK) Kalkfaktor KalkfaktorVK',
    'Produktserie',
]


@dataclass
class ExportResult:
    """Result of Elena CSV export."""
    success: bool
    output_path: Optional[Path] = None
    rows_exported: int = 0
    errors: list = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class ElenaExporter:
    """Exports article data to Elena CSV format."""

    def __init__(self, marke_gln_lookup: dict = None):
        """
        Initialize exporter.

        Args:
            marke_gln_lookup: Optional dict mapping (hersteller_gln, marke_text) -> gln_evendo
        """
        self.marke_gln_lookup = marke_gln_lookup or {}

    def _format_price(self, price: str) -> str:
        """Format price for Elena CSV (German format with comma)."""
        if not price:
            return ''
        # Ensure German format (comma as decimal separator)
        return price.replace('.', ',')

    def _format_weight(self, weight: str, unit: str) -> str:
        """Format weight for Elena CSV."""
        if not weight:
            return ''
        # Convert to kg if needed, return with German decimal format
        weight_val = weight.replace(',', '.').strip()
        try:
            w = float(weight_val)
            # Unit conversion if needed (G -> kg)
            if unit and unit.upper() == 'G':
                w = w / 1000
            return str(w).replace('.', ',')
        except ValueError:
            return weight.replace('.', ',')

    def _extract_image_filename(self, url: str) -> str:
        """Extract filename from image URL."""
        if not url:
            return ''
        # Get last part of URL path
        return url.split('/')[-1] if '/' in url else url

    def _get_marke_gln(self, hersteller_gln: str, marke_text: str) -> str:
        """Get gln_evendo for a brand from lookup."""
        key = (hersteller_gln, marke_text)
        return self.marke_gln_lookup.get(key, '')

    def _article_to_row(self, article: ArticleData) -> list:
        """Convert ArticleData to Elena CSV row."""
        # Extract image filename
        image_filename = self._extract_image_filename(article.bilderlink)

        # Get marke GLN
        marke_gln = self._get_marke_gln(article.hersteller_gln, article.marke_text)

        # Build row matching ELENA_HEADERS
        row = [
            article.lieferant_name,                      # Lieferant
            article.lieferant_gln,                       # Lie-GLN
            article.hersteller_name,                     # Hersteller
            article.hersteller_gln,                      # Hersteller-GLN
            article.marke_text,                          # Marke
            marke_gln,                                   # Marke-GLN
            article.vedes_artikelnummer,                 # Artikelnummer
            article.hersteller_artikelnr,                # MPN
            article.artikelbezeichnung,                  # Kurzbezeichnung
            article.ean,                                 # GTIN/EAN
            article.warengruppe,                         # Warenschlüssel
            '1',                                         # Mindestbestellmenge (default)
            '',                                          # Rabattgruppe
            article.mwst,                                # MWST
            self._format_price(article.gnp_lieferant),   # Grundnettopreis
            self._format_price(article.uvpe),            # Verkaufspreis
            '',                                          # Staffel-EK1
            '',                                          # Staffel-EKMe1
            article.inhalt_einheit or '',                # PA-Einheit
            article.inhalt or '',                        # PA-Inhalt
            article.grunddatentext,                      # Bez-Lang
            article.warnhinweise,                        # Beschreibung (using warnhinweise)
            article.zolltarifnr,                         # Zolltarifnummer
            article.herkunft,                            # Herkunftsland
            self._format_weight(article.gewicht, article.gewichtseinheit),  # Gewicht
            image_filename,                              # Name Bild 1
            '',                                          # Name Bild 2
            '',                                          # Name Bild 3
            '',                                          # Name Bild 4
            '',                                          # Name Bild 5
            '',                                          # Name Bild 6
            '',                                          # Name Bild 7
            '',                                          # Name Bild 8
            '',                                          # Name Bild 9
            '',                                          # Name Bild 10
            '',                                          # Name Bild 11
            '',                                          # Name Bild 12
            '',                                          # Name Bild 13
            '',                                          # Name Bild 14
            '',                                          # Name Bild 15
            '',                                          # Ausführung
            article.marke_text,                          # Marke_1
            '',                                          # Produkt-Art
            '',                                          # Stromsystem
            '',                                          # Spurweite
            '',                                          # Maßstab
            '',                                          # Fahrzeug-Marke
            '',                                          # Fahrzeug-Typ
            '',                                          # Fahrzeug-Art
            '',                                          # Farbe
            '',                                          # Thema
            '',                                          # Bahnverwaltung
            '',                                          # Epoche
            '',                                          # Analog - Digital
            '',                                          # Schnittstelle
            '',                                          # Decoder
            '',                                          # Sound
            '',                                          # Stirnbeleuchtung
            '',                                          # Beleuchtung
            '',                                          # Kupplungssystem
            '',                                          # Mindestradius (mm)
            '',                                          # LüP (mm)
            '',                                          # Material
            article.herkunft,                            # Herstellungsland
            '1',                                         # LosEKAnzahl
            'Stck',                                      # Einheitname Los EK
            '1',                                         # LosEKEinheitNr
            '1',                                         # LosVKAnzahl
            'Stck',                                      # Einheitname Los VK
            '1',                                         # LosVKEinheitNr
            '1',                                         # BestellEinheitEK
            '1',                                         # KalkfaktorEK
            '1',                                         # Mindestbestellmenge VK
            '1',                                         # Mindestbestellmenge EK
            '1',                                         # KalkfaktorVK
            '',                                          # Produktserie
        ]

        return row

    def export(
        self,
        pricat_data: PricatData,
        output_path: Path,
        marke_gln_lookup: dict = None
    ) -> ExportResult:
        """
        Export PRICAT articles to Elena CSV format.

        Args:
            pricat_data: Parsed PRICAT data
            output_path: Path for output CSV file
            marke_gln_lookup: Optional dict mapping (hersteller_gln, marke_text) -> gln_evendo

        Returns:
            ExportResult with success status and statistics
        """
        result = ExportResult(success=False)

        if marke_gln_lookup:
            self.marke_gln_lookup = marke_gln_lookup

        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)

                # Write header
                writer.writerow(ELENA_HEADERS)

                # Write articles
                for article in pricat_data.articles:
                    try:
                        row = self._article_to_row(article)
                        writer.writerow(row)
                        result.rows_exported += 1
                    except Exception as e:
                        result.errors.append(f"Error exporting article {article.ean}: {str(e)}")

            result.success = True
            result.output_path = output_path

        except Exception as e:
            result.errors.append(f"Export failed: {str(e)}")

        return result

    def export_articles(
        self,
        articles: list[ArticleData],
        output_path: Path,
        marke_gln_lookup: dict = None
    ) -> ExportResult:
        """
        Export list of articles to Elena CSV format.

        Args:
            articles: List of ArticleData objects
            output_path: Path for output CSV file
            marke_gln_lookup: Optional dict mapping (hersteller_gln, marke_text) -> gln_evendo

        Returns:
            ExportResult with success status and statistics
        """
        # Create a minimal PricatData wrapper
        pricat_data = PricatData(articles=articles)
        return self.export(pricat_data, output_path, marke_gln_lookup)


def generate_elena_filename(lieferant_vedes_id: str, suffix: str = '') -> str:
    """
    Generate Elena export filename.

    Args:
        lieferant_vedes_id: VEDES ID of supplier
        suffix: Optional suffix

    Returns:
        Filename like 'elena_0000001872_20250103_143052.csv'
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if suffix:
        return f"elena_{lieferant_vedes_id}_{timestamp}_{suffix}.csv"
    return f"elena_{lieferant_vedes_id}_{timestamp}.csv"
