"""PRICAT CSV Parser Service.

Parses VEDES PRICAT CSV files and extracts:
- Lieferant (Supplier) data
- Hersteller (Manufacturer) data
- Marke (Brand) data
- Article data for Elena export
"""
import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app import db
from app.models import Lieferant, Hersteller, Marke
from app.utils import strip_leading_zeros


# PRICAT column indices (0-based)
# Based on CLAUDE.md and actual PRICAT file analysis
PRICAT_COLUMNS = {
    'record_type': 0,           # H/P
    'format': 1,                # PRICAT
    'debitor': 2,
    'debitor_gln': 3,
    'datum': 4,
    'vedes_artikelnummer': 5,
    'alte_artikelnummer': 6,
    'vertriebsstatus': 7,
    'vertriebsstatus_gueltig_ab': 8,
    'ean': 9,
    'ean_typ': 10,
    'artbez_prefix': 11,
    'artikelbezeichnung': 12,
    'artbez_suffix': 13,
    'artbez_sammelart': 14,
    'orig_artbez_hersteller': 15,
    'warengruppe': 16,
    'warengruppen_name': 17,
    'verkaufseinheit': 18,
    'kleinmenge': 19,
    'umkarton': 20,
    'ean_umkarton': 21,
    'ean_typ_umkarton': 22,
    'zolltarifnr': 23,
    'herkunft': 24,
    'lieferant_gln': 25,
    'lieferant_id': 26,
    'lieferant_name': 27,
    'artikelnummer_lieferant': 28,
    'hersteller_gln': 29,
    'hersteller_id': 30,
    'hersteller_name': 31,
    'hersteller_artikelnr': 32,
    'uvpe': 33,                 # Recommended retail price
    'gnp_lieferant': 34,        # Supplier net price (priceEK)
    'uvpe_at': 35,
    'uvpe_ch': 36,
    'uvpe_it': 37,
    'mwst': 38,
    'preisbindung': 39,
    'grundpreis_wert': 40,
    'grundpreis_einheit': 41,
    'skz': 42,
    'verkauf_ab': 43,
    'verkauf_bis': 44,
    'verkauf_ab_b2c': 45,
    'anzeige_ab_b2c': 46,
    'einkaufstagung': 47,
    'neuheiten_kz': 48,
    'lizenzen': 49,
    'schlagworte': 50,
    'marke_text': 51,
    'saisontyp': 52,
    'saison': 53,
    'saisonjahr': 54,
    'kollektion': 55,
    'verfuegbarkeit': 56,
    'vorr_verfuegbar_ab': 57,
    'artikel_anlagedatum': 58,
    'farbcode': 59,
    'farbbez': 60,
    'groesse': 61,
    'geschlecht': 62,
    'gewicht': 63,
    'gewichtseinheit': 64,
    'laenge': 65,
    'breite': 66,
    'hoehe': 67,
    'laengeneinheit': 68,
    'empf_mindestalter': 69,
    'empf_mindestalter_einheit': 70,
    'empf_hoechstalter': 71,
    'empf_hoechstalter_einheit': 72,
    'altersfreigabe': 73,
    'zeiteinheit_altersangaben': 74,
    'anzahl_spieler_min': 75,
    'anzahl_spieler_max': 76,
    'batterie_erforderlich': 77,
    'batterie_enthalten': 78,
    'batterie_format': 79,
    'batterie_menge': 80,
    'wiederaufladbar': 81,
    'massstab': 82,
    'elektroschrott': 83,
    'weee_reg_nr': 84,
    'grs_nr': 85,
    'gruener_punkt': 86,
    'icti': 87,
    'ce_kennzeichnung': 88,
    'ce_richtlinie': 89,
    'tuev_gueltig_bis': 90,
    'tuev_pruefstelle': 91,
    'gs_gueltig_bis': 92,
    'gs_pruefstelle': 93,
    'bilderlink': 94,
    'sprach_kz_texte': 95,
    'grunddatentext': 96,
    'vertriebstext': 97,
    'prueftext': 98,
    'warnhinweise': 99,
    'sprach_vers_warnhinw': 100,
    'sprach_vers_gebr_anw': 101,
    'mhd_kennzeichnung': 102,
    'prod_mit_herst_namen_und_zustellf_adr': 103,
    'n_geschenkfaehig': 104,
    'sortiert': 105,
    'onlinesperre': 106,
    'artikeltyp': 107,
    'ladegruppe': 108,
    'exklusiv': 109,
    'werbemittel': 110,
    'artikel_shb': 111,
    'artikel_gehoert_zu': 112,
    'produktmarke_text': 113,
    'produktlinie': 114,
    'laenge_aufbaumass': 115,
    'breite_aufbaumass': 116,
    'hoehe_aufbaumass': 117,
    'einheit_aufbaumasse': 118,
    'fsc_kennzeichen': 119,
    'fsc_form': 120,
    'fsc_holzart': 121,
    'fsc_zertifikatsnummer': 122,
    'inhalt': 123,
    'inhalt_einheit': 124,
    'durchmesser': 125,
    'durchmesser_einheit': 126,
    'tragkraft': 127,
    'tragkraft_einheit': 128,
    'fuellmenge': 129,
    'fuellmenge_einheit': 130,
    'sound': 131,
    'licht': 132,
    'musik': 133,
    'textilkennzeichnung': 134,
    'spieldauer_minuten': 135,
    'standardartikelgruppe': 136,
    'ds_versandinfo': 137,
    'kopfartikel_ean': 138,
    'kopfartikelnummer': 139,
    'komp_menge': 140,
    'stueckl_pos': 141,
    'sid': 142,
}


