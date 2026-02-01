#!/usr/bin/env python3
"""
Generate Structure JSON for Static Media Viewer

Scans a media directory with Year/Month/Day structure and generates
a structure.json file for the static web viewer.

Usage:
    python generate_structure.py "C:\\Sorted_Media" --output viewer/structure.json --prefix media
"""

import argparse
import json
import os
from pathlib import Path
from datetime import datetime


IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif', '.webp'}
RAW_FORMATS = {'.cr2', '.cr3', '.crw', '.nef', '.arw', '.dng', '.raf', '.orf', '.rw2', '.pef', '.srw', '.raw'}
VIDEO_FORMATS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.mpg', '.mpeg'}
AUDIO_FORMATS = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma', '.opus', '.aiff', '.alac'}
SUPPORTED_FORMATS = IMAGE_FORMATS | RAW_FORMATS | VIDEO_FORMATS | AUDIO_FORMATS


def get_media_type(suffix):
    """Determine media type from file extension."""
    suffix = suffix.lower()
    if suffix in IMAGE_FORMATS or suffix in RAW_FORMATS:
        return "image"
    elif suffix in VIDEO_FORMATS:
        return "video"
    elif suffix in AUDIO_FORMATS:
        return "audio"
    return "unknown"


def get_files_in_folder(folder, prefix):
    """Get all media files in a folder with relative web paths."""
    files = []
    for file in sorted(folder.iterdir(), key=lambda f: f.name):
        if file.is_file() and file.suffix.lower() in SUPPORTED_FORMATS:
            # Web-relative path: prefix/Year/Month/Day/file.jpg
            rel_path = f"{prefix}/{file.relative_to(folder.parents[len(folder.parts) - len(folder.parts)])}"
            # Simpler: just use the folder structure relative to source root
            files.append({
                'name': file.name,
                'path': None,  # will be set by caller
                'size': file.stat().st_size,
                'modified': datetime.fromtimestamp(file.stat().st_mtime).isoformat(),
                'type': get_media_type(file.suffix)
            })
    return files


def scan_directory(base_path, prefix):
    """Scan directory and build structure with web-relative paths."""
    base_path = Path(base_path)
    structure = {
        'years': {},
        'unknown_date': [],
        'invalid_date': [],
        'total_files': 0
    }

    if not base_path.exists():
        print(f"Fehler: Verzeichnis '{base_path}' existiert nicht.")
        return structure

    # Scan years
    for year_dir in sorted(base_path.iterdir(), key=lambda d: d.name):
        if year_dir.is_dir() and year_dir.name.isdigit():
            year = year_dir.name
            structure['years'][year] = {}

            # Scan months
            for month_dir in sorted(year_dir.iterdir(), key=lambda d: d.name):
                if month_dir.is_dir() and not month_dir.name.startswith('_'):
                    month = month_dir.name
                    structure['years'][year][month] = {}

                    # Check for day folders
                    has_day_folders = any(
                        item.is_dir() and item.name.lstrip('0').isdigit()
                        for item in month_dir.iterdir()
                    )

                    if has_day_folders:
                        for day_dir in sorted(month_dir.iterdir(), key=lambda d: d.name):
                            if day_dir.is_dir() and day_dir.name.lstrip('0').isdigit():
                                day = day_dir.name
                                files = collect_files(day_dir, base_path, prefix)
                                if files:
                                    structure['years'][year][month][day] = files
                                    structure['total_files'] += len(files)
                    else:
                        files = collect_files(month_dir, base_path, prefix)
                        if files:
                            structure['years'][year][month]['images'] = files
                            structure['total_files'] += len(files)

            # Remove empty months
            for month_key in list(structure['years'][year].keys()):
                if not structure['years'][year][month_key]:
                    del structure['years'][year][month_key]

            # Remove empty years
            if not structure['years'][year]:
                del structure['years'][year]

    # Scan special folders
    unknown_dir = base_path / '_unknown_date'
    if unknown_dir.exists():
        files = collect_files(unknown_dir, base_path, prefix)
        structure['unknown_date'] = files
        structure['total_files'] += len(files)

    invalid_dir = base_path / '_invalid_date'
    if invalid_dir.exists():
        files = collect_files(invalid_dir, base_path, prefix)
        structure['invalid_date'] = files

    return structure


def collect_files(folder, base_path, prefix):
    """Collect all media files in a folder with web-relative paths."""
    files = []
    for file in sorted(folder.iterdir(), key=lambda f: f.name):
        if file.is_file() and file.suffix.lower() in SUPPORTED_FORMATS:
            # Build web-relative path: prefix/2024/01-January/01/foto.jpg
            rel_to_base = file.relative_to(base_path)
            web_path = f"{prefix}/{str(rel_to_base).replace(os.sep, '/')}"

            files.append({
                'name': file.name,
                'path': web_path,
                'size': file.stat().st_size,
                'modified': datetime.fromtimestamp(file.stat().st_mtime).isoformat(),
                'type': get_media_type(file.suffix)
            })
    return files


def main():
    parser = argparse.ArgumentParser(
        description='Generiert structure.json fuer den statischen Media Viewer'
    )
    parser.add_argument(
        'source',
        help='Pfad zum sortierten Medienordner (Jahr/Monat/Tag-Struktur)'
    )
    parser.add_argument(
        '--output', '-o',
        default='structure.json',
        help='Ausgabepfad fuer die JSON-Datei (Standard: structure.json)'
    )
    parser.add_argument(
        '--prefix', '-p',
        default='media',
        help='URL-Prefix fuer Medienpfade (Standard: media)'
    )

    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        print(f"Fehler: '{source}' existiert nicht.")
        return

    print(f"Scanne: {source}")
    structure = scan_directory(source, args.prefix)

    # Write JSON
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(structure, f, ensure_ascii=False, indent=2)

    print(f"Fertig! {structure['total_files']} Dateien gefunden.")
    print(f"  Jahre: {len(structure['years'])}")
    print(f"  Unbekanntes Datum: {len(structure['unknown_date'])}")
    print(f"  Ausgabe: {output_path.resolve()}")


if __name__ == '__main__':
    main()
