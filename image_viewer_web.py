#!/usr/bin/env python3
"""
Medien Viewer Web - Webbasierte Anwendung zum Betrachten sortierter Medien (Bilder, Videos, Audio)
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
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.image_formats = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif', '.webp'}
        self.video_formats = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.mpg', '.mpeg'}
        self.audio_formats = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma', '.opus', '.aiff', '.alac'}
        self.supported_formats = self.image_formats | self.video_formats | self.audio_formats
    
    def scan_directory(self):
        """Scannt das Verzeichnis und erstellt eine Struktur"""
        structure = {
            'years': {},
            'unknown_date': [],
            'invalid_date': [],
            'total_files': 0
        }
        
        if not self.base_path.exists():
            return structure
        
        # Scanne Jahre
        for year_dir in self.base_path.iterdir():
            if year_dir.is_dir() and year_dir.name.isdigit():
                year = year_dir.name
                structure['years'][year] = {}
                
                # Scanne Monate
                for month_dir in year_dir.iterdir():
                    if month_dir.is_dir() and not month_dir.name.startswith('_'):
                        month = month_dir.name
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
                                    images = self.get_images_in_folder(day_dir)
                                    if images:  # Nur Tage mit Medien hinzufügen
                                        structure['years'][year][month][day] = images
                                        structure['total_files'] += len(images)
                        else:
                            # Monats-Sortierung
                            images = self.get_images_in_folder(month_dir)
                            if images:  # Nur Monate mit Medien hinzufügen
                                structure['years'][year][month]['images'] = images
                                structure['total_files'] += len(images)
        
        # Scanne spezielle Ordner
        unknown_dir = self.base_path / '_unknown_date'
        if unknown_dir.exists():
            structure['unknown_date'] = self.get_images_in_folder(unknown_dir)
            structure['total_files'] += len(structure['unknown_date'])
        
        # Invalid date wird separat behandelt, aber nicht in Gesamtstatistik gezählt
        invalid_dir = self.base_path / '_invalid_date'
        if invalid_dir.exists():
            structure['invalid_date'] = self.get_images_in_folder(invalid_dir)
            # Nicht zur total_files hinzufügen - wird als separater Bereich angezeigt
        
        return structure
    
    def get_images_in_folder(self, folder: Path):
        """Holt alle Medien aus einem Ordner"""
        files = []
        for file in folder.iterdir():
            if file.is_file() and file.suffix.lower() in self.supported_formats:
                # Bestimme Medientyp
                suffix = file.suffix.lower()
                if suffix in self.image_formats:
                    media_type = "image"
                elif suffix in self.video_formats:
                    media_type = "video"
                elif suffix in self.audio_formats:
                    media_type = "audio"
                else:
                    media_type = "unknown"
                
                # Relativer Pfad für Web-Zugriff
                rel_path = file.relative_to(self.base_path)
                files.append({
                    'name': file.name,
                    'path': str(rel_path).replace('\\', '/'),
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
    """API: Setzt das Basis-Verzeichnis"""
    global viewer
    data = request.json
    directory = data.get('directory')
    
    if not directory or not os.path.exists(directory):
        return jsonify({'error': 'Verzeichnis existiert nicht'}), 400
    
    viewer = ImageViewer(directory)
    return jsonify({'success': True})

@app.route('/media/<path:media_path>')
def serve_media(media_path):
    """Liefert Medien aus"""
    if not viewer:
        return "Kein Verzeichnis gesetzt", 400
    
    full_path = viewer.base_path / media_path
    if not full_path.exists():
        return "Datei nicht gefunden", 404
    
    return send_file(full_path)

@app.route('/api/media_info/<path:media_path>')
def get_media_info(media_path):
    """API: Gibt Informationen über eine Medien-Datei zurück"""
    if not viewer:
        return jsonify({'error': 'Kein Verzeichnis gesetzt'}), 400
    
    full_path = viewer.base_path / media_path
    if not full_path.exists():
        return jsonify({'error': 'Datei nicht gefunden'}), 404
    
    stat = full_path.stat()
    
    # Bestimme Medientyp
    suffix = full_path.suffix.lower()
    if suffix in viewer.image_formats:
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