@dataclass
class ArticleData:
    """Parsed article data from PRICAT row."""
    vedes_artikelnummer: str
    ean: str
    artikelbezeichnung: str
    artikelbezeichnung_lang: str = ''
    lieferant_gln: str = ''
    lieferant_id: str = ''
    lieferant_name: str = ''
    hersteller_gln: str = ''
    hersteller_id: str = ''
    hersteller_name: str = ''
    hersteller_artikelnr: str = ''
    marke_text: str = ''
    uvpe: str = ''  # Recommended retail price
    gnp_lieferant: str = ''  # Supplier net price (priceEK)
    mwst: str = ''
    gewicht: str = ''
    gewichtseinheit: str = ''
    bilderlink: str = ''
    grunddatentext: str = ''
    warnhinweise: str = ''
    zolltarifnr: str = ''
    herkunft: str = ''
    warengruppe: str = ''
    warengruppen_name: str = ''
    vertriebsstatus: str = ''
    inhalt: str = ''
    inhalt_einheit: str = ''


@dataclass
class PricatData:
    """Container for parsed PRICAT data."""
    header: list[str] = field(default_factory=list)
    articles: list[ArticleData] = field(default_factory=list)
    lieferant_gln: str = ''
    lieferant_id: str = ''
    lieferant_name: str = ''
    hersteller_set: set = field(default_factory=set)  # (gln, vedes_id, name)
    marken_set: set = field(default_factory=set)  # (hersteller_gln, marke_text)
    image_urls: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    row_count: int = 0
    skipped_count: int = 0


