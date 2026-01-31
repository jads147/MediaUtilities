#!/usr/bin/env python3
"""
Internationalization (i18n) module for MediaUtils
Supports English (en) and German (de)
"""

import json
import os
from pathlib import Path

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "config.json"

# Current language (cached)
_current_language = None

TRANSLATIONS = {
    "en": {
        # ============================================
        # COMMON / SHARED
        # ============================================
        "browse": "Browse",
        "add": "Add",
        "remove": "Remove",
        "load": "Load",
        "settings": "Settings",
        "language": "Language",
        "error": "Error",
        "warning": "Warning",
        "info": "Info",
        "ready": "Ready",
        "cancel": "Cancel",
        "ok": "OK",
        "yes": "Yes",
        "no": "No",
        "close": "Close",
        "open": "Open",
        "save": "Save",
        "delete": "Delete",
        "files": "files",
        "file": "file",
        "folder": "Folder",
        "folders": "Folders",

        # Media types
        "images": "Images",
        "raw": "RAW",
        "videos": "Videos",
        "audio": "Audio",

        # ============================================
        # IMAGE SORTER GUI
        # ============================================
        "title_sorter": "Media Sorter - Automatic Sorting for Images, Videos & Audio",
        "sorter_title_short": "Media Sorter",
        "source_folder": "Source Folder (Media):",
        "target_folder": "Target Folder (Sorted):",
        "select_source_folder": "Select source folder with media",
        "select_target_folder": "Select target folder for sorted media",

        # Mode section
        "mode": "Mode",
        "copy_mode": "Copy (original files remain)",
        "move_mode": "Move (original files are moved)",

        # Sorting section
        "sorting": "Sorting",
        "sort_by_day": "Sort by Days (2023/01-January/01)",
        "sort_by_month": "Sort by Months (2023/01-January)",

        # Options section
        "options": "Options",
        "media_types": "Media Types:",
        "images_formats": "Images (JPG, PNG, TIFF, BMP, GIF, WEBP)",
        "raw_formats": "RAW (CR2, CR3, CRW, NEF, ARW, DNG, RAF, ORF, RW2, PEF, SRW)",
        "video_formats": "Videos (MP4, AVI, MOV, MKV, WMV, FLV, WEBM)",
        "audio_formats": "Audio (MP3, WAV, FLAC, AAC, OGG, M4A, WMA)",
        "custom_extensions": "Only specific extensions (e.g. .crw, .thm):",
        "dry_run": "Dry Run (no files moved)",
        "use_hash_db": "Use hash database (for future sorting)",
        "validate_dates": "Enable date validation",
        "earliest_valid_year": "Earliest valid year:",

        # Duplicate handling
        "duplicate_handling": "Duplicate Handling:",
        "duplicate_off": "off",
        "duplicate_move": "move",
        "duplicate_ignore": "ignore",
        "duplicate_info_off": "All files will be sorted (no duplicate detection)",
        "duplicate_info_move": "Original is sorted, duplicates -> _duplicates/ folder",
        "duplicate_info_ignore": "Original is sorted, duplicates remain in source folder",
        "turbo_mode": "Turbo Mode (faster duplicate detection)",
        "batch_processing": "Batch Processing (1000 files per run for large collections)",

        # Buttons
        "start_sorting": "Start Sorting",
        "stop": "Stop",
        "clear_log": "Clear Log",
        "hash_db_manager": "Hash Database Manager",

        # Status and log
        "log_output": "Log Output",
        "sorting_complete": "Sorting complete!",
        "sorting_stopped": "Sorting stopped",
        "processing": "Processing...",

        # Messages
        "error_no_source": "Please select a source folder!",
        "error_no_target": "Please select a target folder!",
        "error_source_not_exists": "Source folder does not exist!",
        "error_no_media_type": "Please select at least one media type!",
        "warning_no_hash_db": "No hash database found at:\n{path}\n\nDatabase will be created after first sorting.",
        "warning_select_target_first": "Please select a target folder first!",

        # Hash Manager
        "hash_manager_title": "Hash Database Manager",
        "total_entries": "Total entries:",
        "search_placeholder": "Search for filename...",
        "search": "Search",
        "delete_selected": "Delete Selected",
        "delete_all": "Delete All",
        "refresh": "Refresh",
        "confirm_delete": "Really delete {count} entries?",
        "confirm_delete_all": "Really delete ALL {count} entries?\n\nThis action cannot be undone!",
        "entries_deleted": "{count} entries deleted",
        "all_entries_deleted": "All entries deleted",

        # Hash Manager GUI
        "database": "Database",
        "statistics": "Statistics",
        "actions": "Actions",
        "refresh_stats": "Refresh statistics",
        "all_entries": "All entries",
        "check_duplicates": "Check duplicates",
        "cleanup": "Cleanup",
        "csv_export": "CSV Export",
        "delete_selection": "Delete selection",
        "edit_entry": "Edit entry",
        "update_path": "Update path",
        "add_manually": "Add manually",
        "all_entries_title": "All entries",
        "duplicates": "Duplicates",
        "no_duplicates_found": "No duplicates found",
        "db_already_clean": "The database is already clean",
        "no_duplicates_msg": "No duplicates found!\n\nThe database is already clean.",
        "duplicates_found": "{count} duplicates found!",
        "filename": "Filename",
        "path": "Path",
        "size_kb": "Size (KB)",
        "date_taken": "Date taken",
        "date_source": "Date source",
        "search_label": "Search",
        "filename_label": "Filename:",
        "search_btn": "Search",
        "from_date": "From:",
        "to_date": "To:",
        "date_search": "Date search",
        "date_format_hint": "(Format: YYYY-MM-DD)",
        "enter_search_term": "Please enter a search term!",
        "search_results": "Search results",
        "files_found": "{count} files found!\nSearch: {desc}",
        "error_loading_entries": "Error loading entries:\n{error}",
        "error_loading_stats": "Error loading statistics:\n{error}",
        "error_search": "Error searching:\n{error}",
        "error_duplicates": "Error searching for duplicates:\n{error}",
        "total_files": "Total files: {count}",
        "unique_hashes": "Unique hashes: {count}",
        "duplicate_groups": "Duplicate groups: {count}",
        "total_duplicates": "Total duplicates: {count}",
        "all_files_unique": "All files unique (no duplicates)",
        "time_range": "Time range: {range}",
        "confirm_cleanup": "Do you want to remove non-existing files from the database?\n\nThis cannot be undone!",
        "confirmation": "Confirmation",
        "cleanup_result": "{count} non-existing entries removed!",
        "csv_save_title": "Save CSV export",
        "csv_files": "CSV Files",
        "all_files_label": "All Files",
        "export_success": "Database successfully exported:\n{filename}",
        "error_csv_export": "Error exporting CSV:\n{error}",
        "select_entries_delete": "Please select entries to delete!",
        "confirm_delete_entries": "Do you want to delete {count} entries from the database?\n\nThis cannot be undone!",
        "deleted_success": "{count} entries successfully deleted!",
        "error_deleting": "Error deleting:\n{error}",
        "select_entry_edit": "Please select an entry to edit!",
        "select_one_entry": "Please select only one entry to edit!",
        "edit_entry_title": "Edit entry",
        "entry_not_found": "Entry not found in database!",
        "date_taken_label": "Date taken:",
        "date_source_label": "Date source:",
        "media_type_label": "Media type:",
        "hash_label": "Hash:",
        "file_size_label": "File size:",
        "date_added_label": "Added:",
        "date_format_long": "Format: YYYY-MM-DD HH:MM:SS",
        "invalid_date_format": "Invalid date format! Use: YYYY-MM-DD HH:MM:SS",
        "entry_updated": "Entry successfully updated!",
        "error_saving": "Error saving:\n{error}",
        "error_loading_data": "Error loading data:\n{error}",
        "select_entries": "Please select entries!",
        "select_new_base_path": "Select new base path for files",
        "paths_updated": "{count} paths successfully updated!",
        "error_updating_paths": "Error updating paths:\n{error}",
        "add_manual_title": "Add manual entry",
        "browse_file": "Browse",
        "select_file": "Select file",
        "name_and_path_required": "Filename and path are required!",
        "file_not_exists_warning": "The file does not exist at the specified path. Add anyway?",
        "duplicate_hash_warning": "An entry with this hash already exists. Add anyway?",
        "duplicate_label": "Duplicate",
        "entry_added": "Entry successfully added!",
        "error_adding": "Error adding:\n{error}",
        "error_db_connect": "Error connecting to database:\n{error}",
        "error_cleanup": "Error during cleanup:\n{error}",

        # ============================================
        # TIMELINE VIEWER
        # ============================================
        "title_timeline": "Media Timeline Viewer - Horizontal Timeline",
        "timeline_title_short": "Media Timeline Viewer",
        "folders_multiple": "Folders (multiple possible)",
        "size": "Size:",
        "information": "Information",
        "timeline": "Timeline",
        "details": "Details",
        "previous": "Previous",
        "next": "Next",
        "show_images": "Show Images",
        "media_viewer": "Media Viewer",

        # Status messages
        "media_count": "{count} media",
        "select_folder_with_sorted_media": "Select a folder with sorted media",
        "click_for_details": "Click on a period for details",
        "loading_timeline": "Loading timeline data...",
        "timeline_loaded": "Timeline loaded - use size slider or Ctrl+Scroll for size adjustment",
        "selected_period": "Selected: {month} {year} - {count} media",
        "media_in_periods": "{files} media in {periods} periods",
        "select_period_first": "Please select a period first",
        "showing_range": "{start}-{end} of {total}",

        # Errors
        "error_add_folder": "Please add at least one folder",
        "error_invalid_folders": "Invalid folders: {folders}",
        "error_loading": "Error loading: {error}",

        # Context menu
        "open_file": "Open",
        "show_in_folder": "Show in folder",
        "select_folder_title": "Select folder with sorted media",

        # OpenCV warning
        "opencv_not_available": "OpenCV not available - Video thumbnails will be shown as placeholders",

        # ============================================
        # WEB VIEWER (index.html)
        # ============================================
        "title_viewer": "Media Viewer",
        "viewer_title_short": "Media Viewer",
        "paths_placeholder": "Paths to sorted media (one path per line)\ne.g.:\nC:\\Sorted_Media\nD:\\Backup\\Photos",
        "paths_hint": "Multiple paths: one path per line or separated by ;. Ctrl+Enter to load.",
        "load_btn": "Load",
        "show_all_days": "Show all days/months (from first to last available)",
        "auto_scroll_preview": "Auto-Scroll Preview",

        # Stats
        "total_media": "Total Media",
        "years": "Years",
        "months": "Months",
        "unknown_dates": "Unknown Dates",

        # Content
        "select_folder_to_browse": "Select a folder to browse your images...",
        "loading_media": "Loading media...",
        "back": "Back",
        "unrealistic_dates": "Unrealistic Dates",
        "unknown_dates_section": "Unknown Dates",
        "files_count": "{count} files",
        "files_in_days": "{files} files in {days} days",

        # Errors
        "error_enter_path": "Please enter at least one folder path",
        "error_valid_path": "Please enter at least one valid folder path",
        "error_setting_directories": "Error setting directories",

        # Navigation
        "navigate_hint": "({start}-{end} of {total} files, use arrow keys to navigate)",

        # ============================================
        # MEDIA SWIPER (swiper.html)
        # ============================================
        "title_swiper": "MEDIA SWIPER",
        "folder_placeholder": "Enter folder path (e.g. C:\\Users\\Pictures)",
        "start": "Start",
        "debug": "Debug",

        # Settings
        "settings_expand": "Expand",
        "settings_collapse": "Collapse",
        "media_types_label": "Media Types",
        "sort_order": "Sort Order",
        "oldest_first": "Oldest First",
        "newest_first": "Newest First",
        "by_name": "By Name",
        "random": "Random",
        "options_label": "Options",
        "include_subfolders": "Include subfolders",
        "skip_already_sorted": "Skip already sorted",

        # Stats
        "kept": "Kept",
        "trashed": "Trashed",
        "remaining": "Remaining",
        "already_sorted": "Already Sorted",

        # Session
        "session_resumed": "Session resumed: {skipped} already sorted, {remaining} new to process",

        # Card indicators
        "keep_indicator": "KEEP",
        "trash_indicator": "TRASH",

        # Done screen
        "done": "Done!",
        "new_folder": "New Folder",

        # Loading
        "loading": "Loading...",
        "select_folder_to_start": "Select a folder to start",

        # Keyboard hints
        "key_trash": "Trash",
        "key_undo": "Undo",
        "key_keep": "Keep",

        # Log
        "session_log": "Session Log",

        # Errors/Alerts
        "error_enter_folder": "Please enter folder path",
        "error_no_media": "No media files found in folder",
        "all_files_sorted": "All {total} files have already been sorted.\n\nDisable \"Skip already sorted\" in settings to sort again.",
        "connection_error": "Connection error: {error}",

        # Debug
        "debug_info": "DEBUG INFO",
        "debug_folder": "Folder: {folder}",
        "debug_formats": "Allowed formats: {count}",
        "debug_recursive": "Recursive: {value}",
        "debug_items_found": "Items found: {count}",
        "debug_first_entries": "First entries:",
        "debug_media_found": "Media found: {count}",
        "debug_no_media": "NO MEDIA FOUND!",
        "debug_check_extensions": "Check if files with these extensions exist:",
        "debug_error": "ERROR: {error}",

        # ============================================
        # RAW TO PNG CONVERTER
        # ============================================
        "title_raw_converter": "RAW to PNG Converter",
        "raw_converter_title_short": "RAW Converter",

        # Folder selection
        "source_folder_raw": "Source Folder (RAW Files):",
        "output_folder_raw": "Output Folder (PNG):",
        "select_source_folder_raw": "Select folder containing RAW files",
        "select_output_folder_raw": "Select output folder for PNG files",
        "same_as_source": "Same as source folder",
        "output_mode_label": "Output Location",
        "output_in_place": "Save PNG next to RAW file (in-place)",
        "output_custom": "Save to separate output folder",

        # Conversion settings
        "conversion_settings": "Conversion Settings",
        "png_compression": "PNG Compression (0-9):",
        "compression_hint": "0 = no compression, 9 = max compression",
        "bit_depth_label": "Bit Depth:",
        "bit_depth_8": "8-bit (standard)",
        "bit_depth_16": "16-bit (high quality)",
        "color_profile_label": "Color Profile:",
        "color_srgb": "sRGB (standard)",
        "color_adobe_rgb": "Adobe RGB",
        "color_preserve": "Camera profile",

        # Resize options
        "resize_options": "Resize Options",
        "resize_none": "No resize (original dimensions)",
        "resize_max_dim": "Maximum dimensions",
        "resize_percentage": "Percentage",
        "max_width_label": "Max Width:",
        "max_height_label": "Max Height:",
        "percentage_label": "Scale:",

        # Options
        "options_raw": "Options",
        "recursive_scan": "Scan subfolders recursively",
        "move_originals": "Move originals to _converted subfolder",

        # Buttons
        "start_conversion": "Start Conversion",
        "stop_conversion": "Stop",
        "clear_log": "Clear Log",

        # Status
        "status_ready": "Ready",
        "status_scanning": "Scanning for RAW files...",
        "status_converting": "Converting...",
        "status_moving": "Moving originals...",
        "status_complete": "Complete",
        "status_stopped": "Stopped",
        "conversion_stopped": "Conversion stopped by user.",
        "converting_file": "Converting: {filename}",
        "moving_file": "Moving: {filename}",
        "files_progress": "{current} / {total} files",

        # Results
        "conversion_summary": "Conversion Complete",
        "conversion_success_msg": "Converted: {converted}\nFailed: {failed}\nSkipped: {skipped}",
        "no_raw_files_found": "No RAW files found in the selected folder.",
        "originals_moved": "{count} original(s) moved to _converted",
        "file_converted": "Converted: {src} -> {dst}",
        "file_skipped": "Skipped (already exists): {filename}",

        # Errors
        "error_no_source_raw": "Please select a source folder.",
        "error_no_output_raw": "Please select an output folder.",
        "error_source_not_exists_raw": "Source folder does not exist.",
        "error_rawpy_not_installed": "rawpy is not installed.\nInstall with: pip install rawpy",
        "error_conversion_failed": "Failed: {filename} - {error}",
        "error_permission": "Permission denied: {path}",
        "error_move_failed": "Failed to move: {filename} - {error}",

        # Supported formats
        "supported_raw_formats": "Supported: CR2, CR3, NEF, ARW, DNG, ORF, RW2, PEF, SRW, RAF, and more",
    },

    "de": {
        # ============================================
        # COMMON / SHARED
        # ============================================
        "browse": "Durchsuchen",
        "add": "Hinzufügen",
        "remove": "Entfernen",
        "load": "Laden",
        "settings": "Einstellungen",
        "language": "Sprache",
        "error": "Fehler",
        "warning": "Achtung",
        "info": "Info",
        "ready": "Bereit",
        "cancel": "Abbrechen",
        "ok": "OK",
        "yes": "Ja",
        "no": "Nein",
        "close": "Schließen",
        "open": "Öffnen",
        "save": "Speichern",
        "delete": "Löschen",
        "files": "Dateien",
        "file": "Datei",
        "folder": "Ordner",
        "folders": "Ordner",

        # Media types
        "images": "Bilder",
        "raw": "RAW",
        "videos": "Videos",
        "audio": "Audio",

        # ============================================
        # IMAGE SORTER GUI
        # ============================================
        "title_sorter": "Medien Sorter - Automatische Sortierung für Bilder, Videos & Audio",
        "sorter_title_short": "Medien Sorter",
        "source_folder": "Quellordner (Medien):",
        "target_folder": "Zielordner (Sortiert):",
        "select_source_folder": "Quellordner mit Medien auswählen",
        "select_target_folder": "Zielordner für sortierte Medien auswählen",

        # Mode section
        "mode": "Modus",
        "copy_mode": "Kopieren (Originaldateien bleiben erhalten)",
        "move_mode": "Verschieben (Originaldateien werden verschoben)",

        # Sorting section
        "sorting": "Sortierung",
        "sort_by_day": "Nach Tagen sortieren (2023/01-January/01)",
        "sort_by_month": "Nach Monaten sortieren (2023/01-January)",

        # Options section
        "options": "Optionen",
        "media_types": "Medientypen:",
        "images_formats": "Bilder (JPG, PNG, TIFF, BMP, GIF, WEBP)",
        "raw_formats": "RAW (CR2, CR3, CRW, NEF, ARW, DNG, RAF, ORF, RW2, PEF, SRW)",
        "video_formats": "Videos (MP4, AVI, MOV, MKV, WMV, FLV, WEBM)",
        "audio_formats": "Audio (MP3, WAV, FLAC, AAC, OGG, M4A, WMA)",
        "custom_extensions": "Nur bestimmte Endungen (z.B. .crw, .thm):",
        "dry_run": "Testlauf (keine Dateien verschieben)",
        "use_hash_db": "Hash-Datenbank verwenden (für zukünftige Sortierungen)",
        "validate_dates": "Datumsvalidierung aktivieren",
        "earliest_valid_year": "Frühstes gültiges Jahr:",

        # Duplicate handling
        "duplicate_handling": "Duplikat-Behandlung:",
        "duplicate_off": "aus",
        "duplicate_move": "verschieben",
        "duplicate_ignore": "ignorieren",
        "duplicate_info_off": "Alle Dateien werden sortiert (keine Duplikat-Erkennung)",
        "duplicate_info_move": "Original wird sortiert, Duplikate → _duplicates/ Ordner",
        "duplicate_info_ignore": "Original wird sortiert, Duplikate bleiben unberührt im Quellordner",
        "turbo_mode": "Turbo-Modus (schnellere Duplikaterkennung)",
        "batch_processing": "Batch-Verarbeitung (1000 Dateien pro Durchgang für große Sammlungen)",

        # Buttons
        "start_sorting": "Sortierung starten",
        "stop": "Stoppen",
        "clear_log": "Log löschen",
        "hash_db_manager": "Hash-Datenbank verwalten",

        # Status and log
        "log_output": "Log-Ausgabe",
        "sorting_complete": "Sortierung abgeschlossen!",
        "sorting_stopped": "Sortierung gestoppt",
        "processing": "Verarbeitung...",

        # Messages
        "error_no_source": "Bitte Quellordner auswählen!",
        "error_no_target": "Bitte Zielordner auswählen!",
        "error_source_not_exists": "Quellordner existiert nicht!",
        "error_no_media_type": "Bitte mindestens einen Medientyp auswählen!",
        "warning_no_hash_db": "Keine Hash-Datenbank gefunden in:\n{path}\n\nDatenbank wird nach der ersten Sortierung erstellt.",
        "warning_select_target_first": "Bitte erst einen Zielordner auswählen!",

        # Hash Manager
        "hash_manager_title": "Hash-Datenbank Manager",
        "total_entries": "Einträge gesamt:",
        "search_placeholder": "Nach Dateiname suchen...",
        "search": "Suchen",
        "delete_selected": "Ausgewählte löschen",
        "delete_all": "Alle löschen",
        "refresh": "Aktualisieren",
        "confirm_delete": "Wirklich {count} Einträge löschen?",
        "confirm_delete_all": "Wirklich ALLE {count} Einträge löschen?\n\nDiese Aktion kann nicht rückgängig gemacht werden!",
        "entries_deleted": "{count} Einträge gelöscht",
        "all_entries_deleted": "Alle Einträge gelöscht",

        # Hash Manager GUI
        "database": "Datenbank",
        "statistics": "Statistiken",
        "actions": "Aktionen",
        "refresh_stats": "Statistiken aktualisieren",
        "all_entries": "Alle Einträge",
        "check_duplicates": "Duplikate prüfen",
        "cleanup": "Aufräumen",
        "csv_export": "CSV Export",
        "delete_selection": "Auswahl löschen",
        "edit_entry": "Eintrag bearbeiten",
        "update_path": "Pfad aktualisieren",
        "add_manually": "Manuell hinzufügen",
        "all_entries_title": "Alle Einträge",
        "duplicates": "Duplikate",
        "no_duplicates_found": "Keine Duplikate gefunden",
        "db_already_clean": "Die Datenbank ist bereits bereinigt",
        "no_duplicates_msg": "Keine Duplikate gefunden!\n\nDie Datenbank ist bereits bereinigt.",
        "duplicates_found": "{count} Duplikate gefunden!",
        "filename": "Dateiname",
        "path": "Pfad",
        "size_kb": "Größe (KB)",
        "date_taken": "Aufnahmedatum",
        "date_source": "Datumsquelle",
        "search_label": "Suche",
        "filename_label": "Dateiname:",
        "search_btn": "Suchen",
        "from_date": "Von:",
        "to_date": "Bis:",
        "date_search": "Datumssuche",
        "date_format_hint": "(Format: YYYY-MM-DD)",
        "enter_search_term": "Bitte Suchbegriff eingeben!",
        "search_results": "Suchergebnisse",
        "files_found": "{count} Dateien gefunden!\nSuche: {desc}",
        "error_loading_entries": "Fehler beim Laden der Einträge:\n{error}",
        "error_loading_stats": "Fehler beim Laden der Statistiken:\n{error}",
        "error_search": "Fehler bei der Suche:\n{error}",
        "error_duplicates": "Fehler beim Suchen von Duplikaten:\n{error}",
        "total_files": "Gesamt Dateien: {count}",
        "unique_hashes": "Eindeutige Hashes: {count}",
        "duplicate_groups": "Duplikat-Gruppen: {count}",
        "total_duplicates": "Gesamt Duplikate: {count}",
        "all_files_unique": "Alle Dateien eindeutig (keine Duplikate)",
        "time_range": "Zeitraum: {range}",
        "confirm_cleanup": "Möchten Sie nicht existierende Dateien aus der Datenbank entfernen?\n\nDies kann nicht rückgängig gemacht werden!",
        "confirmation": "Bestätigung",
        "cleanup_result": "{count} nicht existierende Einträge entfernt!",
        "csv_save_title": "CSV Export speichern",
        "csv_files": "CSV Dateien",
        "all_files_label": "Alle Dateien",
        "export_success": "Datenbank erfolgreich exportiert:\n{filename}",
        "error_csv_export": "Fehler beim CSV-Export:\n{error}",
        "select_entries_delete": "Bitte wählen Sie Einträge zum Löschen aus!",
        "confirm_delete_entries": "Möchten Sie {count} Einträge aus der Datenbank löschen?\n\nDies kann nicht rückgängig gemacht werden!",
        "deleted_success": "{count} Einträge erfolgreich gelöscht!",
        "error_deleting": "Fehler beim Löschen:\n{error}",
        "select_entry_edit": "Bitte wählen Sie einen Eintrag zum Bearbeiten aus!",
        "select_one_entry": "Bitte wählen Sie nur einen Eintrag zum Bearbeiten aus!",
        "edit_entry_title": "Eintrag bearbeiten",
        "entry_not_found": "Eintrag nicht in Datenbank gefunden!",
        "date_taken_label": "Aufnahmedatum:",
        "date_source_label": "Datumsquelle:",
        "media_type_label": "Medientyp:",
        "hash_label": "Hash:",
        "file_size_label": "Dateigröße:",
        "date_added_label": "Hinzugefügt:",
        "date_format_long": "Format: YYYY-MM-DD HH:MM:SS",
        "invalid_date_format": "Ungültiges Datumsformat! Verwenden Sie: YYYY-MM-DD HH:MM:SS",
        "entry_updated": "Eintrag erfolgreich aktualisiert!",
        "error_saving": "Fehler beim Speichern:\n{error}",
        "error_loading_data": "Fehler beim Laden der Daten:\n{error}",
        "select_entries": "Bitte wählen Sie Einträge aus!",
        "select_new_base_path": "Neuen Basispfad für Dateien auswählen",
        "paths_updated": "{count} Pfade erfolgreich aktualisiert!",
        "error_updating_paths": "Fehler beim Aktualisieren der Pfade:\n{error}",
        "add_manual_title": "Manuellen Eintrag hinzufügen",
        "browse_file": "Durchsuchen",
        "select_file": "Datei auswählen",
        "name_and_path_required": "Dateiname und Pfad sind erforderlich!",
        "file_not_exists_warning": "Die Datei existiert nicht am angegebenen Pfad. Trotzdem hinzufügen?",
        "duplicate_hash_warning": "Ein Eintrag mit diesem Hash existiert bereits. Trotzdem hinzufügen?",
        "duplicate_label": "Duplikat",
        "entry_added": "Eintrag erfolgreich hinzugefügt!",
        "error_adding": "Fehler beim Hinzufügen:\n{error}",
        "error_db_connect": "Fehler beim Verbinden zur Datenbank:\n{error}",
        "error_cleanup": "Fehler beim Aufräumen:\n{error}",

        # ============================================
        # TIMELINE VIEWER
        # ============================================
        "title_timeline": "Medien Timeline Viewer - Horizontaler Zeitstrahl",
        "timeline_title_short": "Medien Timeline Viewer",
        "folders_multiple": "Ordner (mehrere möglich)",
        "size": "Größe:",
        "information": "Information",
        "timeline": "Timeline",
        "details": "Details",
        "previous": "Vorherige",
        "next": "Nächste",
        "show_images": "Bilder anzeigen",
        "media_viewer": "Medien Viewer",

        # Status messages
        "media_count": "{count} Medien",
        "select_folder_with_sorted_media": "Wähle einen Ordner mit sortierten Medien aus",
        "click_for_details": "Klicke auf einen Zeitraum für Details",
        "loading_timeline": "Lade Timeline-Daten...",
        "timeline_loaded": "Timeline geladen - verwende Größen-Schieber oder Ctrl+Mausrad für Größenanpassung",
        "selected_period": "Ausgewählt: {month} {year} - {count} Medien",
        "media_in_periods": "{files} Medien in {periods} Zeiträumen",
        "select_period_first": "Bitte wähle zuerst einen Zeitraum aus",
        "showing_range": "{start}-{end} von {total}",

        # Errors
        "error_add_folder": "Bitte füge mindestens einen Ordner hinzu",
        "error_invalid_folders": "Ungültige Ordner: {folders}",
        "error_loading": "Fehler beim Laden: {error}",

        # Context menu
        "open_file": "Öffnen",
        "show_in_folder": "Im Ordner anzeigen",
        "select_folder_title": "Ordner mit sortierten Medien auswählen",

        # OpenCV warning
        "opencv_not_available": "OpenCV nicht verfügbar - Video-Thumbnails werden als Platzhalter angezeigt",

        # ============================================
        # WEB VIEWER (index.html)
        # ============================================
        "title_viewer": "Medien Viewer",
        "viewer_title_short": "Medien Viewer",
        "paths_placeholder": "Pfade zu sortierten Medien (ein Pfad pro Zeile)\nz.B.:\nC:\\Sortierte_Medien\nD:\\Backup\\Fotos",
        "paths_hint": "Mehrere Pfade: ein Pfad pro Zeile oder mit ; getrennt. Ctrl+Enter zum Laden.",
        "load_btn": "Laden",
        "show_all_days": "Alle Tage/Monate anzeigen (vom ersten bis zum letzten verfügbaren)",
        "auto_scroll_preview": "Auto-Scroll Preview",

        # Stats
        "total_media": "Medien insgesamt",
        "years": "Jahre",
        "months": "Monate",
        "unknown_dates": "Unbekannte Daten",

        # Content
        "select_folder_to_browse": "Wähle einen Ordner aus, um deine Bilder zu durchsuchen...",
        "loading_media": "Lade Medien...",
        "back": "Zurück",
        "unrealistic_dates": "Unrealistische Daten",
        "unknown_dates_section": "Unbekannte Daten",
        "files_count": "{count} Dateien",
        "files_in_days": "{files} Dateien in {days} Tagen",

        # Errors
        "error_enter_path": "Bitte gib mindestens einen Ordnerpfad ein",
        "error_valid_path": "Bitte gib mindestens einen gültigen Ordnerpfad ein",
        "error_setting_directories": "Fehler beim Setzen der Verzeichnisse",

        # Navigation
        "navigate_hint": "({start}-{end} von {total} Dateien, ← → zum Navigieren)",

        # ============================================
        # MEDIA SWIPER (swiper.html)
        # ============================================
        "title_swiper": "MEDIA SWIPER",
        "folder_placeholder": "Ordnerpfad eingeben (z.B. C:\\Users\\Pictures)",
        "start": "Start",
        "debug": "Debug",

        # Settings
        "settings_expand": "Erweitern",
        "settings_collapse": "Einklappen",
        "media_types_label": "Medientypen",
        "sort_order": "Sortierung",
        "oldest_first": "Älteste zuerst",
        "newest_first": "Neueste zuerst",
        "by_name": "Nach Name",
        "random": "Zufällig",
        "options_label": "Optionen",
        "include_subfolders": "Unterordner einschließen",
        "skip_already_sorted": "Bereits sortierte überspringen",

        # Stats
        "kept": "Behalten",
        "trashed": "Aussortiert",
        "remaining": "Verbleibend",
        "already_sorted": "Bereits sortiert",

        # Session
        "session_resumed": "Session fortgesetzt: {skipped} bereits sortiert, {remaining} neu zu bearbeiten",

        # Card indicators
        "keep_indicator": "BEHALTEN",
        "trash_indicator": "TRASH",

        # Done screen
        "done": "Fertig!",
        "new_folder": "Neuer Ordner",

        # Loading
        "loading": "Laden...",
        "select_folder_to_start": "Wähle einen Ordner zum Starten",

        # Keyboard hints
        "key_trash": "Trash",
        "key_undo": "Undo",
        "key_keep": "Keep",

        # Log
        "session_log": "Session Log",

        # Errors/Alerts
        "error_enter_folder": "Bitte Ordnerpfad eingeben",
        "error_no_media": "Keine Mediendateien im Ordner gefunden",
        "all_files_sorted": "Alle {total} Dateien wurden bereits sortiert.\n\nDeaktiviere \"Bereits geswiped überspringen\" in den Einstellungen um erneut zu sortieren.",
        "connection_error": "Verbindungsfehler: {error}",

        # Debug
        "debug_info": "DEBUG INFO",
        "debug_folder": "Ordner: {folder}",
        "debug_formats": "Erlaubte Formate: {count}",
        "debug_recursive": "Rekursiv: {value}",
        "debug_items_found": "Gefundene Items: {count}",
        "debug_first_entries": "Erste Einträge:",
        "debug_media_found": "Medien gefunden: {count}",
        "debug_no_media": "KEINE MEDIEN GEFUNDEN!",
        "debug_check_extensions": "Prüfe ob Dateien mit diesen Endungen existieren:",
        "debug_error": "FEHLER: {error}",

        # ============================================
        # RAW TO PNG CONVERTER
        # ============================================
        "title_raw_converter": "RAW zu PNG Konverter",
        "raw_converter_title_short": "RAW Konverter",

        # Ordnerauswahl
        "source_folder_raw": "Quellordner (RAW-Dateien):",
        "output_folder_raw": "Ausgabeordner (PNG):",
        "select_source_folder_raw": "Ordner mit RAW-Dateien auswählen",
        "select_output_folder_raw": "Ausgabeordner für PNG-Dateien auswählen",
        "same_as_source": "Gleicher Ordner wie Quelle",
        "output_mode_label": "Ausgabeort",
        "output_in_place": "PNG neben RAW-Datei speichern (In-Place)",
        "output_custom": "In separaten Ausgabeordner speichern",

        # Konvertierungseinstellungen
        "conversion_settings": "Konvertierungseinstellungen",
        "png_compression": "PNG Kompression (0-9):",
        "compression_hint": "0 = keine Kompression, 9 = max. Kompression",
        "bit_depth_label": "Bit-Tiefe:",
        "bit_depth_8": "8-Bit (Standard)",
        "bit_depth_16": "16-Bit (hohe Qualität)",
        "color_profile_label": "Farbprofil:",
        "color_srgb": "sRGB (Standard)",
        "color_adobe_rgb": "Adobe RGB",
        "color_preserve": "Kameraprofil",

        # Größenänderung
        "resize_options": "Größenänderung",
        "resize_none": "Keine Änderung (Originalgröße)",
        "resize_max_dim": "Maximale Abmessungen",
        "resize_percentage": "Prozent",
        "max_width_label": "Max. Breite:",
        "max_height_label": "Max. Höhe:",
        "percentage_label": "Skalierung:",

        # Optionen
        "options_raw": "Optionen",
        "recursive_scan": "Unterordner rekursiv scannen",
        "move_originals": "Originale nach _converted verschieben",

        # Buttons
        "start_conversion": "Konvertierung starten",
        "stop_conversion": "Stopp",
        "clear_log": "Log löschen",

        # Status
        "status_ready": "Bereit",
        "status_scanning": "Suche RAW-Dateien...",
        "status_converting": "Konvertiere...",
        "status_moving": "Verschiebe Originale...",
        "status_complete": "Abgeschlossen",
        "status_stopped": "Gestoppt",
        "conversion_stopped": "Konvertierung vom Benutzer gestoppt.",
        "converting_file": "Konvertiere: {filename}",
        "moving_file": "Verschiebe: {filename}",
        "files_progress": "{current} / {total} Dateien",

        # Ergebnisse
        "conversion_summary": "Konvertierung abgeschlossen",
        "conversion_success_msg": "Konvertiert: {converted}\nFehlgeschlagen: {failed}\nÜbersprungen: {skipped}",
        "no_raw_files_found": "Keine RAW-Dateien im ausgewählten Ordner gefunden.",
        "originals_moved": "{count} Original(e) nach _converted verschoben",
        "file_converted": "Konvertiert: {src} -> {dst}",
        "file_skipped": "Übersprungen (existiert bereits): {filename}",

        # Fehler
        "error_no_source_raw": "Bitte Quellordner auswählen.",
        "error_no_output_raw": "Bitte Ausgabeordner auswählen.",
        "error_source_not_exists_raw": "Quellordner existiert nicht.",
        "error_rawpy_not_installed": "rawpy ist nicht installiert.\nInstallieren mit: pip install rawpy",
        "error_conversion_failed": "Fehlgeschlagen: {filename} - {error}",
        "error_permission": "Zugriff verweigert: {path}",
        "error_move_failed": "Verschieben fehlgeschlagen: {filename} - {error}",

        # Unterstützte Formate
        "supported_raw_formats": "Unterstützt: CR2, CR3, NEF, ARW, DNG, ORF, RW2, PEF, SRW, RAF und mehr",
    }
}


