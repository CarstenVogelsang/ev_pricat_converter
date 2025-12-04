"""Utility functions for pricat-converter."""
import re
from typing import Optional, Tuple


def strip_leading_zeros(value: str) -> str:
    """
    Remove leading zeros from a string value.

    Used for normalizing VEDES_IDs which may come with leading zeros
    from PRICAT files but should be stored without them.

    Args:
        value: String value potentially with leading zeros

    Returns:
        String with leading zeros removed, or '0' if value is all zeros

    Examples:
        >>> strip_leading_zeros('0000001872')
        '1872'
        >>> strip_leading_zeros('1872')
        '1872'
        >>> strip_leading_zeros('0000')
        '0'
        >>> strip_leading_zeros('')
        ''
    """
    if not value:
        return ''

    stripped = value.lstrip('0')

    # If the value was all zeros, return '0'
    if not stripped and value:
        return '0'

    return stripped


def parse_pricat_filename(filename: str) -> Optional[Tuple[str, str]]:
    """
    Parse VEDES_ID and supplier name from PRICAT filename.

    Expected format: pricat_{vedes_id}_{supplier_name}_{version}.csv
    Example: pricat_1872_Lego Spielwaren GmbH_0.csv

    Args:
        filename: PRICAT filename

    Returns:
        Tuple of (vedes_id, supplier_name) or None if parsing fails

    Examples:
        >>> parse_pricat_filename('pricat_1872_Lego Spielwaren GmbH_0.csv')
        ('1872', 'Lego Spielwaren GmbH')
        >>> parse_pricat_filename('pricat_123_Supplier Name_1.csv')
        ('123', 'Supplier Name')
    """
    if not filename:
        return None

    # Pattern: pricat_{digits}_{name}_{digits}.csv
    match = re.match(r'^pricat_(\d+)_(.+?)_\d+\.csv$', filename, re.IGNORECASE)
    if match:
        vedes_id = strip_leading_zeros(match.group(1))
        supplier_name = match.group(2).strip()
        return (vedes_id, supplier_name)

    return None
