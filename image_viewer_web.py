#!/usr/bin/env python3
"""
Media Viewer Web - Web-based application for viewing sorted media (images, videos, audio)
"""

from flask import Flask, render_template, send_file, jsonify, request
import os
from pathlib import Path
import json
from datetime import datetime
import mimetypes
import webbrowser
import threading
import time
import sys
import io
import exifread
from PIL import Image

# Import i18n for language settings
try:
    from i18n import set_language, get_language
except ImportError:
    def set_language(lang): pass
    def get_language(): return 'en'

def get_resource_path(relative_path):
    """Ermittelt den korrekten Pfad zu Ressourcen sowohl für normale Python-Ausführung als auch für exe-Dateien"""
    try:
        # PyInstaller erstellt einen temporären Ordner und speichert den Pfad in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Normale Python-Ausführung
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)

# Konfiguriere Flask mit dem korrekten Template-Pfad
template_dir = get_resource_path('templates')
app = Flask(__name__, template_folder=template_dir)

class ImageViewer:
    def __init__(self, base_paths: list):
        # Unterstützt mehrere Pfade
        if isinstance(base_paths, str):
            base_paths = [base_paths]
        self.base_paths = [Path(p.strip()) for p in base_paths if p.strip()]
        self.image_formats = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif', '.webp'}
        self.raw_formats = {'.cr2', '.cr3', '.crw', '.nef', '.arw', '.dng', '.raf', '.orf', '.rw2', '.pef', '.srw', '.raw'}
        self.video_formats = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.mpg', '.mpeg'}
        self.audio_formats = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma', '.opus', '.aiff', '.alac'}
        self.supported_formats = self.image_formats | self.raw_formats | self.video_formats | self.audio_formats
        # Mapping von relativen Pfaden zu absoluten Pfaden
        self.path_mapping = {}
    
    def scan_directory(self):
        """Scannt alle Verzeichnisse und erstellt eine kombinierte Struktur"""
        structure = {
            'years': {},
            'unknown_date': [],
            'invalid_date': [],
            'total_files': 0
        }

        # Scanne alle Basis-Pfade
        for base_path in self.base_paths:
            if not base_path.exists():
                continue

            # Scanne Jahre
            for year_dir in base_path.iterdir():
                if year_dir.is_dir() and year_dir.name.isdigit():
                    year = year_dir.name
                    if year not in structure['years']:
                        structure['years'][year] = {}

                    # Scanne Monate
                    for month_dir in year_dir.iterdir():
                        if month_dir.is_dir() and not month_dir.name.startswith('_'):
                            month = month_dir.name
                            if month not in structure['years'][year]:
                                structure['years'][year][month] = {}

                            # Prüfe ob Tages-Sortierung (flexiblere Erkennung)
                            has_day_folders = any(
                                item.is_dir() and (
                                    item.name.isdigit() or  # z.B. "1", "15"
                                    (item.name.isdigit() and len(item.name) <= 2) or  # z.B. "01", "02"
                                    item.name.lstrip('0').isdigit()  # z.B. "01", "02", "031"
                                )
                                for item in month_dir.iterdir()
                            )

                            if has_day_folders:
                                # Tages-Sortierung
                                for day_dir in month_dir.iterdir():
                                    if day_dir.is_dir() and (
                                        day_dir.name.isdigit() or
                                        day_dir.name.lstrip('0').isdigit()
                                    ):
                                        day = day_dir.name
                                        images = self.get_images_in_folder(day_dir, base_path)
                                        if images:  # Nur Tage mit Medien hinzufügen
                                            if day not in structure['years'][year][month]:
                                                structure['years'][year][month][day] = []
                                            structure['years'][year][month][day].extend(images)
                                            structure['total_files'] += len(images)
                            else:
                                # Monats-Sortierung
                                images = self.get_images_in_folder(month_dir, base_path)
                                if images:  # Nur Monate mit Medien hinzufügen
                                    if 'images' not in structure['years'][year][month]:
                                        structure['years'][year][month]['images'] = []
                                    structure['years'][year][month]['images'].extend(images)
                                    structure['total_files'] += len(images)

            # Scanne spezielle Ordner
            unknown_dir = base_path / '_unknown_date'
            if unknown_dir.exists():
                unknown_files = self.get_images_in_folder(unknown_dir, base_path)
                structure['unknown_date'].extend(unknown_files)
                structure['total_files'] += len(unknown_files)

            # Invalid date wird separat behandelt, aber nicht in Gesamtstatistik gezählt
            invalid_dir = base_path / '_invalid_date'
            if invalid_dir.exists():
                invalid_files = self.get_images_in_folder(invalid_dir, base_path)
                structure['invalid_date'].extend(invalid_files)

        return structure
    
    def get_images_in_folder(self, folder: Path, base_path: Path = None):
        """Holt alle Medien aus einem Ordner"""
        if base_path is None:
            base_path = self.base_paths[0] if self.base_paths else folder

        files = []
        for file in folder.iterdir():
            if file.is_file() and file.suffix.lower() in self.supported_formats:
                # Bestimme Medientyp
                suffix = file.suffix.lower()
                if suffix in self.image_formats or suffix in self.raw_formats:
                    media_type = "image"
                elif suffix in self.video_formats:
                    media_type = "video"
                elif suffix in self.audio_formats:
                    media_type = "audio"
                else:
                    media_type = "unknown"

                # Relativer Pfad für Web-Zugriff - mit Pfad-Index für eindeutige Zuordnung
                rel_path = file.relative_to(base_path)
                path_index = self.base_paths.index(base_path) if base_path in self.base_paths else 0
                unique_path = f"{path_index}/{str(rel_path).replace(chr(92), '/')}"

                # Speichere Mapping für späteres Serving
                self.path_mapping[unique_path] = str(file)

                files.append({
                    'name': file.name,
                    'path': unique_path,
                    'size': file.stat().st_size,
                    'modified': datetime.fromtimestamp(file.stat().st_mtime).isoformat(),
                    'type': media_type
                })
        return sorted(files, key=lambda x: x['name'])