def get_language() -> str:
    """Get the current language from config.json"""
    global _current_language

    if _current_language is not None:
        return _current_language

    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
                _current_language = config.get('language', 'en')
        else:
            _current_language = 'en'
    except Exception:
        _current_language = 'en'

    return _current_language


def set_language(lang: str) -> bool:
    """Set the language and save to config.json"""
    global _current_language

    if lang not in TRANSLATIONS:
        return False

    try:
        # Read existing config or create new
        config = {}
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)

        config['language'] = lang

        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        _current_language = lang
        return True
    except Exception as e:
        print(f"Error saving language setting: {e}")
        return False


def t(key: str, **kwargs) -> str:
    """
    Get translation for a key.
    Supports format strings with {placeholder} syntax.

    Example:
        t("files_count", count=5)  -> "5 files" or "5 Dateien"
    """
    lang = get_language()
    translations = TRANSLATIONS.get(lang, TRANSLATIONS['en'])

    # Try to get translation, fall back to English, then to key itself
    text = translations.get(key)
    if text is None:
        text = TRANSLATIONS['en'].get(key, key)

    # Apply format arguments if provided
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass  # If format fails, return unformatted text

    return text


def get_all_translations() -> dict:
    """Get all translations for the current language (useful for JavaScript)"""
    lang = get_language()
    return TRANSLATIONS.get(lang, TRANSLATIONS['en'])


def get_available_languages() -> list:
    """Get list of available languages"""
    return [
        {"code": "en", "name": "English"},
        {"code": "de", "name": "Deutsch"}
    ]


# For convenience, expose commonly used functions at module level
def reload_language():
    """Force reload of language setting from config file"""
    global _current_language
    _current_language = None
    return get_language()
