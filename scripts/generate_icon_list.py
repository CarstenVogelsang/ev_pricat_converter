#!/usr/bin/env python3
"""
Script to generate tabler-icons-list.json with tags from the official @tabler/icons npm package.

Downloads icons.json from jsDelivr CDN and transforms it to a compact format for the icon picker.

Usage:
    uv run python scripts/generate_icon_list.py
"""

import json
import urllib.request
import urllib.error
from pathlib import Path


CDN_URL = "https://cdn.jsdelivr.net/npm/@tabler/icons@latest/icons.json"
OUTPUT_PATH = Path(__file__).parent.parent / "app" / "static" / "js" / "tabler-icons-list.json"


def download_icons_json() -> dict:
    """Download icons.json from jsDelivr CDN."""
    print(f"Downloading icons.json from {CDN_URL}...")

    try:
        with urllib.request.urlopen(CDN_URL, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"Downloaded {len(data)} icons")
            return data
    except urllib.error.URLError as e:
        print(f"Error downloading: {e}")
        raise


def transform_icons(icons_data: dict) -> list:
    """
    Transform icons.json to compact format for icon picker.

    Input format:
    {
        "icon-name": {
            "name": "icon-name",
            "category": "Category",
            "tags": ["tag1", "tag2", ...],
            "styles": {...}
        }
    }

    Output format:
    [
        {"name": "ti-icon-name", "tags": ["tag1", "tag2", ...]},
        ...
    ]
    """
    result = []

    for icon_name, icon_data in icons_data.items():
        # Skip if no outline style (we only use outline icons)
        if 'styles' in icon_data and 'outline' not in icon_data.get('styles', {}):
            continue

        # Get tags, filter out non-strings (some have integers)
        tags = icon_data.get('tags', [])
        tags = [str(tag) for tag in tags if tag]  # Convert to string and filter empty

        # Add category as a tag too (for searching by category)
        category = icon_data.get('category', '')
        if category and category.lower() not in [t.lower() for t in tags]:
            tags.append(category)

        result.append({
            "name": f"ti-{icon_name}",
            "tags": tags
        })

    # Sort by name for consistency
    result.sort(key=lambda x: x['name'])

    return result


def save_json(data: list, path: Path) -> None:
    """Save JSON data to file with compact formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)

    # Use compact JSON to reduce file size
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

    # Also create a readable version for debugging
    debug_path = path.with_suffix('.debug.json')
    with open(debug_path, 'w', encoding='utf-8') as f:
        json.dump(data[:20], f, ensure_ascii=False, indent=2)  # Only first 20 for debugging

    file_size_kb = path.stat().st_size / 1024
    print(f"Saved {len(data)} icons to {path}")
    print(f"File size: {file_size_kb:.1f} KB")


def main():
    """Main entry point."""
    print("=" * 60)
    print("Tabler Icons List Generator")
    print("=" * 60)

    # Download
    icons_data = download_icons_json()

    # Transform
    print("\nTransforming to compact format...")
    transformed = transform_icons(icons_data)

    # Save
    print(f"\nSaving to {OUTPUT_PATH}...")
    save_json(transformed, OUTPUT_PATH)

    # Show sample
    print("\nSample entries:")
    for icon in transformed[:5]:
        print(f"  {icon['name']}: {icon['tags'][:5]}...")

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