# Globale Viewer-Instanz
viewer = None

@app.route('/')
def index():
    """Hauptseite"""
    return render_template('index.html')

@app.route('/api/structure')
def get_structure():
    """API: Gibt die Ordnerstruktur zurück"""
    global viewer
    if not viewer:
        return jsonify({'error': 'Kein Verzeichnis ausgewählt'}), 400
    
    structure = viewer.scan_directory()
    return jsonify(structure)

@app.route('/api/set_directory', methods=['POST'])
def set_directory():
    """API: Setzt die Basis-Verzeichnisse (unterstützt mehrere Pfade)"""
    global viewer
    data = request.json
    directories = data.get('directories', [])

    # Rückwärtskompatibilität: einzelnes directory auch akzeptieren
    if not directories and data.get('directory'):
        directories = [data.get('directory')]

    if not directories:
        return jsonify({'error': 'Keine Verzeichnisse angegeben'}), 400

    # Validiere alle Pfade
    valid_dirs = []
    invalid_dirs = []
    for d in directories:
        d = d.strip()
        if d and os.path.exists(d):
            valid_dirs.append(d)
        elif d:
            invalid_dirs.append(d)

    if not valid_dirs:
        return jsonify({'error': f'Keine gültigen Verzeichnisse gefunden. Ungültig: {", ".join(invalid_dirs)}'}), 400

    viewer = ImageViewer(valid_dirs)
    return jsonify({
        'success': True,
        'loaded_paths': valid_dirs,
        'invalid_paths': invalid_dirs
    })

@app.route('/api/set_language', methods=['POST'])
def api_set_language():
    """API: Sets the application language"""
    data = request.json
    language = data.get('language', 'en')
    if language in ['en', 'de']:
        set_language(language)
        return jsonify({'success': True, 'language': language})
    return jsonify({'error': 'Invalid language'}), 400

