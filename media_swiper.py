#!/usr/bin/env python3
"""
Media Swiper - Tinder-style media sorting app
Swipe left (trash) or right (keep) to sort your media files.
Supports the sorted folder structure from Image Sorter (Year/Month folders).
"""

import os
import sys
import json
import shutil
import webbrowser
import threading
import time
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_file
import mimetypes

import re

# Import i18n for language settings
try:
    from i18n import set_language, get_language
except ImportError:
    def set_language(lang): pass
    def get_language(): return 'en'

# Initialize Flask
app = Flask(__name__)

# Supported formats (comprehensive list)
IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif', '.heic', '.heif', '.ico', '.svg'}
RAW_FORMATS = {'.cr2', '.cr3', '.crw', '.nef', '.arw', '.dng', '.raf', '.orf', '.rw2', '.pef', '.srw', '.raw', '.3fr', '.dcr', '.kdc', '.mrw', '.nrw', '.rwl', '.x3f'}
VIDEO_FORMATS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.m4v', '.3gp', '.mpg', '.mpeg', '.wmv', '.vob', '.ogv', '.mts', '.m2ts', '.ts'}
AUDIO_FORMATS = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.opus', '.m4a', '.wma', '.alac', '.aiff', '.ape'}

ALL_FORMATS = IMAGE_FORMATS | RAW_FORMATS | VIDEO_FORMATS | AUDIO_FORMATS

# Log file name
LOG_FILENAME = "swiper_log.json"

# Global state
current_folder = None
trash_folder = None
media_files = []
current_index = 0
stats = {"kept": 0, "trashed": 0, "total": 0, "skipped": 0}
session_log = {"folder": "", "started": "", "entries": [], "settings": {}}
settings = {
    "recursive": True,
    "skip_already_swiped": True,
    "include_images": True,
    "include_raw": True,
    "include_video": True,
    "include_audio": True,
    "trash_folder_name": "_trash",
    "sort_order": "oldest"  # oldest, newest, name, random
}


def get_media_type(filepath):
    """Determine media type from file extension."""
    ext = Path(filepath).suffix.lower()
    if ext in IMAGE_FORMATS:
        return "image"
    elif ext in RAW_FORMATS:
        return "raw"
    elif ext in VIDEO_FORMATS:
        return "video"
    elif ext in AUDIO_FORMATS:
        return "audio"
    return "unknown"


def get_date_from_path(filepath):
    """Extract date from folder path. Supports:
    - YYYY/MM-Month/DD (e.g., 2021/02-February/17)
    - MM-Month/YYYY (e.g., 02-February/2021)
    """
    parts = Path(filepath).parts

    # Pattern 1: YYYY / MM-MonthName / DD
    for i, part in enumerate(parts):
        if re.match(r'^\d{4}$', part) and i + 2 < len(parts):
            year = part
            month_match = re.match(r'^(\d{2})-', parts[i + 1])
            day_match = re.match(r'^(\d{2})$', parts[i + 2])
            if month_match and day_match:
                return f"{year}-{month_match.group(1)}-{day_match.group(1)}"

    # Pattern 2: MM-MonthName / YYYY (no day)
    for i, part in enumerate(parts):
        month_match = re.match(r'^(\d{2})-', part)
        if month_match and i + 1 < len(parts):
            year_match = re.match(r'^(\d{4})$', parts[i + 1])
            if year_match:
                return f"{year_match.group(1)}-{month_match.group(1)}-01"

    return None


def get_allowed_formats():
    """Get allowed formats based on current settings."""
    formats = set()
    if settings["include_images"]:
        formats.update(IMAGE_FORMATS)
    if settings["include_raw"]:
        formats.update(RAW_FORMATS)
    if settings["include_video"]:
        formats.update(VIDEO_FORMATS)
    if settings["include_audio"]:
        formats.update(AUDIO_FORMATS)
    return formats


