#!/usr/bin/env python3
"""
Import-Script für NTG Produkt-Codelisten

Liest alle 15 Codelisten aus der Excel-Datei und importiert sie
in die ProduktLookup-Tabelle.

Ausführung:
    uv run python scripts/import_produkt_codelisten.py

Kategorien (15 Stück, ~900 Einträge):
    - laender (258)
    - gewichtseinheiten (18)
    - waehrungen (6)
    - batterien (88)
    - weee_kennzeichnung (8)
    - gefahrengut (26)
    - dvd_bluray_codes (21)
    - gpc_brick (75)
    - bamberger (93)
    - saison (43)
    - mwst_saetze (31)
    - genre (49)
    - plattform (20)
    - gefahrstoffe (135)
    - lagerklassen (29)
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import xlrd
from app import create_app, db
from app.models import ProduktLookup


def clean_value(value):
    """Clean cell value - handle strings, numbers, empty values."""
    if value is None:
        return None
    if isinstance(value, float):
        # Convert float to int if it's a whole number
        if value == int(value):
            return str(int(value))
        return str(value)
    value = str(value).strip()
    # Remove non-breaking spaces
    value = value.replace('\xa0', '').strip()
    return value if value else None


def import_simple_codelist(sheet, kategorie, code_col=1, bez_col=2, data_start_row=3):
    """
    Import a simple codelist with Code and Bezeichnung columns.

    Args:
        sheet: xlrd sheet object
        kategorie: Category name for ProduktLookup
        code_col: Column index for code (0-based)
        bez_col: Column index for bezeichnung (0-based)
        data_start_row: First row with actual data (0-based)

    Returns:
        List of ProduktLookup objects
    """
    entries = []
    sortierung = 0

    for row in range(data_start_row, sheet.nrows):
        code = clean_value(sheet.cell_value(row, code_col))
        bezeichnung = clean_value(sheet.cell_value(row, bez_col))

        # Skip empty rows
        if not code or not bezeichnung:
            continue

        sortierung += 10
        entries.append(ProduktLookup(
            kategorie=kategorie,
            code=code,
            bezeichnung=bezeichnung,
            sortierung=sortierung
        ))

    return entries


def import_laender(sheet):
    """Import Länder (258 Einträge)."""
    return import_simple_codelist(sheet, 'laender', code_col=1, bez_col=2, data_start_row=3)


def import_gewichtseinheiten(sheet):
    """Import Gewichts- und Maßeinheiten (18 Einträge)."""
    return import_simple_codelist(sheet, 'gewichtseinheiten', code_col=1, bez_col=2, data_start_row=3)


def import_waehrungen(sheet):
    """Import Währungen (6 Einträge)."""
    return import_simple_codelist(sheet, 'waehrungen', code_col=1, bez_col=2, data_start_row=3)


def import_batterien(sheet):
    """
    Import Batterien (88 Einträge).

    Columns:
        B (1): ANSI Nummer (-> Code)
        C (2): IEC Kennzeichnung (-> zusatz_1)
        D (3): Allgemeine Kennzeichnung (-> zusatz_2)
        E (4): Volt (-> zusatz_3)
        F (5): Chemikalien (-> bezeichnung)
    """
    entries = []
    sortierung = 0

    for row in range(3, sheet.nrows):
        ansi = clean_value(sheet.cell_value(row, 1))
        iec = clean_value(sheet.cell_value(row, 2))
        allgemein = clean_value(sheet.cell_value(row, 3))
        volt = clean_value(sheet.cell_value(row, 4))
        chemikalien = clean_value(sheet.cell_value(row, 5))

        if not ansi:
            continue

        # Create combined designation
        bezeichnung = f"{allgemein or ''} ({iec or ansi})"
        if chemikalien:
            bezeichnung += f" - {chemikalien}"

        sortierung += 10
        entries.append(ProduktLookup(
            kategorie='batterien',
            code=ansi,
            bezeichnung=bezeichnung.strip(),
            zusatz_1=iec,      # IEC Kennzeichnung
            zusatz_2=allgemein,  # Allgemeine Kennzeichnung (D, AA, AAA, etc.)
            zusatz_3=volt,       # Volt
            sortierung=sortierung
        ))

    return entries


def import_weee(sheet):
    """Import WEEE Kennzeichnung (8 Einträge)."""
    return import_simple_codelist(sheet, 'weee_kennzeichnung', code_col=1, bez_col=2, data_start_row=3)


def import_gefahrengut(sheet):
    """
    Import Gefahrengutschlüssel (26 Einträge).

    Sheet has two sections:
        - 1. Ziffer (Hauptgefahr): codes 2-9
        - 2. und 3. Ziffer (Zusatzgefahren): codes 1-9

    We create unique codes: H2-H9 for Hauptgefahr, Z1-Z9 for Zusatzgefahren.
    """
    entries = []
    sortierung = 0
    current_section = None

    for row in range(3, sheet.nrows):
        cell_value = sheet.cell_value(row, 1)
        bezeichnung = clean_value(sheet.cell_value(row, 2))

        # Check for section headers
        if isinstance(cell_value, str):
            if '1. Ziffer' in cell_value or 'Hauptgefahr' in cell_value:
                current_section = 'H'  # Hauptgefahr
                continue
            elif '2. und 3. Ziffer' in cell_value or 'Zusatzgefahr' in cell_value:
                current_section = 'Z'  # Zusatzgefahr
                continue
            elif cell_value.startswith('-') or cell_value.startswith('Steht'):
                # Skip notes
                continue

        code = clean_value(cell_value)
        if not code or not bezeichnung:
            continue

        # Create unique code with section prefix
        if current_section:
            unique_code = f"{current_section}{code}"
        else:
            unique_code = code

        sortierung += 10
        entries.append(ProduktLookup(
            kategorie='gefahrengut',
            code=unique_code,
            bezeichnung=bezeichnung,
            zusatz_1=current_section,  # H = Hauptgefahr, Z = Zusatzgefahr
            zusatz_2=code,  # Original code
            sortierung=sortierung
        ))

    return entries


def import_dvd_bluray(sheet):
    """
    Import DVD und Blu-Ray Codes (21 Einträge).

    Sheet has two sections:
        - DVD: Rows 3-10, Regionalcode in column C (R1-R8)
        - Blu-Ray: Rows 16-18, Regionalcode in column C (A/1, B/2, C/3)

    Use Regionalcode (column C) as the code, with type prefix (DVD_, BR_).
    """
    entries = []
    sortierung = 0
    current_type = None

    for row in range(1, sheet.nrows):
        cell_b = sheet.cell_value(row, 1)

        # Check for section headers
        if isinstance(cell_b, str):
            if cell_b.strip() == 'DVD':
                current_type = 'DVD'
                continue
            elif cell_b.strip() == 'Blu-Ray':
                current_type = 'BR'
                continue
            elif cell_b.startswith('Quelle:') or not cell_b.strip():
                continue

        # Get regional code from column C
        regional_code = clean_value(sheet.cell_value(row, 2))

        # Skip header rows
        if not regional_code or regional_code == 'Regionalcode:':
            continue

        # Get description from column D or E depending on type
        if current_type == 'DVD':
            bezeichnung = clean_value(sheet.cell_value(row, 4))  # Region column
        else:
            bezeichnung = clean_value(sheet.cell_value(row, 3))  # Direct description for Blu-Ray

        if not bezeichnung:
            continue

        # Create unique code with type prefix
        unique_code = f"{current_type}_{regional_code}" if current_type else regional_code

        sortierung += 10
        entries.append(ProduktLookup(
            kategorie='dvd_bluray_codes',
            code=unique_code,
            bezeichnung=bezeichnung,
            zusatz_1=current_type,  # DVD or BR
            zusatz_2=regional_code,  # Original regional code
            sortierung=sortierung
        ))

    return entries


def import_gpc_brick(sheet):
    """
    Import GPC Brick (75 Einträge).

    Columns:
        B (1): GPC Brick (-> Code)
        C (2): Beschreibung (-> Bezeichnung)
        D (3): ETIM Klassen ID (-> zusatz_1)
        E (4): ETIM Klassen Beschreibung (-> zusatz_2)
    """
    entries = []
    sortierung = 0

    for row in range(3, sheet.nrows):
        code = clean_value(sheet.cell_value(row, 1))
        bezeichnung = clean_value(sheet.cell_value(row, 2))
        etim_id = clean_value(sheet.cell_value(row, 3))
        etim_bez = clean_value(sheet.cell_value(row, 4))

        if not code or not bezeichnung:
            continue

        sortierung += 10
        entries.append(ProduktLookup(
            kategorie='gpc_brick',
            code=code,
            bezeichnung=bezeichnung,
            zusatz_1=etim_id,
            zusatz_2=etim_bez,
            sortierung=sortierung
        ))

    return entries


def import_bamberger(sheet):
    """
    Import Bamberger Verzeichnis (93 Einträge).

    Columns:
        B (1): Code
        C (2): Hauptkategorie (-> zusatz_1)
        D (3): Beschreibung (-> Bezeichnung)
    """
    entries = []
    sortierung = 0

    for row in range(3, sheet.nrows):
        code = clean_value(sheet.cell_value(row, 1))
        hauptkategorie = clean_value(sheet.cell_value(row, 2))
        bezeichnung = clean_value(sheet.cell_value(row, 3))

        if not code or not bezeichnung:
            continue

        sortierung += 10
        entries.append(ProduktLookup(
            kategorie='bamberger',
            code=code,
            bezeichnung=bezeichnung,
            zusatz_1=hauptkategorie,
            sortierung=sortierung
        ))

    return entries


def import_saison(sheet):
    """
    Import Saisonkennzeichen (43 Einträge).

    Complex structure with monthly, quarterly and half-yearly codes.
    We extract all unique codes with their types.
    """
    entries = []
    sortierung = 0

    # Monthly codes (Monats-Sortimente): Row 5+ in columns C-F
    # Format: Jahr.Monat (e.g. 1.3.0.1 = ?)
    # Actually looking at the data, it seems like:
    # Column C: Jahr prefix (1)
    # Column D: Code part 1 (3)
    # Column E: Code part 2 (0)
    # Column F: Month (1-12)

    # Let's read the actual codes more carefully
    for row in range(5, sheet.nrows):
        # Monats-Sortimente (columns 2-5)
        month_parts = []
        for col in range(2, 6):
            val = clean_value(sheet.cell_value(row, col))
            if val:
                month_parts.append(val)

        if len(month_parts) >= 4:
            code = '.'.join(month_parts)
            month_num = month_parts[-1] if month_parts else ''
            month_names = {
                '1': 'Januar', '2': 'Februar', '3': 'März', '4': 'April',
                '5': 'Mai', '6': 'Juni', '7': 'Juli', '8': 'August',
                '9': 'September', '10': 'Oktober', '11': 'November', '12': 'Dezember'
            }
            bezeichnung = f"Monat: {month_names.get(month_num, month_num)}"

            sortierung += 10
            entries.append(ProduktLookup(
                kategorie='saison',
                code=code,
                bezeichnung=bezeichnung,
                zusatz_1='monat',
                sortierung=sortierung
            ))

        # Quartals-Sortimente (columns 7-9)
        quarter_parts = []
        for col in range(7, 10):
            val = clean_value(sheet.cell_value(row, col))
            if val:
                quarter_parts.append(val)

        if len(quarter_parts) >= 3:
            code = '.'.join(quarter_parts)
            quarter_num = quarter_parts[-1] if quarter_parts else ''
            quarter_names = {'1': 'Q1', '2': 'Q2', '3': 'Q3', '4': 'Q4'}
            bezeichnung = f"Quartal: {quarter_names.get(quarter_num, quarter_num)}"

            sortierung += 10
            entries.append(ProduktLookup(
                kategorie='saison',
                code=code,
                bezeichnung=bezeichnung,
                zusatz_1='quartal',
                sortierung=sortierung
            ))

        # Halbjahres-Sortimente (columns 12-14)
        half_parts = []
        for col in range(12, 15):
            val = clean_value(sheet.cell_value(row, col))
            if val:
                half_parts.append(val)

        if len(half_parts) >= 3:
            code = '.'.join(half_parts)
            half_num = half_parts[-1] if half_parts else ''
            half_names = {'1': '1. Halbjahr', '2': '2. Halbjahr'}
            bezeichnung = f"Halbjahr: {half_names.get(half_num, half_num)}"

            sortierung += 10
            entries.append(ProduktLookup(
                kategorie='saison',
                code=code,
                bezeichnung=bezeichnung,
                zusatz_1='halbjahr',
                sortierung=sortierung
            ))

    # Remove duplicates (based on code)
    seen = set()
    unique_entries = []
    for entry in entries:
        if entry.code not in seen:
            seen.add(entry.code)
            unique_entries.append(entry)

    return unique_entries


def import_mwst(sheet):
    """
    Import MwSt-Sätze (31 Einträge).

    Columns:
        B (1): Land
        C (2): Ländercode (-> Code)
        D (3): Normalsatz (-> zusatz_1)
        E (4): Ermäßigter Satz (-> zusatz_2)
        F (5): Stark ermäßigter Satz (-> zusatz_3)
        G (6): Zwischensatz (included in bezeichnung if relevant)
    """
    entries = []
    sortierung = 0

    for row in range(4, sheet.nrows):
        land = clean_value(sheet.cell_value(row, 1))
        code = clean_value(sheet.cell_value(row, 2))
        normalsatz = clean_value(sheet.cell_value(row, 3))
        ermaessigt = clean_value(sheet.cell_value(row, 4))
        stark_ermaessigt = clean_value(sheet.cell_value(row, 5))

        if not code or not land:
            continue

        bezeichnung = f"{land} (Normalsatz: {normalsatz}%)"

        sortierung += 10
        entries.append(ProduktLookup(
            kategorie='mwst_saetze',
            code=code,
            bezeichnung=bezeichnung,
            zusatz_1=normalsatz,
            zusatz_2=ermaessigt,
            zusatz_3=stark_ermaessigt,
            sortierung=sortierung
        ))

    return entries


def import_genre(sheet):
    """Import Genre (49 Einträge)."""
    return import_simple_codelist(sheet, 'genre', code_col=1, bez_col=1, data_start_row=3)


def import_plattform(sheet):
    """Import Plattform (20 Einträge)."""
    return import_simple_codelist(sheet, 'plattform', code_col=1, bez_col=1, data_start_row=3)


def import_gefahrstoffe(sheet):
    """
    Import Gefahrstoffe (135 Einträge).

    Three types:
        - P-Sätze (column B, 1)
        - H-Sätze (column E, 4)
        - EUH-Sätze (column H, 7)
    """
    entries = []
    sortierung = 0

    for row in range(4, sheet.nrows):
        # P-Sätze (column 1)
        p_code = clean_value(sheet.cell_value(row, 1))
        p_bez = clean_value(sheet.cell_value(row, 2)) if sheet.ncols > 2 else None
        if p_code and p_code.startswith('P'):
            sortierung += 10
            entries.append(ProduktLookup(
                kategorie='gefahrstoffe',
                code=p_code,
                bezeichnung=p_bez or p_code,
                zusatz_1='P-Satz',
                sortierung=sortierung
            ))

        # H-Sätze (column 4)
        if sheet.ncols > 4:
            h_code = clean_value(sheet.cell_value(row, 4))
            h_bez = clean_value(sheet.cell_value(row, 5)) if sheet.ncols > 5 else None
            if h_code and h_code.startswith('H'):
                sortierung += 10
                entries.append(ProduktLookup(
                    kategorie='gefahrstoffe',
                    code=h_code,
                    bezeichnung=h_bez or h_code,
                    zusatz_1='H-Satz',
                    sortierung=sortierung
                ))

        # EUH-Sätze (column 7)
        if sheet.ncols > 7:
            euh_code = clean_value(sheet.cell_value(row, 7))
            euh_bez = clean_value(sheet.cell_value(row, 8)) if sheet.ncols > 8 else None
            if euh_code and (euh_code.startswith('EUH') or euh_code.startswith('EU')):
                sortierung += 10
                entries.append(ProduktLookup(
                    kategorie='gefahrstoffe',
                    code=euh_code,
                    bezeichnung=euh_bez or euh_code,
                    zusatz_1='EUH-Satz',
                    sortierung=sortierung
                ))

    return entries


def import_lagerklassen(sheet):
    """Import Lagerklassen Gefahrstoffe (29 Einträge)."""
    return import_simple_codelist(sheet, 'lagerklassen', code_col=1, bez_col=2, data_start_row=3)


# Mapping: Sheet name -> import function
SHEET_IMPORTERS = {
    'Codeliste Länder': import_laender,
    'Gewichts- und Maßeinheiten': import_gewichtseinheiten,
    'Codeliste Währung': import_waehrungen,
    'Codeliste Batterien': import_batterien,
    'WEEE Kennzeichnung': import_weee,
    'Codeliste Gefahrengutschlüssel': import_gefahrengut,
    'Codeliste DVD und Blu-Ray Code': import_dvd_bluray,
    'GPCBrick': import_gpc_brick,
    'Bamberger Verzeichnis': import_bamberger,
    'Saisonkennzeichen': import_saison,
    'Codeliste MwSt.': import_mwst,
    'Codeliste Genre': import_genre,
    'Codeliste Plattform': import_plattform,
    'Codeliste Gefahrstoffe': import_gefahrstoffe,
    'Lagerklasse Gefahrstoffe': import_lagerklassen,
}


def main():
    """Main import function."""
    print("=" * 60)
    print("NTG Produkt-Codelisten Import")
    print("=" * 60)

    # Path to Excel file
    excel_path = 'docs/prd/module/PRD-009-produktdaten/NTG_Artikelstamm-Codelisten.xls'

    if not os.path.exists(excel_path):
        print(f"FEHLER: Excel-Datei nicht gefunden: {excel_path}")
        return 1

    # Create Flask app context
    app = create_app()

    with app.app_context():
        # Check if table already has data
        existing_count = ProduktLookup.query.count()
        if existing_count > 0:
            print(f"\n⚠️  ProduktLookup enthält bereits {existing_count} Einträge.")
            response = input("Alle löschen und neu importieren? (j/N): ")
            if response.lower() != 'j':
                print("Abbruch.")
                return 0

            # Delete all existing entries
            ProduktLookup.query.delete()
            db.session.commit()
            print(f"✓ {existing_count} Einträge gelöscht.\n")

        # Open Excel workbook
        print(f"Öffne: {excel_path}")
        wb = xlrd.open_workbook(excel_path)

        total_imported = 0
        all_entries = []
        seen_keys = set()  # Track (kategorie, code) pairs to avoid duplicates

        # Process each sheet
        for sheet_name, importer in SHEET_IMPORTERS.items():
            try:
                sheet = wb.sheet_by_name(sheet_name)
                entries = importer(sheet)

                # Deduplicate entries
                unique_entries = []
                for entry in entries:
                    key = (entry.kategorie, entry.code)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        unique_entries.append(entry)
                    else:
                        print(f"    ⚠️  Duplikat übersprungen: {entry.kategorie}:{entry.code}")

                all_entries.extend(unique_entries)
                print(f"  ✓ {sheet_name}: {len(unique_entries)} Einträge")
                total_imported += len(unique_entries)

            except Exception as e:
                print(f"  ✗ {sheet_name}: FEHLER - {e}")
                import traceback
                traceback.print_exc()

        # Add all entries to session
        for entry in all_entries:
            db.session.add(entry)

        # Commit all changes
        db.session.commit()

        print("-" * 60)
        print(f"✓ Import abgeschlossen: {total_imported} Einträge")

        # Summary by category
        print("\n=== Zusammenfassung nach Kategorie ===")
        counts = ProduktLookup.count_by_kategorie()
        for kategorie, count in sorted(counts.items()):
            print(f"  {kategorie}: {count}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