def extract_raw_thumbnail(file_path):
    """Extrahiert eingebettetes JPEG-Vorschaubild aus RAW-Datei"""
    try:
        with open(file_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)

            # Versuche JPEGInterchangeFormat (eingebettetes JPEG)
            if 'JPEGThumbnail' in tags:
                return tags['JPEGThumbnail']

            # Alternative: Suche nach JPEG-Markern im File
            f.seek(0)
            data = f.read()

            # Suche nach JPEG SOI (Start of Image) Marker
            jpeg_start = data.find(b'\xff\xd8\xff')
            if jpeg_start > 0:
                # Suche nach JPEG EOI (End of Image) Marker
                jpeg_end = data.find(b'\xff\xd9', jpeg_start)
                if jpeg_end > jpeg_start:
                    return data[jpeg_start:jpeg_end + 2]
    except Exception:
        pass
    return None

@app.route('/media/<path:media_path>')
def serve_media(media_path):
    """Liefert Medien aus (RAW zeigt eingebettete Vorschau)"""
    if not viewer:
        return "Kein Verzeichnis gesetzt", 400

    # Verwende path_mapping für mehrere Pfade
    if media_path in viewer.path_mapping:
        full_path = Path(viewer.path_mapping[media_path])
    else:
        # Fallback: versuche ersten Pfad (Rückwärtskompatibilität)
        if viewer.base_paths:
            full_path = viewer.base_paths[0] / media_path
        else:
            return "Datei nicht gefunden", 404

    if not full_path.exists():
        return "Datei nicht gefunden", 404

    # RAW-Dateien: eingebettetes JPEG-Vorschaubild extrahieren
    suffix = full_path.suffix.lower()
    if suffix in viewer.raw_formats:
        thumbnail_data = extract_raw_thumbnail(str(full_path))
        if thumbnail_data:
            img_io = io.BytesIO(thumbnail_data)
            return send_file(img_io, mimetype='image/jpeg')
        else:
            # Fallback: Placeholder-Bild generieren
            img = Image.new('RGB', (400, 300), color=(50, 50, 50))
            img_io = io.BytesIO()
            img.save(img_io, 'JPEG')
            img_io.seek(0)
            return send_file(img_io, mimetype='image/jpeg')

    return send_file(full_path)

@app.route('/api/media_info/<path:media_path>')
def get_media_info(media_path):
    """API: Gibt Informationen über eine Medien-Datei zurück"""
    if not viewer:
        return jsonify({'error': 'Kein Verzeichnis gesetzt'}), 400

    # Verwende path_mapping für mehrere Pfade
    if media_path in viewer.path_mapping:
        full_path = Path(viewer.path_mapping[media_path])
    else:
        # Fallback: versuche ersten Pfad
        if viewer.base_paths:
            full_path = viewer.base_paths[0] / media_path
        else:
            return jsonify({'error': 'Datei nicht gefunden'}), 404

    if not full_path.exists():
        return jsonify({'error': 'Datei nicht gefunden'}), 404
    
    stat = full_path.stat()
    
    # Bestimme Medientyp
    suffix = full_path.suffix.lower()
    if suffix in viewer.image_formats or suffix in viewer.raw_formats:
        media_type = "image"
    elif suffix in viewer.video_formats:
        media_type = "video"
    elif suffix in viewer.audio_formats:
        media_type = "audio"
    else:
        media_type = "unknown"
    
    return jsonify({
        'name': full_path.name,
        'type': media_type,
        'size': stat.st_size,
        'size_mb': round(stat.st_size / (1024 * 1024), 2),
        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
        'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
        'path': str(full_path)
    })

def open_browser():
    """Öffnet den Browser nach einem kurzen Delay"""
    time.sleep(1.5)  # Kurze Pause, damit der Server Zeit hat zu starten
    webbrowser.open('http://127.0.0.1:5000')

if __name__ == '__main__':
    # Starte Browser nur einmal (verhindert doppeltes Öffnen im Debug-Modus)
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        threading.Timer(1.5, open_browser).start()
    app.run(debug=True, host='127.0.0.1', port=5000) 