def scan_media_files(folder, recursive=True):
    """Scan folder for all supported media files."""
    files = []
    folder_path = Path(folder)
    allowed_formats = get_allowed_formats()
    trash_name = settings["trash_folder_name"]

    if not folder_path.exists():
        return files

    def scan_dir(dir_path):
        try:
            for item in dir_path.iterdir():
                # Skip trash folders and hidden folders
                if item.is_dir():
                    if item.name.startswith('_') or item.name.startswith('.'):
                        continue
                    if recursive:
                        scan_dir(item)
                elif item.is_file() and item.suffix.lower() in allowed_formats:
                    files.append(str(item))
        except PermissionError:
            pass

    scan_dir(folder_path)

    # Sort based on settings
    sort_order = settings.get("sort_order", "oldest")
    if isinstance(sort_order, str):
        sort_order = sort_order.strip().lower()
    print(f"[DEBUG] Sort order: '{sort_order}' (repr: {repr(sort_order)})")

    if sort_order == "random":
        import random
        random.shuffle(files)
    elif sort_order == "name":
        files.sort(key=lambda x: Path(x).name.lower())
    elif sort_order == "newest":
        # Sort by date from folder path, newest first
        files.sort(key=lambda x: get_date_from_path(x) or "0000-00-00", reverse=True)
        print(f"[DEBUG] Sorted newest first")
    else:  # oldest (default)
        # Sort by date from folder path, oldest first
        files.sort(key=lambda x: get_date_from_path(x) or "9999-99-99", reverse=False)
        print(f"[DEBUG] Sorted oldest first")

    # Show first few files with their dates for verification
    if files:
        print(f"[DEBUG] First 3 files after sorting:")
        for f in files[:3]:
            date = get_date_from_path(f) or "unknown"
            print(f"  {Path(f).name}: {date}")

    return files


def load_session_log(folder):
    """Load existing session log if it exists."""
    log_path = Path(folder) / LOG_FILENAME
    if log_path.exists():
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return None