class PricatParser:
    """Parser for VEDES PRICAT CSV files."""

    def __init__(self):
        self.encoding = None

    def _detect_encoding(self, file_path: Path) -> str:
        """Detect file encoding by trying UTF-8 first, then Latin-1."""
        encodings = ['utf-8', 'latin-1', 'cp1252']
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    # Try to read first few lines
                    for _ in range(10):
                        f.readline()
                return enc
            except UnicodeDecodeError:
                continue
        return 'latin-1'  # Fallback

    def _safe_get(self, row: list, index: int) -> str:
        """Safely get value from row, return empty string if index out of range."""
        if index < len(row):
            value = row[index]
            return value.strip() if value else ''
        return ''

    def _parse_price(self, price_str: str) -> str:
        """Parse price string, handling German number format."""
        if not price_str:
            return ''
        # Remove spaces and handle German decimal format
        price = price_str.strip().replace(' ', '')
        # Convert German format (comma as decimal separator)
        if ',' in price and '.' not in price:
            price = price.replace(',', '.')
        return price

    def _is_data_row(self, row: list) -> bool:
        """Check if row is a data row (starts with P;PRICAT)."""
        if len(row) < 2:
            return False
        return row[0] == 'P' and row[1] == 'PRICAT'

    def _is_header_row(self, row: list) -> bool:
        """Check if row is header row (starts with H;PRICAT)."""
        if len(row) < 2:
            return False
        return row[0] == 'H' and row[1] == 'PRICAT'

    def parse(self, file_path: Path) -> PricatData:
        """
        Parse PRICAT CSV file.

        Args:
            file_path: Path to PRICAT CSV file

        Returns:
            PricatData with parsed articles, entities, and image URLs
        """
        result = PricatData()

        if not file_path.exists():
            result.errors.append(f"File not found: {file_path}")
            return result

        self.encoding = self._detect_encoding(file_path)

        with open(file_path, 'r', encoding=self.encoding) as f:
            reader = csv.reader(f, delimiter=';', quotechar='"')

            for line_num, row in enumerate(reader, start=1):
                if not row:
                    continue

                # Parse header row
                if self._is_header_row(row):
                    result.header = row
                    continue

                # Parse data rows
                if self._is_data_row(row):
                    result.row_count += 1

                    try:
                        article = self._parse_article_row(row)
                        result.articles.append(article)

                        # Extract Lieferant info (same for all articles)
                        if not result.lieferant_gln and article.lieferant_gln:
                            result.lieferant_gln = article.lieferant_gln
                            result.lieferant_id = article.lieferant_id
                            result.lieferant_name = article.lieferant_name

                        # Collect unique Hersteller
                        if article.hersteller_gln:
                            result.hersteller_set.add((
                                article.hersteller_gln,
                                article.hersteller_id,
                                article.hersteller_name
                            ))

                        # Collect unique Marken (associated with Hersteller)
                        if article.marke_text and article.hersteller_gln:
                            result.marken_set.add((
                                article.hersteller_gln,
                                article.marke_text
                            ))

                        # Collect image URLs
                        if article.bilderlink:
                            result.image_urls.append(article.bilderlink)

                    except Exception as e:
                        result.errors.append(f"Error parsing line {line_num}: {str(e)}")
                        result.skipped_count += 1

        return result

    def _parse_article_row(self, row: list) -> ArticleData:
        """Parse a single article row into ArticleData."""
        return ArticleData(
            vedes_artikelnummer=self._safe_get(row, PRICAT_COLUMNS['vedes_artikelnummer']),
            ean=self._safe_get(row, PRICAT_COLUMNS['ean']),
            artikelbezeichnung=self._safe_get(row, PRICAT_COLUMNS['artikelbezeichnung']),
            artikelbezeichnung_lang=self._safe_get(row, PRICAT_COLUMNS['orig_artbez_hersteller']),
            lieferant_gln=self._safe_get(row, PRICAT_COLUMNS['lieferant_gln']),
            lieferant_id=strip_leading_zeros(self._safe_get(row, PRICAT_COLUMNS['lieferant_id'])),
            lieferant_name=self._safe_get(row, PRICAT_COLUMNS['lieferant_name']),
            hersteller_gln=self._safe_get(row, PRICAT_COLUMNS['hersteller_gln']),
            hersteller_id=strip_leading_zeros(self._safe_get(row, PRICAT_COLUMNS['hersteller_id'])),
            hersteller_name=self._safe_get(row, PRICAT_COLUMNS['hersteller_name']),
            hersteller_artikelnr=self._safe_get(row, PRICAT_COLUMNS['hersteller_artikelnr']),
            marke_text=self._safe_get(row, PRICAT_COLUMNS['marke_text']),
            uvpe=self._parse_price(self._safe_get(row, PRICAT_COLUMNS['uvpe'])),
            gnp_lieferant=self._parse_price(self._safe_get(row, PRICAT_COLUMNS['gnp_lieferant'])),
            mwst=self._safe_get(row, PRICAT_COLUMNS['mwst']),
            gewicht=self._safe_get(row, PRICAT_COLUMNS['gewicht']),
            gewichtseinheit=self._safe_get(row, PRICAT_COLUMNS['gewichtseinheit']),
            bilderlink=self._safe_get(row, PRICAT_COLUMNS['bilderlink']),
            grunddatentext=self._safe_get(row, PRICAT_COLUMNS['grunddatentext']),
            warnhinweise=self._safe_get(row, PRICAT_COLUMNS['warnhinweise']),
            zolltarifnr=self._safe_get(row, PRICAT_COLUMNS['zolltarifnr']),
            herkunft=self._safe_get(row, PRICAT_COLUMNS['herkunft']),
            warengruppe=self._safe_get(row, PRICAT_COLUMNS['warengruppe']),
            warengruppen_name=self._safe_get(row, PRICAT_COLUMNS['warengruppen_name']),
            vertriebsstatus=self._safe_get(row, PRICAT_COLUMNS['vertriebsstatus']),
            inhalt=self._safe_get(row, PRICAT_COLUMNS['inhalt']),
            inhalt_einheit=self._safe_get(row, PRICAT_COLUMNS['inhalt_einheit']),
        )

    def extract_entities(self, data: PricatData) -> tuple[
        Optional[Lieferant],
        list[Hersteller],
        list[Marke]
    ]:
        """
        Extract and upsert Lieferant, Hersteller, and Marke entities from parsed data.

        Args:
            data: PricatData from parse()

        Returns:
            Tuple of (Lieferant, list[Hersteller], list[Marke])
        """
        lieferant = None
        hersteller_list = []
        marken_list = []

        # Upsert Lieferant
        if data.lieferant_gln:
            lieferant = Lieferant.query.filter_by(gln=data.lieferant_gln).first()
            if lieferant:
                # Update existing
                if data.lieferant_name:
                    lieferant.kurzbezeichnung = data.lieferant_name
                if data.lieferant_id:
                    lieferant.vedes_id = data.lieferant_id
            else:
                # Create new
                lieferant = Lieferant(
                    gln=data.lieferant_gln,
                    vedes_id=data.lieferant_id or data.lieferant_gln,
                    kurzbezeichnung=data.lieferant_name or 'Unknown',
                    aktiv=True
                )
                db.session.add(lieferant)

            db.session.flush()

        # Upsert Hersteller
        hersteller_map = {}  # gln -> Hersteller
        for h_gln, h_vedes_id, h_name in data.hersteller_set:
            hersteller = Hersteller.query.filter_by(gln=h_gln).first()
            if hersteller:
                if h_name:
                    hersteller.kurzbezeichnung = h_name
                if h_vedes_id:
                    hersteller.vedes_id = h_vedes_id
            else:
                hersteller = Hersteller(
                    gln=h_gln,
                    vedes_id=h_vedes_id or h_gln,
                    kurzbezeichnung=h_name or 'Unknown'
                )
                db.session.add(hersteller)

            db.session.flush()
            hersteller_list.append(hersteller)
            hersteller_map[h_gln] = hersteller

        # Upsert Marken
        for h_gln, marke_text in data.marken_set:
            if h_gln not in hersteller_map:
                continue

            hersteller = hersteller_map[h_gln]

            # Check if marke already exists for this hersteller
            existing_marke = Marke.query.filter_by(
                hersteller_id=hersteller.id,
                kurzbezeichnung=marke_text
            ).first()

            if existing_marke:
                marken_list.append(existing_marke)
            else:
                # Generate unique gln_evendo
                gln_evendo = Marke.generate_gln_evendo(hersteller, marke_text)

                marke = Marke(
                    kurzbezeichnung=marke_text,
                    gln_evendo=gln_evendo,
                    hersteller_id=hersteller.id
                )
                db.session.add(marke)
                db.session.flush()
                marken_list.append(marke)

        db.session.commit()

        return lieferant, hersteller_list, marken_list

    def get_image_urls(self, data: PricatData) -> list[str]:
        """
        Get unique image URLs from parsed data.

        Args:
            data: PricatData from parse()

        Returns:
            List of unique image URLs
        """
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in data.image_urls:
            if url and url not in seen:
                seen.add(url)
                unique_urls.append(url)
        return unique_urls

    def get_marke_gln_evendo(self, hersteller_gln: str, marke_text: str) -> Optional[str]:
        """
        Get the gln_evendo for a marke, looking up from database.

        Args:
            hersteller_gln: GLN of the manufacturer
            marke_text: Brand name text

        Returns:
            gln_evendo if found, None otherwise
        """
        hersteller = Hersteller.query.filter_by(gln=hersteller_gln).first()
        if not hersteller:
            return None

        marke = Marke.query.filter_by(
            hersteller_id=hersteller.id,
            kurzbezeichnung=marke_text
        ).first()

        return marke.gln_evendo if marke else None