def save_session_log():
    """Save current session log to file."""
    global session_log
    if not current_folder:
        return

    log_path = Path(current_folder) / LOG_FILENAME
    session_log["last_updated"] = datetime.now().isoformat()

    try:
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(session_log, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Error saving log: {e}")


def get_swiped_files(log_data):
    """Get set of already swiped file paths from log."""
    if not log_data or "entries" not in log_data:
        return set()
    return {entry["filepath"] for entry in log_data["entries"]}


def add_log_entry(filepath, action, filename):
    """Add entry to session log."""
    entry = {
        "filepath": filepath,
        "filename": filename,
        "action": action,
        "timestamp": datetime.now().isoformat(),
        "relative_path": str(Path(filepath).relative_to(current_folder)) if current_folder else filename
    }
    session_log["entries"].append(entry)
    save_session_log()


def remove_last_log_entry():
    """Remove last entry from session log (for undo)."""
    if session_log["entries"]:
        session_log["entries"].pop()
        save_session_log()


@app.route('/')
def index():
    """Main page."""
    return render_template('swiper.html')


@app.route('/api/init', methods=['POST'])
def init_session():
    """Initialize a new sorting session."""
    global current_folder, trash_folder, media_files, current_index, stats, session_log, settings

    data = request.json
    folder = data.get('folder', '')
    user_settings = data.get('settings', {})

    if not folder or not os.path.isdir(folder):
        return jsonify({"error": "Ungültiger Ordnerpfad"}), 400

    # Update settings
    for key in settings:
        if key in user_settings:
            settings[key] = user_settings[key]

    current_folder = folder
    trash_folder = os.path.join(folder, settings["trash_folder_name"])

    # Create trash folder if it doesn't exist
    os.makedirs(trash_folder, exist_ok=True)

    # Load existing session log
    existing_log = load_session_log(folder)
    swiped_files = set()

    if existing_log and settings["skip_already_swiped"]:
        swiped_files = get_swiped_files(existing_log)
        # Continue existing session
        session_log = existing_log
        session_log["resumed"] = datetime.now().isoformat()
        session_log["settings"] = settings.copy()  # Update with current settings
    else:
        # Start new session
        session_log = {
            "folder": folder,
            "started": datetime.now().isoformat(),
            "settings": settings.copy(),
            "entries": []
        }

    # Scan for media files
    all_files = scan_media_files(folder, settings["recursive"])

    # Debug output
    print(f"[DEBUG] Folder: {folder}")
    print(f"[DEBUG] Recursive: {settings['recursive']}")
    print(f"[DEBUG] Sort order: {settings['sort_order']}")
    print(f"[DEBUG] Allowed formats: {len(get_allowed_formats())} types")
    print(f"[DEBUG] Files found: {len(all_files)}")
    if all_files:
        print(f"[DEBUG] First 5 files: {all_files[:5]}")

    # Filter out already swiped files if enabled
    if settings["skip_already_swiped"] and swiped_files:
        media_files = [f for f in all_files if f not in swiped_files]
        skipped = len(all_files) - len(media_files)
    else:
        media_files = all_files
        skipped = 0

    current_index = 0
    stats = {
        "kept": len([e for e in session_log.get("entries", []) if e["action"] == "keep"]),
        "trashed": len([e for e in session_log.get("entries", []) if e["action"] == "trash"]),
        "total": len(all_files),
        "skipped": skipped,
        "remaining": len(media_files)
    }

    save_session_log()

    return jsonify({
        "success": True,
        "total": len(all_files),
        "remaining": len(media_files),
        "skipped": skipped,
        "folder": folder,
        "trash_folder": trash_folder,
        "resumed": existing_log is not None and settings["skip_already_swiped"],
        "stats": stats
    })


@app.route('/api/current')
def get_current():
    """Get current media file info."""
    global current_index, media_files

    if not media_files:
        return jsonify({
            "done": True,
            "stats": stats,
            "message": "Keine Mediendateien gefunden"
        })

    if current_index >= len(media_files):
        return jsonify({
            "done": True,
            "stats": stats,
            "message": f"Fertig! Behalten: {stats['kept']}, Aussortiert: {stats['trashed']}"
        })

    filepath = media_files[current_index]
    filename = Path(filepath).name
    media_type = get_media_type(filepath)

    # Get relative path for display
    try:
        relative_path = str(Path(filepath).relative_to(current_folder))
    except ValueError:
        relative_path = filename

    # Get file size
    try:
        file_size = os.path.getsize(filepath)
        if file_size > 1024 * 1024:
            size_str = f"{file_size / (1024 * 1024):.1f} MB"
        elif file_size > 1024:
            size_str = f"{file_size / 1024:.1f} KB"
        else:
            size_str = f"{file_size} B"
    except:
        size_str = ""

    # Get file date from folder path
    file_date = get_date_from_path(filepath) or ""

    return jsonify({
        "done": False,
        "index": current_index,
        "total": len(media_files),
        "filename": filename,
        "filepath": filepath,
        "relative_path": relative_path,
        "media_type": media_type,
        "file_size": size_str,
        "file_date": file_date,
        "remaining": len(media_files) - current_index,
        "stats": stats
    })


@app.route('/api/media/<path:filepath>')
def serve_media(filepath):
    """Serve media file."""
    full_path = filepath

    if not os.path.exists(full_path):
        return "File not found", 404

    mimetype, _ = mimetypes.guess_type(full_path)
    if mimetype is None:
        mimetype = 'application/octet-stream'

    return send_file(full_path, mimetype=mimetype)


@app.route('/api/action', methods=['POST'])
def perform_action():
    """Perform keep or trash action on current file."""
    global current_index, stats

    data = request.json
    action = data.get('action', '')

    if not media_files or current_index >= len(media_files):
        return jsonify({"error": "Keine Datei zum Verarbeiten"}), 400

    filepath = media_files[current_index]
    filename = Path(filepath).name

    if action == 'trash':
        # Move to trash folder
        try:
            dest = os.path.join(trash_folder, filename)
            # Handle duplicate filenames in trash
            if os.path.exists(dest):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(dest):
                    dest = os.path.join(trash_folder, f"{base}_{counter}{ext}")
                    counter += 1
            shutil.move(filepath, dest)
            stats['trashed'] += 1
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        # Keep - just increment stats
        stats['kept'] += 1

    # Log the action
    add_log_entry(filepath, action, filename)

    current_index += 1
    stats['remaining'] = len(media_files) - current_index

    return jsonify({
        "success": True,
        "action": action,
        "filename": filename,
        "stats": stats,
        "remaining": len(media_files) - current_index
    })


@app.route('/api/undo', methods=['POST'])
def undo_action():
    """Undo the last action (restore from trash if trashed)."""
    global current_index, stats

    if current_index <= 0:
        return jsonify({"error": "Nichts zum Rückgängig machen"}), 400

    current_index -= 1
    filepath = media_files[current_index]
    filename = Path(filepath).name

    # Check if file was trashed (check various possible names)
    restored = False
    for check_name in [filename] + [f"{Path(filename).stem}_{i}{Path(filename).suffix}" for i in range(1, 100)]:
        trash_path = os.path.join(trash_folder, check_name)
        if os.path.exists(trash_path) and not os.path.exists(filepath):
            try:
                shutil.move(trash_path, filepath)
                stats['trashed'] -= 1
                restored = True
                break
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    if not restored:
        stats['kept'] -= 1

    # Remove last log entry
    remove_last_log_entry()

    stats['remaining'] = len(media_files) - current_index

    return jsonify({
        "success": True,
        "filename": filename,
        "stats": stats
    })


@app.route('/api/stats')
def get_stats():
    """Get current statistics."""
    return jsonify(stats)


@app.route('/api/debug', methods=['POST'])
def debug_scan():
    """Debug endpoint to check what files are found."""
    data = request.json
    folder = data.get('folder', '')

    if not folder or not os.path.isdir(folder):
        return jsonify({"error": "Ungültiger Ordnerpfad", "folder": folder}), 400

    # Get allowed formats
    allowed = get_allowed_formats()

    # List all files in folder
    all_items = []
    media_found = []
    folder_path = Path(folder)

    try:
        for item in folder_path.iterdir():
            if item.is_file():
                ext = item.suffix.lower()
                all_items.append({"name": item.name, "ext": ext, "is_media": ext in allowed})
                if ext in allowed:
                    media_found.append(item.name)
            elif item.is_dir():
                all_items.append({"name": item.name + "/", "ext": "DIR", "is_media": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "folder": folder,
        "settings": settings,
        "allowed_formats_count": len(allowed),
        "allowed_formats": list(allowed)[:20],  # First 20
        "total_items": len(all_items),
        "items": all_items[:50],  # First 50
        "media_found": media_found[:20]
    })


@app.route('/api/log')
def get_log():
    """Get session log."""
    return jsonify(session_log)


@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    """Get or update settings."""
    global settings
    if request.method == 'POST':
        data = request.json
        for key in settings:
            if key in data:
                settings[key] = data[key]
        return jsonify({"success": True, "settings": settings})
    return jsonify(settings)

@app.route('/api/set_language', methods=['POST'])
def api_set_language():
    """API: Sets the application language"""
    data = request.json
    language = data.get('language', 'en')
    if language in ['en', 'de']:
        set_language(language)
        return jsonify({'success': True, 'language': language})
    return jsonify({'error': 'Invalid language'}), 400


def open_browser():
    """Open browser after a short delay."""
    time.sleep(1)
    webbrowser.open('http://127.0.0.1:5001')


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  Media Swiper - Tinder-style Media Sorting")
    print("="*60)
    print("\nUnterstützte Formate:")
    print(f"  Bilder: {', '.join(sorted(IMAGE_FORMATS))}")
    print(f"  RAW:    {', '.join(sorted(RAW_FORMATS))}")
    print(f"  Video:  {', '.join(sorted(VIDEO_FORMATS))}")
    print(f"  Audio:  {', '.join(sorted(AUDIO_FORMATS))}")
    print("\nSteuerung:")
    print("  → / D / Swipe Rechts = BEHALTEN")
    print("  ← / A / Swipe Links  = TRASH")
    print("  Ctrl+Z / U           = UNDO")
    print("\nFeatures:")
    print("  - Rekursives Scannen (Jahr/Monat Ordner)")
    print("  - Session-Log (swiper_log.json)")
    print("  - Fortsetzung unterbrochener Sessions")
    print("\nStarte Server auf http://127.0.0.1:5001")
    print("="*60 + "\n")

    # Open browser in background
    threading.Thread(target=open_browser, daemon=True).start()

    # Run Flask app
    app.run(host='127.0.0.1', port=5001, debug=False)
