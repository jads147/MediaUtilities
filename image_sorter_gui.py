#!/usr/bin/env python3
"""
Bilder Sorter GUI - Grafische Benutzeroberfläche für den Bilder-Sortierer
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import shutil
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Set, List, Tuple
import logging
from PIL import Image
from PIL.ExifTags import TAGS
import exifread
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
import tkinter.font as tkFont

class ImageSorterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Medien Sorter - Automatische Sortierung für Bilder, Videos & Audio")
        self.root.geometry("1050x880")  # Optimiert für das neue Layout
        self.root.minsize(1000, 820)  # Mindestgröße für gute Lesbarkeit
        self.root.configure(bg='#f0f0f0')
        
        # Fenster zentrieren
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - self.root.winfo_width()) // 2
        y = (self.root.winfo_screenheight() - self.root.winfo_height()) // 2
        self.root.geometry(f"+{x}+{y}")
        
        # Variablen
        self.source_dir = tk.StringVar()
        self.target_dir = tk.StringVar()
        self.copy_mode = tk.BooleanVar(value=True)  # False = Verschieben, True = Kopieren
        self.sort_by_day = tk.BooleanVar(value=True)  # False = Monat, True = Tag
        self.dry_run = tk.BooleanVar(value=True)
        
        # Datumsvalidierung - frühstes gültiges Jahr
        self.earliest_valid_year = tk.IntVar(value=2004)
        
        # Sortierer-Instanz
        self.sorter = None
        self.is_running = False
        
        self.setup_gui()
        self.setup_logging()
        
    def setup_gui(self):
        """Erstellt die GUI-Elemente"""
        # Hauptframe
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Titel
        title_label = ttk.Label(main_frame, text="🎭 Medien Sorter", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Quellordner
        ttk.Label(main_frame, text="Quellordner (Medien):").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.source_dir, width=65).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(main_frame, text="Durchsuchen", 
                  command=self.browse_source).grid(row=1, column=2, pady=5)
        
        # Zielordner
        ttk.Label(main_frame, text="Zielordner (Sortiert):").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.target_dir, width=65).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(main_frame, text="Durchsuchen", 
                  command=self.browse_target).grid(row=2, column=2, pady=5)
        
        # Modus und Sortierung nebeneinander
        mode_sort_frame = ttk.Frame(main_frame)
        mode_sort_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # Modus-Sektion (links)
        mode_frame = ttk.LabelFrame(mode_sort_frame, text="Modus", padding="10")
        mode_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), padx=(0, 5))
        
        # Radio buttons für Modus
        ttk.Radiobutton(mode_frame, text="📋 Kopieren (Originaldateien bleiben erhalten)", 
                       variable=self.copy_mode, value=True).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Radiobutton(mode_frame, text="📁 Verschieben (Originaldateien werden verschoben)", 
                       variable=self.copy_mode, value=False).grid(row=1, column=0, sticky=tk.W, pady=2)
        
        # Sortier-Optionen (rechts)
        sort_frame = ttk.LabelFrame(mode_sort_frame, text="Sortierung", padding="10")
        sort_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N), padx=(5, 0))
        
        # Radio buttons für Sortierung
        ttk.Radiobutton(sort_frame, text="📆 Nach Tagen sortieren (2023/01-January/01)", 
                       variable=self.sort_by_day, value=True).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Radiobutton(sort_frame, text="📅 Nach Monaten sortieren (2023/01-January)", 
                       variable=self.sort_by_day, value=False).grid(row=1, column=0, sticky=tk.W, pady=2)
        
        # Grid-Konfiguration für gleichmäßige Verteilung
        mode_sort_frame.columnconfigure(0, weight=1)
        mode_sort_frame.columnconfigure(1, weight=1)
        
        # Optionen (mit Medientypen integriert)
        options_frame = ttk.LabelFrame(main_frame, text="Optionen", padding="10")
        options_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # Medientyp-Auswahl in Optionen integriert
        ttk.Label(options_frame, text="Medientypen:", font=('Arial', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        self.process_images = tk.BooleanVar(value=True)
        self.process_raw = tk.BooleanVar(value=False)
        self.process_videos = tk.BooleanVar(value=False)
        self.process_audio = tk.BooleanVar(value=False)

        ttk.Checkbutton(options_frame, text="Bilder (JPG, PNG, TIFF, BMP, GIF, WEBP)",
                       variable=self.process_images).grid(row=1, column=0, sticky=tk.W, pady=2, padx=(20, 0))
        ttk.Checkbutton(options_frame, text="RAW (CR2, CR3, CRW, NEF, ARW, DNG, RAF, ORF, RW2, PEF, SRW)",
                       variable=self.process_raw).grid(row=2, column=0, sticky=tk.W, pady=2, padx=(20, 0))
        ttk.Checkbutton(options_frame, text="Videos (MP4, AVI, MOV, MKV, WMV, FLV, WEBM)",
                       variable=self.process_videos).grid(row=3, column=0, sticky=tk.W, pady=2, padx=(20, 0))
        ttk.Checkbutton(options_frame, text="Audio (MP3, WAV, FLAC, AAC, OGG, M4A, WMA)",
                       variable=self.process_audio).grid(row=4, column=0, sticky=tk.W, pady=2, padx=(20, 0))

        # Nur bestimmte Endungen (Debug/Nachholen)
        self.custom_extensions = tk.StringVar(value="")
        ttk.Label(options_frame, text="Nur bestimmte Endungen (z.B. .crw, .thm):").grid(
            row=5, column=0, sticky=tk.W, pady=2, padx=(20, 0))
        ttk.Entry(options_frame, textvariable=self.custom_extensions, width=40).grid(
            row=6, column=0, sticky=tk.W, pady=2, padx=(20, 0))

        # Trennlinie zwischen Medientypen und anderen Optionen
        separator = ttk.Separator(options_frame, orient='horizontal')
        separator.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)

        ttk.Checkbutton(options_frame, text="Testlauf (keine Dateien verschieben)",
                       variable=self.dry_run).grid(row=8, column=0, sticky=tk.W)
        
        # Hash-Datenbank Option
        self.use_hash_db = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Hash-Datenbank verwenden (für zukünftige Sortierungen)",
                       variable=self.use_hash_db).grid(row=9, column=0, columnspan=2, sticky=tk.W)

        # Datumsvalidierung Option
        self.validate_dates = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Datumsvalidierung aktivieren",
                       variable=self.validate_dates).grid(row=10, column=0, sticky=tk.W)

        # Frühjahr-Jahr Einstellung
        ttk.Label(options_frame, text="Frühstes gültiges Jahr:").grid(row=10, column=1, sticky=tk.W, padx=(20, 5))
        year_spinbox = tk.Spinbox(options_frame, from_=1990, to=2030, width=8,
                                 textvariable=self.earliest_valid_year,
                                 state="normal" if self.validate_dates.get() else "disabled")
        year_spinbox.grid(row=10, column=1, sticky=tk.W, padx=(150, 0))

        # Callback für Aktivierung/Deaktivierung des Spinbox
        def toggle_year_spinbox():
            year_spinbox.config(state="normal" if self.validate_dates.get() else "disabled")

        self.validate_dates.trace_add('write', lambda *args: toggle_year_spinbox())

        # Zweite Trennlinie zwischen allgemeinen Optionen und Duplikat-Optionen
        separator2 = ttk.Separator(options_frame, orient='horizontal')
        separator2.grid(row=11, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)

        # Duplikat-Behandlung Option
        ttk.Label(options_frame, text="Duplikat-Behandlung:").grid(row=12, column=0, sticky=tk.W, pady=5)
        self.duplicate_mode = tk.StringVar(value="verschieben")
        duplicate_combo = ttk.Combobox(options_frame, textvariable=self.duplicate_mode,
                                     values=["aus", "verschieben", "ignorieren"],
                                     state="readonly", width=20)
        duplicate_combo.grid(row=12, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # Turbo-Modus für Duplikaterkennung
        self.turbo_duplicate_detection = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="🚀 Turbo-Modus (schnellere Duplikaterkennung)",
                       variable=self.turbo_duplicate_detection).grid(row=13, column=0, columnspan=2, sticky=tk.W)

        # Tooltip-Label für Duplikat-Modi
        duplicate_info = tk.Label(options_frame, text="", fg="gray", font=("Arial", 8), wraplength=400)
        duplicate_info.grid(row=14, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))

        def update_duplicate_info(*args):
            mode = self.duplicate_mode.get()
            if mode == "aus":
                duplicate_info.config(text="Alle Dateien werden sortiert (keine Duplikat-Erkennung)")
            elif mode == "verschieben":
                duplicate_info.config(text="Original wird sortiert, Duplikate → _duplicates/ Ordner")
            elif mode == "ignorieren":
                duplicate_info.config(text="Original wird sortiert, Duplikate bleiben unberührt im Quellordner")

        self.duplicate_mode.trace_add('write', update_duplicate_info)
        update_duplicate_info()  # Initial anzeigen

        # Batch-Verarbeitung Option
        self.batch_processing = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Batch-Verarbeitung (1000 Dateien pro Durchgang für große Sammlungen)",
                       variable=self.batch_processing).grid(row=15, column=0, columnspan=2, sticky=tk.W)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=20)
        
        self.start_button = ttk.Button(button_frame, text="🚀 Sortierung starten", 
                                      command=self.start_sorting)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="⏹️ Stoppen", 
                                     command=self.stop_sorting, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="📋 Log löschen", 
                  command=self.clear_log).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="🔢 Hash-Datenbank verwalten", 
                  command=self.open_hash_manager).pack(side=tk.LEFT, padx=5)
        
        # Fortschrittsbalken
        self.progress_var = tk.StringVar(value="Bereit")
        ttk.Label(main_frame, textvariable=self.progress_var).grid(row=6, column=0, columnspan=3, pady=5)
        
        self.progress_bar = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress_bar.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # Log-Ausgabe
        log_frame = ttk.LabelFrame(main_frame, text="Log-Ausgabe", padding="5")
        log_frame.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=18, width=110)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Grid-Konfiguration
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(8, weight=1)
        
    def setup_logging(self):
        """Konfiguriert Logging für GUI"""
        self.logger = logging.getLogger('ImageSorterGUI')
        self.logger.setLevel(logging.INFO)
        
        # Handler für GUI-Ausgabe
        gui_handler = GUILogHandler(self.log_text)
        gui_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        gui_handler.setFormatter(formatter)
        self.logger.addHandler(gui_handler)
        
        # File handler mit UTF-8 Encoding
        file_handler = logging.FileHandler('image_sorter_gui.log', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
    def browse_source(self):
        """Durchsucht Quellordner"""
        folder = filedialog.askdirectory(title="Quellordner mit Medien auswählen")
        if folder:
            self.source_dir.set(folder)
    
    def browse_target(self):
        """Durchsucht Zielordner"""
        folder = filedialog.askdirectory(title="Zielordner für sortierte Medien auswählen")
        if folder:
            self.target_dir.set(folder)
    
    def clear_log(self):
        """Löscht Log-Ausgabe"""
        self.log_text.delete(1.0, tk.END)
    
    def open_hash_manager(self):
        """Öffnet Hash-Datenbank-Manager"""
        if not self.target_dir.get():
            messagebox.showwarning("Achtung", "Bitte erst einen Zielordner auswählen!")
            return
        
        db_path = Path(self.target_dir.get()) / "media_hashes.db"
        if not db_path.exists():
            messagebox.showinfo("Info", f"Keine Hash-Datenbank gefunden in:\n{db_path}\n\nDatenbank wird nach der ersten Sortierung erstellt.")
            return
        
        HashManagerWindow(self.root, db_path)
    
    def validate_inputs(self):
        """Validiert Eingaben"""
        if not self.source_dir.get():
            messagebox.showerror("Fehler", "Bitte Quellordner auswählen!")
            return False
        
        if not self.target_dir.get():
            messagebox.showerror("Fehler", "Bitte Zielordner auswählen!")
            return False
        
        if not Path(self.source_dir.get()).exists():
            messagebox.showerror("Fehler", "Quellordner existiert nicht!")
            return False
        
        if self.source_dir.get() == self.target_dir.get():
            messagebox.showerror("Fehler", "Quell- und Zielordner müssen unterschiedlich sein!")
            return False
        
        # Prüfe ob mindestens ein Medientyp ausgewählt ist oder custom extensions gesetzt
        has_custom = self.custom_extensions.get().strip() != ""
        has_checkbox = self.process_images.get() or self.process_raw.get() or self.process_videos.get() or self.process_audio.get()
        if not (has_custom or has_checkbox):
            messagebox.showerror("Fehler", "Bitte mindestens einen Medientyp auswählen oder bestimmte Endungen angeben!")
            return False
        
        return True
    

    
    def start_sorting(self):
        """Startet Sortierung in separatem Thread"""
        if not self.validate_inputs():
            return
        
        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress_bar.start()
        
        # Starte in separatem Thread
        thread = threading.Thread(target=self.run_sorting)
        thread.daemon = True
        thread.start()
    
    def stop_sorting(self):
        """Stoppt Sortierung"""
        self.is_running = False
        if self.sorter:
            self.sorter.is_running = False
        self.logger.info("Sortierung wird gestoppt...")
        self.progress_var.set("Stoppe...")
    
    def run_sorting(self):
        """Führt Sortierung aus"""
        try:
            # Sortierer erstellen
            self.sorter = ImageSorter(
                source_dir=self.source_dir.get(),
                target_dir=self.target_dir.get(),
                copy_mode=self.copy_mode.get(),
                sort_by_day=self.sort_by_day.get(),
                dry_run=self.dry_run.get(),
                use_hash_db=self.use_hash_db.get(),
                validate_dates=self.validate_dates.get(),
                earliest_valid_year=self.earliest_valid_year.get(),
                handle_duplicates=self.duplicate_mode.get() == "verschieben", # Verschieben ist aktiv
                ignore_duplicates=self.duplicate_mode.get() == "ignorieren", # Ignorieren ist aktiv
                batch_processing=self.batch_processing.get(),
                logger=self.logger,
                gui_callback=self.update_progress,
                process_images=self.process_images.get(),
                process_raw=self.process_raw.get(),
                process_videos=self.process_videos.get(),
                process_audio=self.process_audio.get(),
                turbo_duplicate_detection=self.turbo_duplicate_detection.get(),
                custom_extensions=self.custom_extensions.get()
            )
            
            # Status synchronisieren
            self.sorter.is_running = self.is_running
            
            # Sortierung ausführen
            self.sorter.run()
            
            if not self.is_running:
                self.logger.info("Sortierung wurde gestoppt")
                self.progress_var.set("Gestoppt")
            else:
                self.logger.info("Sortierung erfolgreich abgeschlossen!")
                self.progress_var.set("Abgeschlossen")
                
                # Erfolgsmeldung
                unknown_count = len(self.sorter.unknown_date_files)
                invalid_count = len(self.sorter.invalid_date_files)
                skipped_count = len(self.sorter.skipped_files)
                conflict_count = len(self.sorter.duplicate_date_conflicts)
                unknown_msg = f"\nDateien mit unbekanntem Datum: {unknown_count}" if unknown_count > 0 else ""
                invalid_msg = f"\nDateien mit unrealistischem Datum: {invalid_count}" if invalid_count > 0 else ""
                skipped_msg = f"\nÜbersprungene Dateien (bereits in DB): {skipped_count}" if skipped_count > 0 else ""
                conflict_msg = f"\nDuplikat-Datumskonflikte (früheres Datum gewählt): {conflict_count}" if conflict_count > 0 else ""
                
                # Medientyp-Information
                selected_types = []
                if self.process_images.get():
                    selected_types.append("Bilder")
                if self.process_videos.get():
                    selected_types.append("Videos")
                if self.process_audio.get():
                    selected_types.append("Audio")
                media_types_msg = f"\nVerarbeitete Medientypen: {', '.join(selected_types)}"
                
                # Duplikat-Information abhängig von Einstellung
                duplicate_mode = self.duplicate_mode.get()
                if duplicate_mode == "verschieben":
                    duplicate_msg = f"\nGefundene Duplikate: {len(self.sorter.duplicates)}"
                elif duplicate_mode == "ignorieren":
                    duplicate_msg = f"\nDuplikate ignoriert: {len(self.sorter.duplicates)} (Original sortiert, Rest unberührt)"
                else:
                    duplicate_msg = "\nDuplikat-Behandlung: Deaktiviert"
                
                action_text = "Kopierte Dateien" if self.copy_mode.get() else "Verschobene Dateien"
                
                self.root.after(0, lambda: messagebox.showinfo(
                    "Erfolg", 
                    "Sortierung erfolgreich abgeschlossen!\n\n"
                    f"{action_text}: {len(self.sorter.moved_files)}"
                    f"{media_types_msg}"
                    f"{duplicate_msg}"
                    f"{unknown_msg}"
                    f"{invalid_msg}"
                    f"{skipped_msg}"
                    f"{conflict_msg}\n\n"
                    "Überprüfe den Bericht für Details."
                ))
                
        except Exception as e:
            self.logger.error(f"Fehler bei der Sortierung: {e}")
            self.root.after(0, lambda: messagebox.showerror("Fehler", f"Fehler bei der Sortierung:\n{e}"))
            self.progress_var.set("Fehler")
        
        finally:
            self.is_running = False
            self.root.after(0, self.sorting_finished)
    
    def update_progress(self, message):
        """Aktualisiert Fortschrittsanzeige"""
        self.root.after(0, lambda: self.progress_var.set(message))
    
    def sorting_finished(self):
        """Wird nach Sortierung aufgerufen"""
        self.progress_bar.stop()
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

class GUILogHandler(logging.Handler):
    """Log-Handler für GUI-Ausgabe"""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
    
    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.see(tk.END)
        self.text_widget.after(0, append)

class ImageSorter:
    """Modifizierte Version des ImageSorters für GUI"""
    
    # Hash-Berechnung Konstanten
    CHUNK_SIZE = 65536  # 64KB chunks
    TURBO_SMALL_FILE_THRESHOLD = 1024 * 1024  # 1MB
    TURBO_MEDIUM_FILE_THRESHOLD = 50 * 1024 * 1024  # 50MB
    TURBO_SAMPLE_SIZE_MEDIUM = 1024 * 1024  # 1MB pro Sample
    TURBO_SAMPLE_SIZE_LARGE = 512 * 1024  # 512KB pro Sample
    
    # Unterstützte Medienformate
    IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif', '.webp'}
    RAW_FORMATS = {'.cr2', '.cr3', '.crw', '.nef', '.arw', '.dng', '.raf', '.orf', '.rw2', '.pef', '.srw', '.raw'}
    VIDEO_FORMATS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.mpg', '.mpeg'}
    AUDIO_FORMATS = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma', '.opus', '.aiff', '.alac'}
    
    def __init__(self, source_dir: str, target_dir: str, copy_mode: bool = False,
                 sort_by_day: bool = False, dry_run: bool = False, use_hash_db: bool = True,
                 validate_dates: bool = True, earliest_valid_year: int = 2004, handle_duplicates: bool = True,
                 ignore_duplicates: bool = False, batch_processing: bool = False, logger=None, gui_callback=None,
                 process_images: bool = True, process_raw: bool = False, process_videos: bool = False,
                 process_audio: bool = False, turbo_duplicate_detection: bool = False, custom_extensions: str = ""):
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        self.copy_mode = copy_mode
        self.sort_by_day = sort_by_day
        self.dry_run = dry_run
        self.use_hash_db = use_hash_db
        self.validate_dates = validate_dates
        self.earliest_valid_year = earliest_valid_year
        self.handle_duplicates_enabled = handle_duplicates
        self.ignore_duplicates = ignore_duplicates
        self.batch_processing = batch_processing
        self.batch_size = 1000  # Anzahl Dateien pro Batch
        
        # Turbo-Modus für Duplikaterkennung
        self.turbo_duplicate_detection = turbo_duplicate_detection
        
        # Medientyp-Optionen
        self.process_images = process_images
        self.process_raw = process_raw
        self.process_videos = process_videos
        self.process_audio = process_audio
        
        self.logger = logger or logging.getLogger(__name__)
        self.gui_callback = gui_callback
        self.duplicates: Dict[str, List[Path]] = {}
        self.processed_files: Set[str] = set()
        self.moved_files: List[Tuple[Path, Path]] = []
        self.unknown_date_files: List[Path] = []
        self.skipped_files: List[Path] = []  # Bereits in DB vorhandene Dateien
        self.invalid_date_files: List[Path] = []  # Dateien mit ungültigen Daten (vor 2004/nach heute)
        self.duplicate_date_conflicts: List[Tuple[Path, str, str]] = []  # Dateien mit Duplikat-Datumskonflikten (Datei, altes Datum, neues Datum)
        
        # Status-Variablen
        self.is_running = True  # Wird von GUI gesetzt für Abbruch-Funktionalität
        
        # Set für Tracking von ungültigen Dateinamen-Daten
        self._invalid_filename_dates = set()
        
        # Hash-Datenbank
        self.hash_db_path = self.target_dir / "media_hashes.db"  # Umbenannt für alle Medientypen
        self.hash_db = None
        
        # Kombiniere alle gewählten Formate
        self.supported_formats = set()

        # Custom Extensions überschreiben die Checkboxen
        if custom_extensions and custom_extensions.strip():
            # Parse custom extensions (z.B. ".crw, .thm" oder ".crw .thm")
            for ext in custom_extensions.replace(',', ' ').split():
                ext = ext.strip().lower()
                if ext and not ext.startswith('.'):
                    ext = '.' + ext
                if ext:
                    self.supported_formats.add(ext)
            self.logger.info(f"Nur bestimmte Endungen: {', '.join(sorted(self.supported_formats))}")
        else:
            # Normale Checkbox-Logik
            if self.process_images:
                self.supported_formats.update(self.IMAGE_FORMATS)
            if self.process_raw:
                self.supported_formats.update(self.RAW_FORMATS)
            if self.process_videos:
                self.supported_formats.update(self.VIDEO_FORMATS)
            if self.process_audio:
                self.supported_formats.update(self.AUDIO_FORMATS)
        
        # Regex patterns für Datum im Dateinamen
        self.date_patterns = [
            r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
            r'(\d{4})(\d{2})(\d{2})',    # YYYYMMDD
            r'(\d{2})\.(\d{2})\.(\d{4})', # DD.MM.YYYY
            r'(\d{2})-(\d{2})-(\d{4})',  # DD-MM-YYYY
            r'IMG_(\d{4})(\d{2})(\d{2})', # IMG_YYYYMMDD
            r'(\d{4})-(\d{2})',          # YYYY-MM
            r'(\d{4})(\d{2})',           # YYYYMM
        ]
    
    def update_gui(self, message):
        """Aktualisiert GUI wenn Callback verfügbar"""
        if self.gui_callback:
            self.gui_callback(message)
    
    def init_hash_database(self):
        """Initialisiert die Hash-Datenbank"""
        if not self.use_hash_db:
            return
        
        try:
            self.hash_db = sqlite3.connect(str(self.hash_db_path))
            cursor = self.hash_db.cursor()
            
            # Tabelle erstellen falls nicht vorhanden
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS media_hashes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_hash TEXT UNIQUE NOT NULL,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    media_type TEXT NOT NULL,
                    date_added TEXT NOT NULL,
                    date_taken TEXT,
                    date_source TEXT
                )
            ''')
            
            # Index für bessere Performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_hash ON media_hashes(file_hash)')
            
            self.hash_db.commit()
            self.logger.info(f"Hash-Datenbank initialisiert: {self.hash_db_path}")
            
        except Exception as e:
            self.logger.error(f"Fehler beim Initialisieren der Hash-Datenbank: {e}")
            self.hash_db = None
    
    def close_hash_database(self):
        """Schließt die Hash-Datenbank"""
        if self.hash_db:
            self.hash_db.close()
            self.hash_db = None
    
    def get_file_info_from_database(self, file_hash: str) -> Optional[Dict]:
        """Holt Informationen zu einer Datei aus der Hash-Datenbank"""
        if not self.hash_db:
            return None
        
        try:
            cursor = self.hash_db.cursor()
            cursor.execute('''
                SELECT file_name, file_path, date_taken, date_source 
                FROM media_hashes WHERE file_hash = ?
            ''', (file_hash,))
            result = cursor.fetchone()
            
            if result:
                return {
                    'file_name': result[0],
                    'file_path': result[1],
                    'date_taken': datetime.fromisoformat(result[2]) if result[2] else None,
                    'date_source': result[3]
                }
            return None
        except Exception as e:
            self.logger.error(f"Fehler beim Abrufen der Datei-Info aus Hash-Datenbank: {e}")
            return None
    
    def is_file_in_database(self, file_hash: str) -> bool:
        """Prüft ob Datei bereits in der Datenbank ist"""
        if not self.hash_db:
            return False
        
        try:
            cursor = self.hash_db.cursor()
            cursor.execute('SELECT COUNT(*) FROM media_hashes WHERE file_hash = ?', (file_hash,))
            count = cursor.fetchone()[0]
            return count > 0
        except Exception as e:
            self.logger.error(f"Fehler beim Prüfen der Hash-Datenbank: {e}")
            return False
    
    def get_media_type(self, file_path: Path) -> str:
        """Bestimmt den Medientyp basierend auf der Dateiendung"""
        suffix = file_path.suffix.lower()
        
        if suffix in self.IMAGE_FORMATS or suffix in self.RAW_FORMATS:
            return "IMAGE"
        elif suffix in self.VIDEO_FORMATS:
            return "VIDEO"
        elif suffix in self.AUDIO_FORMATS:
            return "AUDIO"
        else:
            return "UNKNOWN"
    
    def move_existing_file_to_new_date(self, existing_file_path: str, new_date: datetime, new_date_source: str) -> bool:
        """Verschiebt eine bereits sortierte Datei zu einem neuen Datum"""
        try:
            existing_path = Path(existing_file_path)
            if not existing_path.exists():
                self.logger.warning(f"Bereits sortierte Datei nicht gefunden: {existing_path}")
                return False
            
            # Erstelle neuen Zielpfad
            new_target_path = self.create_target_path(new_date, existing_path.name, new_date_source)
            
            # Erstelle Zielverzeichnis
            if not self.dry_run:
                new_target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Behandle Namenskonflikte
            if new_target_path.exists():
                counter = 1
                stem = new_target_path.stem
                suffix = new_target_path.suffix
                while new_target_path.exists():
                    new_target_path = new_target_path.parent / f"{stem}_{counter}{suffix}"
                    counter += 1
            
            # Verschiebe die Datei
            if not self.dry_run:
                shutil.move(str(existing_path), str(new_target_path))
                self.logger.info(f"Bereits sortierte Datei verschoben: {existing_path.name}")
                self.logger.info(f"  Von: {existing_path.relative_to(self.target_dir)}")
                self.logger.info(f"  Nach: {new_target_path.relative_to(self.target_dir)}")
                return True
            else:
                self.logger.info(f"[TESTLAUF] Würde bereits sortierte Datei verschieben: {existing_path.name}")
                self.logger.info(f"  Von: {existing_path.relative_to(self.target_dir)}")
                self.logger.info(f"  Nach: {new_target_path.relative_to(self.target_dir)}")
                return True
                
        except Exception as e:
            self.logger.error(f"Fehler beim Verschieben der bereits sortierten Datei: {e}")
            return False
    
    def add_file_to_database(self, file_path: Path, file_hash: str, target_path: Path, 
                           file_date: datetime, date_source: str):
        """Fügt Datei zur Hash-Datenbank hinzu"""
        if not self.hash_db or self.dry_run:
            return
        
        try:
            media_type = self.get_media_type(file_path)
            cursor = self.hash_db.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO media_hashes 
                (file_hash, file_name, file_path, file_size, media_type, date_added, date_taken, date_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                file_hash,
                file_path.name,
                str(target_path),
                file_path.stat().st_size,
                media_type,
                datetime.now().isoformat(),
                file_date.isoformat(),
                date_source
            ))
            self.hash_db.commit()
            
        except Exception as e:
            self.logger.error(f"Fehler beim Hinzufügen zur Hash-Datenbank: {e}")
    
    def get_database_stats(self) -> Dict[str, int]:
        """Holt Statistiken aus der Hash-Datenbank"""
        if not self.hash_db:
            return {}
        
        try:
            cursor = self.hash_db.cursor()
            cursor.execute('SELECT COUNT(*) FROM media_hashes')
            total_files = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT file_hash) FROM media_hashes')
            unique_hashes = cursor.fetchone()[0]
            
            return {
                'total_files': total_files,
                'unique_hashes': unique_hashes,
                'potential_duplicates': total_files - unique_hashes
            }
        except Exception as e:
            self.logger.error(f"Fehler beim Abrufen der Datenbankstatistiken: {e}")
            return {}
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Berechnet MD5 Hash einer Datei mit optimierter Chunk-Größe und Turbo-Modus"""
        hash_md5 = hashlib.md5()
        try:
            file_size = file_path.stat().st_size
            
            if self.turbo_duplicate_detection:
                self._calculate_turbo_hash(hash_md5, file_path, file_size)
            else:
                self._calculate_full_hash(hash_md5, file_path)
            
            return hash_md5.hexdigest()
            
        except Exception as e:
            self.logger.error(f"Fehler beim Hash-Berechnen für {file_path}: {e}")
            return None  # Verwende None statt leerer String
    
    def _calculate_full_hash(self, hash_md5, file_path: Path):
        """Berechnet vollständigen Hash der Datei"""
        with open(file_path, "rb") as f:
            while chunk := f.read(self.CHUNK_SIZE):
                hash_md5.update(chunk)
    
    def _calculate_turbo_hash(self, hash_md5, file_path: Path, file_size: int):
        """Berechnet Hash im Turbo-Modus basierend auf Dateigröße - OHNE Dateiname oder Dateigröße im Hash"""
        
        if file_size < self.TURBO_SMALL_FILE_THRESHOLD:
            # Kleine Dateien: Vollständiger Hash
            self._calculate_full_hash(hash_md5, file_path)
        elif file_size < self.TURBO_MEDIUM_FILE_THRESHOLD:
            # Mittlere Dateien: Sampling-Hash (Anfang, Mitte, Ende)
            self._calculate_sample_hash(hash_md5, file_path, file_size, self.TURBO_SAMPLE_SIZE_MEDIUM)
        else:
            # Große Dateien: Schnell-Hash NUR auf Dateiinhalt basierend
            self._calculate_sample_hash(hash_md5, file_path, file_size, self.TURBO_SAMPLE_SIZE_LARGE)
    
    def _calculate_sample_hash(self, hash_md5, file_path: Path, file_size: int, sample_size: int):
        """Berechnet Hash basierend auf Datei-Samples"""
        with open(file_path, "rb") as f:
            # Anfang
            chunk = f.read(sample_size)
            if chunk:
                hash_md5.update(chunk)
            
            # Mitte (nur wenn Datei groß genug)
            if file_size > sample_size * 2:
                f.seek(file_size // 2 - sample_size // 2)
                chunk = f.read(sample_size)
                if chunk:
                    hash_md5.update(chunk)
            
            # Ende (nur wenn Datei groß genug)
            if file_size > sample_size * 3:
                f.seek(-sample_size, 2)
                chunk = f.read(sample_size)
                if chunk:
                    hash_md5.update(chunk)
    
    def get_exif_date(self, file_path: Path) -> Optional[datetime]:
        """Extrahiert Aufnahmedatum aus EXIF-Daten (für Bilder und RAW-Dateien)"""
        suffix = file_path.suffix.lower()

        # Prüfe ob es ein Bild oder RAW-Format ist
        if suffix not in self.IMAGE_FORMATS and suffix not in self.RAW_FORMATS:
            return None

        # Für RAW-Dateien: exifread verwenden
        if suffix in self.RAW_FORMATS:
            try:
                with open(file_path, 'rb') as f:
                    tags = exifread.process_file(f, details=False)
                    for tag_name in ['EXIF DateTimeOriginal', 'EXIF DateTimeDigitized', 'Image DateTime']:
                        if tag_name in tags:
                            try:
                                return datetime.strptime(str(tags[tag_name]), '%Y:%m:%d %H:%M:%S')
                            except ValueError:
                                continue
            except Exception as e:
                self.logger.debug(f"Keine EXIF-Daten für RAW {file_path}: {e}")
            return None

        # Für normale Bilder: PIL verwenden
        try:
            with Image.open(file_path) as img:
                exif_data = img._getexif()
                if exif_data:
                    for tag_id, value in exif_data.items():
                        tag = TAGS.get(tag_id, tag_id)
                        if tag in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                            try:
                                return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                            except ValueError:
                                continue
        except Exception as e:
            self.logger.debug(f"Keine EXIF-Daten für {file_path}: {e}")
        return None
    
    def get_media_metadata_date(self, file_path: Path) -> Optional[datetime]:
        """Extrahiert Metadaten-Datum für Videos und Audio-Dateien"""
        media_type = self.get_media_type(file_path)
        
        if media_type == "IMAGE":
            return self.get_exif_date(file_path)
        elif media_type in ["VIDEO", "AUDIO"]:
            # Für Videos und Audio verwenden wir erstmal Datei-Metadaten
            # Später könnte hier ffprobe oder ähnliche Tools verwendet werden
            try:
                # Versuche das Änderungsdatum als Aufnahmedatum zu interpretieren
                modification_time = file_path.stat().st_mtime
                return datetime.fromtimestamp(modification_time)
            except Exception as e:
                self.logger.debug(f"Keine Metadaten für {file_path}: {e}")
                return None
        
        return None
    
    def _validate_date_components(self, year_int: int, month_int: int, day_int: int = None) -> bool:
        """Validiert Datums-Komponenten"""
        # Prüfe Jahr
        if not (1900 <= year_int <= 2100):
            return False
        
        # Prüfe Monat
        if not (1 <= month_int <= 12):
            return False
        
        # Prüfe Tag (falls angegeben)
        if day_int is not None:
            if not (1 <= day_int <= 31):
                return False
            
            # Prüfe ob Tag für den gegebenen Monat gültig ist
            days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            if day_int > days_in_month[month_int - 1]:
                return False
        
        return True
    
    def get_date_from_filename(self, filename: str) -> Optional[datetime]:
        """Extrahiert Datum aus Dateiname (ignoriert Ordnernamen)"""
        # Stelle sicher, dass nur der Dateiname verwendet wird, nicht der Pfad
        if isinstance(filename, Path):
            filename = filename.name
        else:
            # Falls ein Pfad übergeben wurde, extrahiere nur den Dateinamen
            filename = Path(filename).name
        
        self.logger.debug(f"Suche Datum in Dateiname: {filename}")
        
        # Flag um zu tracken ob wir ein ungültiges Datum gefunden haben
        found_invalid_date = False
        matched_positions = []  # Speichere bereits gematche Positionen
        
        for pattern in self.date_patterns:
            match = re.search(pattern, filename)
            if match:
                # Prüfe ob dieser Match sich mit einem bereits ungültigen Match überschneidet
                match_start, match_end = match.span()
                overlap_with_invalid = False
                for invalid_start, invalid_end in matched_positions:
                    if not (match_end <= invalid_start or match_start >= invalid_end):
                        overlap_with_invalid = True
                        break
                
                if overlap_with_invalid:
                    self.logger.debug(f"Pattern {pattern} überlappt mit bereits ungültigem Match in '{filename}' - überspringe")
                    continue
                
                groups = match.groups()
                try:
                    if len(groups) == 3:
                        if len(groups[0]) == 4:  # YYYY-MM-DD format
                            year, month, day = groups
                        else:  # DD-MM-YYYY format
                            day, month, year = groups
                        
                        # Explizite Validierung der Datumswerte vor datetime-Erstellung
                        year_int = int(year)
                        month_int = int(month)
                        day_int = int(day)
                        
                        # Prüfe Gültigkeitsbereiche
                        if not self._validate_date_components(year_int, month_int, day_int):
                            self.logger.debug(f"Ungültiger Datumswert in '{filename}' - überspringe")
                            found_invalid_date = True
                            matched_positions.append((match_start, match_end))
                            continue
                        
                        # Prüfe ob Tag für den gegebenen Monat gültig ist
                        # Februar kann max 29 Tage haben, April/Juni/September/November max 30
                        days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
                        if day_int > days_in_month[month_int - 1]:
                            self.logger.debug(f"Tag {day_int} ungültig für Monat {month_int} in '{filename}' - überspringe")
                            found_invalid_date = True
                            matched_positions.append((match_start, match_end))
                            continue
                        
                        # Jetzt können wir sicher datetime erstellen
                        result_date = datetime(year_int, month_int, day_int)
                        self.logger.debug(f"Datum aus Dateiname extrahiert: {result_date.strftime('%Y-%m-%d')} aus '{filename}'")
                        return result_date
                        
                    elif len(groups) == 2:  # YYYY-MM format
                        year, month = groups
                        year_int = int(year)
                        month_int = int(month)
                        
                        # Prüfe ob dieser 2-Gruppen-Match Teil eines bereits ungültigen 3-Gruppen-Matches ist
                        # Zum Beispiel: 2005035416 -> erst (2005, 03, 54) ungültig, dann (2005, 03) gültig
                        # Das sollten wir verhindern
                        for invalid_start, invalid_end in matched_positions:
                            if match_start >= invalid_start and match_end <= invalid_end:
                                self.logger.debug(f"YYYY-MM Pattern {pattern} ist Teil eines bereits ungültigen Matches in '{filename}' - überspringe")
                                overlap_with_invalid = True
                                break
                        
                        if overlap_with_invalid:
                            continue
                        
                        # Validiere Jahr und Monat
                        if not self._validate_date_components(year_int, month_int):
                            self.logger.debug(f"Ungültiger Datumswert in '{filename}' - überspringe")
                            found_invalid_date = True
                            matched_positions.append((match_start, match_end))
                            continue
                        
                        result_date = datetime(year_int, month_int, 1)
                        self.logger.debug(f"Datum aus Dateiname extrahiert: {result_date.strftime('%Y-%m-%d')} aus '{filename}'")
                        return result_date
                        
                except ValueError as e:
                    self.logger.debug(f"Fehler beim Parsen des Datums aus '{filename}': {e}")
                    found_invalid_date = True
                    matched_positions.append((match_start, match_end))
                    continue
        
        # Wenn wir hier ankommen, wurde kein gültiges Datum gefunden
        if found_invalid_date:
            self.logger.debug(f"Ungültiges Datum im Dateinamen gefunden: {filename}")
            # Speichere Info über ungültiges Datum für determine_date
            if not hasattr(self, '_invalid_filename_dates'):
                self._invalid_filename_dates = set()
            self._invalid_filename_dates.add(filename)
        else:
            self.logger.debug(f"Kein Datum im Dateinamen gefunden: {filename}")
        
        return None
    

    def get_file_metadata_dates(self, file_path: Path) -> datetime:
        """Holt das beste Datum aus Datei-Metadaten (Erstellung vs. Änderung)"""
        try:
            # Hole beide Zeiten
            if os.name == 'nt':
                # Windows: getctime = Erstellungszeit, getmtime = Änderungszeit
                creation_time = os.path.getctime(file_path)
                modification_time = os.path.getmtime(file_path)
            else:
                # Unix-Systeme: getctime = Metadaten-Änderung, getmtime = Inhalt-Änderung
                # Verwende stat für bessere Kontrolle
                stat = file_path.stat()
                creation_time = getattr(stat, 'st_birthtime', stat.st_ctime)  # st_birthtime falls verfügbar
                modification_time = stat.st_mtime
            
            creation_date = datetime.fromtimestamp(creation_time)
            modification_date = datetime.fromtimestamp(modification_time)
            
            # Nimm das frühere der beiden Daten (wahrscheinlich näher am Aufnahmedatum)
            earlier_date = min(creation_date, modification_date)
            
            self.logger.debug(f"Dateimetadaten für {file_path.name}: "
                             f"Erstellt: {creation_date.strftime('%Y-%m-%d')}, "
                             f"Geändert: {modification_date.strftime('%Y-%m-%d')}, "
                             f"Gewählt: {earlier_date.strftime('%Y-%m-%d')}")
            
            return earlier_date
            
        except Exception as e:
            self.logger.error(f"Fehler beim Abrufen der Datei-Metadaten für {file_path}: {e}")
            return datetime.now()
    
    def is_date_realistic(self, date: datetime) -> bool:
        """Prüft ob ein Datum realistisch für ein Digitalfoto ist"""
        if not date:
            return False
        
        # Wenn Validierung deaktiviert ist, alle Daten als gültig betrachten
        if not self.validate_dates:
            return True
        
        # Verwendung des konfigurierbaren frühesten gültigen Jahres
        min_date = datetime(self.earliest_valid_year, 1, 1)
        max_date = datetime.now()
        
        is_valid = min_date <= date <= max_date
        
        if not is_valid:
            self.logger.debug(f"Unrealistisches Datum erkannt: {date.strftime('%Y-%m-%d')} "
                             f"(gültig: {min_date.strftime('%Y-%m-%d')} bis {max_date.strftime('%Y-%m-%d')})")
        
        return is_valid
    
    def determine_date(self, file_path: Path) -> tuple[datetime, str]:
        """Bestimmt das beste verfügbare Datum für eine Datei"""
        found_unrealistic_date = False
        found_invalid_filename_date = False
        
        # 1. Priorität: Datum im Dateinamen (wenn realistisch)
        filename_date = self.get_date_from_filename(file_path.name)
        if filename_date and self.is_date_realistic(filename_date):
            return filename_date, "FILENAME"
        elif filename_date:
            found_unrealistic_date = True
            self.logger.debug(f"Dateinamen-Datum unrealistisch für {file_path.name}: {filename_date.strftime('%Y-%m-%d')}")
        else:
            # Prüfe ob ein ungültiges Datum im Dateinamen gefunden wurde
            if hasattr(self, '_invalid_filename_dates') and file_path.name in self._invalid_filename_dates:
                found_invalid_filename_date = True
                self.logger.debug(f"Ungültiges Datums-Pattern im Dateinamen bekannt für {file_path.name}")
            else:
                # Fallback: Prüfe nochmals alle Patterns (für Rückwärtskompatibilität)
                for pattern in self.date_patterns:
                    match = re.search(pattern, file_path.name)
                    if match:
                        found_invalid_filename_date = True
                        self.logger.debug(f"Ungültiges Datums-Pattern im Dateinamen gefunden für {file_path.name}: {match.groups()}")
                        break
        
        # 2. Priorität: Metadaten (EXIF für Bilder, Datei-Metadaten für Videos/Audio)
        metadata_date = self.get_media_metadata_date(file_path)
        if metadata_date and self.is_date_realistic(metadata_date):
            media_type = self.get_media_type(file_path)
            if media_type == "IMAGE":
                return metadata_date, "EXIF"
            else:
                return metadata_date, "METADATA"
        elif metadata_date:
            found_unrealistic_date = True
            self.logger.debug(f"Metadaten-Datum unrealistisch für {file_path.name}: {metadata_date.strftime('%Y-%m-%d')}")
        
        # 3. Priorität: Datei-Metadaten (Erstellungs-/Änderungsdatum)
        file_metadata_date = self.get_file_metadata_dates(file_path)
        if file_metadata_date and self.is_date_realistic(file_metadata_date):
            return file_metadata_date, "METADATA"
        elif file_metadata_date:
            found_unrealistic_date = True
            self.logger.debug(f"Datei-Metadaten-Datum unrealistisch für {file_path.name}: {file_metadata_date.strftime('%Y-%m-%d')}")
        
        # 4. Fallback: Unterscheide zwischen verschiedenen Arten von "kein Datum"
        fallback_date = datetime.now()
        if found_unrealistic_date or found_invalid_filename_date:
            self.logger.warning(f"Nur unrealistische/ungültige Daten gefunden für {file_path.name}, verwende aktuelles Datum")
            return fallback_date, "INVALID"
        else:
            self.logger.warning(f"Kein Datum gefunden für {file_path.name}, verwende aktuelles Datum")
            return fallback_date, "UNKNOWN"
    
    def create_target_path(self, date: datetime, filename: str, date_source: str = "KNOWN") -> Path:
        """Erstellt Zielpfad basierend auf Datum"""
        if date_source == "UNKNOWN":
            # Spezialordner für Dateien ohne erkennbares realistisches Datum
            return self.target_dir / "_unknown_date" / filename
        elif date_source == "INVALID":
            # Spezialordner für Dateien mit unrealistischen Daten
            return self.target_dir / "_invalid_date" / filename
        else:
            year = date.strftime('%Y')
            month = date.strftime('%m-%B')
            
            if self.sort_by_day:
                # Tages-Sortierung: 2023/01-January/01
                day = date.strftime('%d')
                return self.target_dir / year / month / day / filename
            else:
                # Monats-Sortierung: 2023/01-January
                return self.target_dir / year / month / filename
    
    def find_duplicates(self) -> None:
        """Findet Duplikate basierend auf Dateihash mit Multi-Threading und Turbo-Modus"""
        if not self.handle_duplicates_enabled and not self.ignore_duplicates:
            self.logger.info("Duplikat-Suche übersprungen (deaktiviert)")
            return
        
        mode_text = "🚀 TURBO-MODUS" if self.turbo_duplicate_detection else "Standard-Modus"
        self.logger.info(f"Suche nach Duplikaten... ({mode_text})")
        self.update_gui(f"🔍 Suche nach Duplikaten... ({mode_text})")
        
        # Sammle alle relevanten Dateien
        files_to_check = []
        for file_path in self.source_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                files_to_check.append(file_path)
        
        if not files_to_check:
            self.logger.info("Keine Mediendateien gefunden.")
            return
        
        self.logger.info(f"Prüfe {len(files_to_check)} Dateien auf Duplikate...")
        
        # TURBO-MODUS: Zusätzliche Optimierungen
        if self.turbo_duplicate_detection:
            # 1. Vorfilterung nach Dateigröße (schneller als Hash-Berechnung)
            self.logger.info("🚀 Turbo-Optimierung: Vorfilterung nach Dateigröße...")
            size_groups = {}
            for file_path in files_to_check:
                try:
                    file_size = file_path.stat().st_size
                    if file_size not in size_groups:
                        size_groups[file_size] = []
                    size_groups[file_size].append(file_path)
                except Exception as e:
                    self.logger.debug(f"Fehler beim Lesen der Dateigröße für {file_path}: {e}")
            
            # Nur Dateien mit gleicher Größe können Duplikate sein
            potential_duplicates = []
            size_groups_with_duplicates = 0
            for size, files in size_groups.items():
                if len(files) > 1:
                    potential_duplicates.extend(files)
                    size_groups_with_duplicates += 1
            
            files_to_check = potential_duplicates
            self.logger.info(f"🚀 Vorfilterung: {len(files_to_check)} potentielle Duplikate in {size_groups_with_duplicates} Größengruppen")
            
            if not files_to_check:
                self.logger.info("Keine potentiellen Duplikate nach Größenfilterung gefunden.")
                return
        
        # Verwende ThreadPoolExecutor für parallele Hash-Berechnung
        
        hash_to_files: Dict[str, List[Path]] = {}
        hash_lock = threading.Lock()
        processed_count = 0
        
        def calculate_hash_safe(file_path):
            """Thread-sichere Hash-Berechnung"""
            nonlocal processed_count
            try:
                file_hash = self.calculate_file_hash(file_path)
                if file_hash:  # file_hash ist jetzt None oder ein gültiger Hash
                    with hash_lock:
                        if file_hash not in hash_to_files:
                            hash_to_files[file_hash] = []
                        hash_to_files[file_hash].append(file_path)
                        
                        processed_count += 1
                        update_interval = 25 if self.turbo_duplicate_detection else 50
                        if processed_count % update_interval == 0:  # Häufigere Updates im Turbo-Modus
                            self.update_gui(f"🔍 Geprüft: {processed_count}/{len(files_to_check)} Dateien")
                else:
                    # Hash-Berechnung fehlgeschlagen - trotzdem zählen für Fortschritt
                    with hash_lock:
                        processed_count += 1
                        if processed_count % 50 == 0:
                            self.update_gui(f"🔍 Geprüft: {processed_count}/{len(files_to_check)} Dateien")
                
                return file_hash
            except Exception as e:
                self.logger.error(f"Fehler beim Hash-Berechnen für {file_path}: {e}")
                return None
        
        # Optimale Thread-Anzahl basierend auf Modus
        import os
        if self.turbo_duplicate_detection:
            # Turbo-Modus: Mehr Threads für I/O-intensive Operationen
            max_workers = min(16, max(4, (os.cpu_count() or 4) * 2))
        else:
            # Standard-Modus: Konservative Thread-Anzahl
            max_workers = min(8, max(2, os.cpu_count() or 2))
        
        self.logger.info(f"Verwende {max_workers} Threads für Hash-Berechnung")
        
        # Parallel Hash-Berechnung
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(calculate_hash_safe, file_path): file_path 
                      for file_path in files_to_check}
            
            for future in as_completed(futures):
                if not self.is_running:  # Abbruch wenn gestoppt
                    executor.shutdown(wait=False)
                    break
                future.result()  # Warte auf Completion
        
        # Finde Duplikate
        duplicate_count = 0
        for file_hash, files in hash_to_files.items():
            if len(files) > 1:
                self.duplicates[file_hash] = files
                duplicate_count += len(files) - 1  # Anzahl der Duplikate (ohne Original)
                self.logger.info(f"Duplikat gefunden: {len(files)} Dateien mit Hash {file_hash[:8]}...")
        
        if duplicate_count > 0:
            self.logger.info(f"Insgesamt {duplicate_count} Duplikate in {len(self.duplicates)} Gruppen gefunden")
        else:
            self.logger.info("Keine Duplikate gefunden.")
    
    def handle_duplicates(self) -> None:
        """Behandelt gefundene Duplikate"""
        if not self.handle_duplicates_enabled:
            self.logger.info("Duplikat-Behandlung übersprungen (deaktiviert)")
            return
        
        if not self.duplicates:
            self.logger.info("Keine Duplikate gefunden.")
            return
        
        self.logger.info(f"Behandle {len(self.duplicates)} Duplikat-Gruppen...")
        self.update_gui("📁 Behandle Duplikate...")
        
        duplicates_dir = self.target_dir / "_duplicates"
        if not self.dry_run:
            duplicates_dir.mkdir(parents=True, exist_ok=True)
        
        for file_hash, files in self.duplicates.items():
            original_file = files[0]  # Das erste wird als Original behalten
            self.logger.info(f"Original behalten: {original_file.name} (wird normal sortiert)")
            
            # Verschiebe nur die zusätzlichen Duplikate
            for i, duplicate_file in enumerate(files[1:], 1):
                if not self.dry_run:
                    duplicate_target = duplicates_dir / f"{duplicate_file.stem}_{i}{duplicate_file.suffix}"
                    shutil.move(str(duplicate_file), str(duplicate_target))
                    relative_path = duplicate_target.relative_to(self.target_dir)
                    self.logger.info(f"Duplikat verschoben: {duplicate_file.name} -> {relative_path}")
                else:
                    relative_path = f"_duplicates/{duplicate_file.stem}_{i}{duplicate_file.suffix}"
                    self.logger.info(f"[TESTLAUF] Würde Duplikat verschieben: {duplicate_file.name} -> {relative_path}")
    
    def sort_media(self) -> None:
        """Sortiert Medien nach Datum"""
        self.logger.info("Starte Mediensortierung...")
        self.update_gui("📂 Sortiere Medien...")
        
        # Sammle alle relevanten Dateien
        files_to_process = []
        for file_path in self.source_dir.rglob('*'):
            if (file_path.is_file() and 
                file_path.suffix.lower() in self.supported_formats):
                
                # Überspringe nur die zusätzlichen Duplikate (nicht das erste/Original)
                if self.handle_duplicates_enabled or self.ignore_duplicates:
                    is_additional_duplicate = False
                    for dup_files in self.duplicates.values():
                        # Das erste Element jeder Duplikat-Gruppe ist das "Original" und wird normal sortiert
                        if file_path in dup_files[1:]:  # Nur die zusätzlichen Duplikate überspringen
                            is_additional_duplicate = True
                            break
                    
                    if is_additional_duplicate:
                        continue
                
                files_to_process.append(file_path)
        
        total_files = len(files_to_process)
        self.logger.info(f"Verarbeite {total_files} Dateien...")
        
        if self.batch_processing and total_files > self.batch_size:
            self.logger.info(f"Batch-Verarbeitung aktiviert: {self.batch_size} Dateien pro Durchgang")
            self._process_files_in_batches(files_to_process)
        else:
            self._process_files_sequential(files_to_process)
    
    def _process_files_in_batches(self, files_to_process: List[Path]) -> None:
        """Verarbeitet Dateien in Batches"""
        total_files = len(files_to_process)
        
        for batch_start in range(0, total_files, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total_files)
            batch_files = files_to_process[batch_start:batch_end]
            
            batch_num = (batch_start // self.batch_size) + 1
            total_batches = (total_files + self.batch_size - 1) // self.batch_size
            
            self.logger.info(f"Verarbeite Batch {batch_num}/{total_batches} ({len(batch_files)} Dateien)")
            self.update_gui(f"📦 Batch {batch_num}/{total_batches} - {len(batch_files)} Dateien")
            
            # Prüfe ob Sortierung gestoppt wurde
            if not self.is_running:
                self.logger.info("Sortierung wurde durch Benutzer gestoppt")
                break
            
            self._process_files_sequential(batch_files, batch_start)
            
            # Kurze Pause zwischen Batches für GUI-Updates und Speicher-Cleanup
            import time
            time.sleep(0.1)
    
    def _process_files_sequential(self, files_to_process: List[Path], start_index: int = 0) -> None:
        """Verarbeitet Dateien sequenziell"""
        for i, file_path in enumerate(files_to_process, 1):
            try:
                # Prüfe ob Sortierung gestoppt wurde
                if not self.is_running:
                    self.logger.info("Sortierung wurde durch Benutzer gestoppt")
                    break
                
                actual_index = start_index + i
                self.update_gui(f"Verarbeite Datei {actual_index}: {file_path.name}")
                
                # Berechne Hash für Hash-Datenbank-Prüfung
                file_hash = None
                if self.use_hash_db:
                    file_hash = self.calculate_file_hash(file_path)
                    
                    # Prüfe ob Datei bereits in Datenbank
                    if file_hash and self.is_file_in_database(file_hash):
                        # Hole Informationen über die bereits gespeicherte Datei
                        existing_file_info = self.get_file_info_from_database(file_hash)
                        if existing_file_info:
                            # Bestimme Datum der aktuellen Datei
                            current_file_date, current_date_source = self.determine_date(file_path)
                            existing_file_date = existing_file_info['date_taken']
                            
                            # Prüfe ob die Daten unterschiedlich sind
                            if existing_file_date and current_file_date:
                                date_diff = abs((existing_file_date - current_file_date).days)
                                if date_diff > 0:  # Unterschiedliche Daten
                                    # Wähle das frühere Datum
                                    if current_file_date < existing_file_date:
                                        # Aktuelles Datum ist früher - verschiebe bereits sortierte Datei
                                        self.logger.warning(f"Duplikat-Datumskonflikt für {file_path.name}:")
                                        self.logger.warning(f"  Bereits in DB: {existing_file_info['file_name']} ({existing_file_date.strftime('%Y-%m-%d')})")
                                        self.logger.warning(f"  Aktuelle Datei: {file_path.name} ({current_file_date.strftime('%Y-%m-%d')})")
                                        self.logger.warning(f"  → Verwende früheres Datum: {current_file_date.strftime('%Y-%m-%d')}")
                                        
                                        # Verschiebe die bereits sortierte Datei zum neuen (früheren) Datum
                                        if self.move_existing_file_to_new_date(existing_file_info['file_path'], current_file_date, current_date_source):
                                            self.logger.info(f"Bereits sortierte Datei erfolgreich zum früheren Datum verschoben")
                                        
                                        # Erfasse Konflikt für Statistik
                                        self.duplicate_date_conflicts.append((file_path, existing_file_date.strftime('%Y-%m-%d'), current_file_date.strftime('%Y-%m-%d')))
                                        
                                        # Überspringe aktuelle Datei (da bereits sortierte Datei verschoben wurde)
                                        self.skipped_files.append(file_path)
                                        
                                        # Aktualisiere DB-Eintrag mit neuem Datum und Pfad
                                        if self.use_hash_db and not self.dry_run:
                                            new_target_path = self.create_target_path(current_file_date, file_path.name, current_date_source)
                                            self.add_file_to_database(file_path, file_hash, new_target_path, current_file_date, current_date_source)
                                        
                                        continue
                                    else:
                                        # Vorhandenes Datum ist früher - überspringe aktuelle Datei
                                        self.logger.warning(f"Duplikat-Datumskonflikt für {file_path.name}:")
                                        self.logger.warning(f"  Bereits in DB: {existing_file_info['file_name']} ({existing_file_date.strftime('%Y-%m-%d')})")
                                        self.logger.warning(f"  Aktuelle Datei: {file_path.name} ({current_file_date.strftime('%Y-%m-%d')})")
                                        self.logger.warning(f"  → Behalte früheres Datum: {existing_file_date.strftime('%Y-%m-%d')}")
                                        
                                        # Erfasse Konflikt für Statistik
                                        self.duplicate_date_conflicts.append((file_path, current_file_date.strftime('%Y-%m-%d'), existing_file_date.strftime('%Y-%m-%d')))
                                        
                                        self.skipped_files.append(file_path)
                                        continue
                                else:
                                    # Gleiche Daten - normal überspringen
                                    self.skipped_files.append(file_path)
                                    self.logger.info(f"Übersprungen (bereits in DB): {file_path.name}")
                                    continue
                            else:
                                # Normale Übersprungung wenn keine Datumsinformationen verfügbar
                                self.skipped_files.append(file_path)
                                self.logger.info(f"Übersprungen (bereits in DB): {file_path.name}")
                                continue
                        else:
                            # Fallback - normale Übersprungung
                            self.skipped_files.append(file_path)
                            self.logger.info(f"Übersprungen (bereits in DB): {file_path.name}")
                            continue
                
                # Bestimme Datum und Quelle (falls noch nicht bestimmt)
                if 'file_date' not in locals():
                    file_date, date_source = self.determine_date(file_path)
                
                # Erstelle Zielpfad
                target_path = self.create_target_path(file_date, file_path.name, date_source)
                
                # Erstelle Zielverzeichnis
                if not self.dry_run:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Behandle Namenskonflikte
                if target_path.exists():
                    counter = 1
                    stem = target_path.stem
                    suffix = target_path.suffix
                    while target_path.exists():
                        target_path = target_path.parent / f"{stem}_{counter}{suffix}"
                        counter += 1
                
                # Verschiebe oder kopiere Datei
                if not self.dry_run:
                    if self.copy_mode:
                        shutil.copy2(str(file_path), str(target_path))
                        action = "Kopiert"
                        action_icon = "📋"
                    else:
                        shutil.move(str(file_path), str(target_path))
                        action = "Verschoben"
                        action_icon = "📁"
                    
                    self.moved_files.append((file_path, target_path))
                    
                    # Zur Hash-Datenbank hinzufügen
                    if self.use_hash_db and file_hash:
                        self.add_file_to_database(file_path, file_hash, target_path, file_date, date_source)
                    
                    if date_source == "UNKNOWN":
                        self.unknown_date_files.append(file_path)
                        self.logger.info(f"{action} (unbekanntes Datum): {file_path.name} -> _unknown_date/")
                    elif date_source == "INVALID":
                        self.invalid_date_files.append(file_path)
                        self.logger.info(f"{action} (unrealistisches Datum): {file_path.name} -> _invalid_date/")
                    else:
                        # Zeige vollständiges Datum und kompletten Zielpfad
                        date_str = file_date.strftime('%Y-%m-%d')
                        relative_path = target_path.relative_to(self.target_dir)
                        self.logger.info(f"{action} ({date_source}) [{date_str}]: {file_path.name} -> {relative_path}")
                else:
                    action = "kopieren" if self.copy_mode else "verschieben"
                    if date_source == "UNKNOWN":
                        self.unknown_date_files.append(file_path)
                        self.logger.info(f"[TESTLAUF] Würde {action} (unbekanntes Datum): {file_path.name} -> _unknown_date/")
                    elif date_source == "INVALID":
                        self.invalid_date_files.append(file_path)
                        self.logger.info(f"[TESTLAUF] Würde {action} (unrealistisches Datum): {file_path.name} -> _invalid_date/")
                    else:
                        # Zeige vollständiges Datum und kompletten Zielpfad für Testlauf
                        date_str = file_date.strftime('%Y-%m-%d')
                        relative_path = target_path.relative_to(self.target_dir)
                        self.logger.info(f"[TESTLAUF] Würde {action} ({date_source}) [{date_str}]: {file_path.name} -> {relative_path}")
                
                # Lokale Variablen für nächste Iteration zurücksetzen
                if 'file_date' in locals():
                    del file_date, date_source
                
            except Exception as e:
                self.logger.error(f"Fehler bei {file_path}: {e}")
    
    def create_summary_report(self) -> None:
        """Erstellt Zusammenfassungsbericht"""
        report_path = self.target_dir / "sort_report.txt"
        
        if not self.dry_run:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("MEDIEN SORTIERUNG BERICHT\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Datum: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Quellverzeichnis: {self.source_dir}\n")
                f.write(f"Zielverzeichnis: {self.target_dir}\n\n")
                
                # Verarbeitungsoptionen
                f.write("VERARBEITUNGSOPTIONEN:\n")
                f.write("-" * 25 + "\n")
                f.write(f"Modus: {'Kopieren' if self.copy_mode else 'Verschieben'}\n")
                f.write(f"Sortierung: {'Nach Tagen' if self.sort_by_day else 'Nach Monaten'}\n")
                
                # Medientypen
                selected_types = []
                if self.process_images:
                    selected_types.append("Bilder")
                if self.process_videos:
                    selected_types.append("Videos")
                if self.process_audio:
                    selected_types.append("Audio")
                f.write(f"Medientypen: {', '.join(selected_types)}\n")
                
                f.write(f"Hash-Datenbank: {'Aktiviert' if self.use_hash_db else 'Deaktiviert'}\n")
                f.write(f"Datumsvalidierung: {'Aktiviert' if self.validate_dates else 'Deaktiviert'}")
                if self.validate_dates:
                    f.write(f" (ab {self.earliest_valid_year})")
                f.write("\n")
                f.write(f"Turbo-Duplikaterkennung: {'Aktiviert' if self.turbo_duplicate_detection else 'Deaktiviert'}\n")
                
                # Duplikat-Modus
                if self.handle_duplicates_enabled:
                    f.write(f"Duplikat-Behandlung: Verschieben\n")
                elif self.ignore_duplicates:
                    f.write(f"Duplikat-Behandlung: Ignorieren\n")
                else:
                    f.write(f"Duplikat-Behandlung: Deaktiviert\n")
                
                f.write(f"Batch-Verarbeitung: {'Aktiviert' if self.batch_processing else 'Deaktiviert'}")
                if self.batch_processing:
                    f.write(f" (Batch-Größe: {self.batch_size})")
                f.write("\n\n")
                
                action_text = "Kopierte Dateien" if self.copy_mode else "Verschobene Dateien"
                f.write(f"{action_text}: {len(self.moved_files)}\n")
                
                if self.handle_duplicates_enabled:
                    f.write(f"Gefundene Duplikate: {len(self.duplicates)}\n")
                else:
                    f.write(f"Duplikat-Behandlung: Deaktiviert\n")
                
                f.write(f"Dateien mit unbekanntem Datum: {len(self.unknown_date_files)}\n")
                f.write(f"Dateien mit unrealistischem Datum: {len(self.invalid_date_files)}\n")
                f.write(f"Übersprungene Dateien (bereits in DB): {len(self.skipped_files)}\n")
                f.write(f"Duplikat-Datumskonflikte: {len(self.duplicate_date_conflicts)}\n\n")
                
                # Hash-Datenbank-Statistiken
                if self.use_hash_db:
                    db_stats = self.get_database_stats()
                    if db_stats:
                        f.write("HASH-DATENBANK STATISTIKEN:\n")
                        f.write("-" * 30 + "\n")
                        f.write(f"Gesamt in DB: {db_stats.get('total_files', 0)} Dateien\n")
                        f.write(f"Eindeutige Hashes: {db_stats.get('unique_hashes', 0)}\n")
                        f.write(f"Potentielle Duplikate: {db_stats.get('potential_duplicates', 0)}\n\n")
                
                if self.handle_duplicates_enabled and self.duplicates:
                    f.write("DUPLIKATE:\n")
                    f.write("-" * 20 + "\n")
                    for file_hash, files in self.duplicates.items():
                        f.write(f"Hash {file_hash[:8]}: {len(files)} Dateien\n")
                        for file in files:
                            f.write(f"  - {file}\n")
                        f.write("\n")
                
                if self.unknown_date_files:
                    f.write("DATEIEN MIT UNBEKANNTEM DATUM:\n")
                    f.write("-" * 30 + "\n")
                    for file in self.unknown_date_files:
                        f.write(f"  - {file}\n")
                    f.write("\n")
                
                if self.invalid_date_files:
                    f.write("DATEIEN MIT UNREALISTISCHEM DATUM:\n")
                    f.write("-" * 30 + "\n")
                    for file in self.invalid_date_files:
                        f.write(f"  - {file}\n")
                    f.write("\n")
                
                if self.skipped_files:
                    f.write("ÜBERSPRUNGENE DATEIEN (BEREITS IN DB):\n")
                    f.write("-" * 35 + "\n")
                    for file in self.skipped_files:
                        f.write(f"  - {file}\n")
                    f.write("\n")
                
                if self.duplicate_date_conflicts:
                    f.write("DUPLIKAT-DATUMSKONFLIKTE:\n")
                    f.write("-" * 25 + "\n")
                    for file_path, old_date_str, new_date_str in self.duplicate_date_conflicts:
                        f.write(f"  - {file_path.name}:")
                        f.write(f"  Alt: {old_date_str}, Neues: {new_date_str}\n")
                    f.write("\n")
                
                action_header = "KOPIERTE DATEIEN" if self.copy_mode else "VERSCHOBENE DATEIEN"
                f.write(f"{action_header}:\n")
                f.write("-" * 20 + "\n")
                for source, target in self.moved_files:
                    f.write(f"{source} -> {target}\n")
        
        self.logger.info(f"Bericht erstellt: {report_path}")
    
    def run(self) -> None:
        """Führt den kompletten Sortiervorgang aus"""
        self.logger.info(f"Starte Mediensortierung von {self.source_dir} nach {self.target_dir}")
        
        if not self.source_dir.exists():
            self.logger.error(f"Quellverzeichnis existiert nicht: {self.source_dir}")
            return
        
        if not self.dry_run:
            self.target_dir.mkdir(parents=True, exist_ok=True)
        
        # Log der gewählten Medientypen
        selected_types = []
        if self.process_images:
            selected_types.append("Bilder")
        if self.process_raw:
            selected_types.append("RAW")
        if self.process_videos:
            selected_types.append("Videos")
        if self.process_audio:
            selected_types.append("Audio")
        
        self.logger.info(f"Gewählte Medientypen: {', '.join(selected_types)}")
        
        try:
            # Hash-Datenbank initialisieren
            self.init_hash_database()
            
            # Schritt 1: Duplikate finden
            self.find_duplicates()
            
            # Schritt 2: Duplikate behandeln
            if self.handle_duplicates_enabled or self.ignore_duplicates: # Duplikat-Erkennung ist aktiv
                if self.ignore_duplicates:
                    self.logger.info("Duplikat-Modus: Ignorieren (nur eine Kopie sortieren, Rest bleibt unberührt)")
                else:
                    self.handle_duplicates()
            
            # Schritt 3: Medien sortieren
            self.sort_media()
            
            # Schritt 4: Bericht erstellen
            if not self.dry_run:
                self.create_summary_report()
            
            self.logger.info("Sortierung abgeschlossen!")
            
        finally:
            # Hash-Datenbank schließen
            self.close_hash_database()

class HashManagerWindow:
    """Hash-Datenbank-Manager als separates Fenster"""
    
    def __init__(self, parent, db_path):
        self.db_path = db_path
        self.db = None
        
        # Neues Fenster erstellen
        self.window = tk.Toplevel(parent)
        self.window.title("Hash-Datenbank Manager")
        self.window.geometry("1000x950")
        self.window.minsize(950, 700)
        
        # Fenster zentrieren
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - self.window.winfo_width()) // 2
        y = (self.window.winfo_screenheight() - self.window.winfo_height()) // 2
        self.window.geometry(f"+{x}+{y}")
        
        self.setup_gui()
        self.connect_database()
        self.refresh_stats()
        self.show_all_entries()
    
    def setup_gui(self):
        """Erstellt die GUI für den Hash-Manager"""
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Titel
        title_label = ttk.Label(main_frame, text="🔢 Hash-Datenbank Manager", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Datenbank-Pfad anzeigen
        path_frame = ttk.LabelFrame(main_frame, text="Datenbank", padding="10")
        path_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(path_frame, text=f"📂 {self.db_path}").pack(anchor=tk.W)
        
        # Statistiken
        self.stats_frame = ttk.LabelFrame(main_frame, text="Statistiken", padding="10")
        self.stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Aktionen
        actions_frame = ttk.LabelFrame(main_frame, text="Aktionen", padding="10")
        actions_frame.pack(fill=tk.X, pady=(0, 10))
        
        buttons_frame = ttk.Frame(actions_frame)
        buttons_frame.pack(fill=tk.X)
        
        ttk.Button(buttons_frame, text="📊 Statistiken aktualisieren", 
                  command=self.refresh_stats).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(buttons_frame, text="📋 Alle Einträge", 
                  command=self.show_all_entries).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(buttons_frame, text="🔍 Duplikate prüfen", 
                  command=self.show_duplicates).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(buttons_frame, text="🧹 Aufräumen", 
                  command=self.cleanup_missing).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(buttons_frame, text="📄 CSV Export", 
                  command=self.export_csv).pack(side=tk.LEFT, padx=5)
        
        # Zweite Zeile für Bearbeitungsfunktionen
        edit_buttons_frame = ttk.Frame(actions_frame)
        edit_buttons_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(edit_buttons_frame, text="🗑️ Auswahl löschen", 
                  command=self.delete_selected).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(edit_buttons_frame, text="📝 Eintrag bearbeiten", 
                  command=self.edit_selected).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(edit_buttons_frame, text="🔄 Pfad aktualisieren", 
                  command=self.update_path).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(edit_buttons_frame, text="➕ Manuell hinzufügen", 
                  command=self.add_manual_entry).pack(side=tk.LEFT, padx=5)
        
        # Suchergebnisse/Output
        self.results_frame = ttk.LabelFrame(main_frame, text="Alle Einträge", padding="5")
        self.results_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Treeview für Ergebnisse
        columns = ('Dateiname', 'Pfad', 'Größe', 'Datum', 'Quelle')
        self.tree = ttk.Treeview(self.results_frame, columns=columns, show='headings', height=20)
        
        # Spalten konfigurieren
        self.tree.heading('Dateiname', text='Dateiname')
        self.tree.heading('Pfad', text='Pfad')
        self.tree.heading('Größe', text='Größe (KB)')
        self.tree.heading('Datum', text='Aufnahmedatum')
        self.tree.heading('Quelle', text='Datumsquelle')
        
        self.tree.column('Dateiname', width=180)
        self.tree.column('Pfad', width=350)
        self.tree.column('Größe', width=90)
        self.tree.column('Datum', width=140)
        self.tree.column('Quelle', width=100)
        
        # Scrollbar für Treeview
        scrollbar = ttk.Scrollbar(self.results_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Suche-Frame
        search_frame = ttk.LabelFrame(main_frame, text="Suche", padding="10")
        search_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Dateiname-Suche
        name_frame = ttk.Frame(search_frame)
        name_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(name_frame, text="Dateiname:").pack(side=tk.LEFT)
        self.search_name = tk.StringVar()
        name_entry = ttk.Entry(name_frame, textvariable=self.search_name, width=30)
        name_entry.pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(name_frame, text="🔍 Suchen", 
                  command=self.search_by_name).pack(side=tk.LEFT)
        
        # Datum-Suche
        date_frame = ttk.Frame(search_frame)
        date_frame.pack(fill=tk.X)
        
        ttk.Label(date_frame, text="Von:").pack(side=tk.LEFT)
        self.search_date_start = tk.StringVar()
        ttk.Entry(date_frame, textvariable=self.search_date_start, width=12).pack(side=tk.LEFT, padx=(5, 5))
        
        ttk.Label(date_frame, text="Bis:").pack(side=tk.LEFT, padx=(10, 0))
        self.search_date_end = tk.StringVar()
        ttk.Entry(date_frame, textvariable=self.search_date_end, width=12).pack(side=tk.LEFT, padx=(5, 5))
        
        ttk.Button(date_frame, text="🔍 Datumssuche", 
                  command=self.search_by_date).pack(side=tk.LEFT)
        
        ttk.Label(date_frame, text="(Format: YYYY-MM-DD)", font=('Arial', 8)).pack(side=tk.LEFT, padx=(10, 0))
    
    def connect_database(self):
        """Verbindet zur Datenbank"""
        try:
            self.db = sqlite3.connect(str(self.db_path))
            self.db.row_factory = sqlite3.Row
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Verbinden zur Datenbank:\n{e}")
    
    def update_results_title(self, title):
        """Aktualisiert den Titel des Ergebnisbereichs"""
        self.results_frame.config(text=title)
    
    def show_all_entries(self):
        """Zeigt alle Einträge an"""
        if not self.db:
            return
        
        # Leere Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            cursor = self.db.cursor()
            cursor.execute('''
                SELECT file_name, file_path, file_size, date_taken, date_source
                FROM media_hashes 
                ORDER BY date_taken DESC, file_name
            ''')
            
            results = cursor.fetchall()
            
            for row in results:
                size_kb = round(row['file_size'] / 1024, 1) if row['file_size'] else 0
                
                self.tree.insert('', tk.END, values=(
                    row['file_name'],
                    row['file_path'],
                    size_kb,
                    row['date_taken'] or '',
                    row['date_source'] or ''
                ))
            
            self.update_results_title(f"📊 Alle Einträge ({len(results)})")
            
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Laden der Einträge:\n{e}")
    
    def refresh_stats(self):
        """Aktualisiert Statistiken"""
        if not self.db:
            return
        
        self.update_results_title("📊 Alle Einträge")
        
        try:
            cursor = self.db.cursor()
            
            # Grundstatistiken
            cursor.execute('SELECT COUNT(*) as total FROM media_hashes')
            total_files = cursor.fetchone()['total']
            
            cursor.execute('SELECT COUNT(DISTINCT file_hash) as unique_count FROM media_hashes')
            unique_hashes = cursor.fetchone()['unique_count']
            
            # Duplikate
            cursor.execute('''
                SELECT COUNT(*) as groups FROM (
                    SELECT file_hash FROM media_hashes 
                    GROUP BY file_hash 
                    HAVING COUNT(*) > 1
                )
            ''')
            duplicate_groups = cursor.fetchone()['groups']
            
            total_duplicates = total_files - unique_hashes
            
            # Datumsbereiche
            cursor.execute('''
                SELECT MIN(date_taken) as earliest, MAX(date_taken) as latest 
                FROM media_hashes 
                WHERE date_taken IS NOT NULL
            ''')
            date_range = cursor.fetchone()
            
            # Stats anzeigen
            for widget in self.stats_frame.winfo_children():
                widget.destroy()
            
            stats_text = f"📊 Gesamt Dateien: {total_files}"
            
            # Duplikate nur anzeigen wenn welche vorhanden sind
            if total_duplicates > 0:
                stats_text += f"\n🔗 Eindeutige Hashes: {unique_hashes}"
                stats_text += f"\n🔄 Duplikat-Gruppen: {duplicate_groups}"
                stats_text += f"\n📁 Gesamt Duplikate: {total_duplicates}"
            else:
                stats_text += f"\n✅ Alle Dateien eindeutig (keine Duplikate)"
            
            if date_range['earliest'] and date_range['latest']:
                try:
                    # Formatiere Datum benutzerfreundlich
                    earliest = datetime.fromisoformat(date_range['earliest'].replace('T', ' ').split('.')[0])
                    latest = datetime.fromisoformat(date_range['latest'].replace('T', ' ').split('.')[0])
                    
                    earliest_str = earliest.strftime('%d.%m.%Y')
                    latest_str = latest.strftime('%d.%m.%Y')
                    
                    # Zeige nur unterschiedliche Daten
                    if earliest_str == latest_str:
                        stats_text += f"\n📅 Zeitraum: {earliest_str}"
                    else:
                        stats_text += f"\n📅 Zeitraum: {earliest_str} - {latest_str}"
                except Exception:
                    # Fallback für ungültige Datumsformate
                    stats_text += f"\n📅 Zeitraum: {date_range['earliest'][:10]} - {date_range['latest'][:10]}"
            
            ttk.Label(self.stats_frame, text=stats_text, font=('Arial', 10)).pack(anchor=tk.W)
            
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Laden der Statistiken:\n{e}")
    
    def show_duplicates(self):
        """Zeigt Duplikate an"""
        if not self.db:
            return
        
        # Leere Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.update_results_title("🔄 Duplikate")
        
        try:
            cursor = self.db.cursor()
            cursor.execute('''
                SELECT file_hash, file_name, file_path, file_size, date_taken, date_source
                FROM media_hashes 
                WHERE file_hash IN (
                    SELECT file_hash 
                    FROM media_hashes 
                    GROUP BY file_hash 
                    HAVING COUNT(*) > 1
                )
                ORDER BY file_hash, date_added
            ''')
            
            results = cursor.fetchall()
            current_hash = None
            
            for row in results:
                # Größe in KB umrechnen
                size_kb = round(row['file_size'] / 1024, 1) if row['file_size'] else 0
                
                # Verschiedene Farben für verschiedene Hash-Gruppen
                tags = []
                if row['file_hash'] != current_hash:
                    current_hash = row['file_hash']
                    tags = ['new_group']
                
                self.tree.insert('', tk.END, values=(
                    row['file_name'],
                    row['file_path'],
                    size_kb,
                    row['date_taken'] or '',
                    row['date_source'] or ''
                ), tags=tags)
            
            # Style für neue Gruppen
            self.tree.tag_configure('new_group', background='#e6f3ff')
            
            if len(results) == 0:
                self.update_results_title("✅ Keine Duplikate gefunden")
                # Zeige eine informative Nachricht im Tree
                self.tree.insert('', tk.END, values=(
                    "✅ Keine Duplikate",
                    "Die Datenbank ist bereits bereinigt",
                    "---",
                    "---",
                    "---"
                ))
                messagebox.showinfo("Duplikate", "Keine Duplikate gefunden!\n\nDie Datenbank ist bereits bereinigt.")
            else:
                self.update_results_title(f"🔄 Duplikate ({len(results)})")
                messagebox.showinfo("Duplikate", f"{len(results)} Duplikate gefunden!")
            
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Suchen von Duplikaten:\n{e}")
    
    def search_by_name(self):
        """Sucht nach Dateinamen"""
        pattern = self.search_name.get().strip()
        if not pattern:
            messagebox.showwarning("Achtung", "Bitte Suchbegriff eingeben!")
            return
        
        self.update_results_title(f"🔍 Suche: '{pattern}'")
        self.search_files("file_name LIKE ?", (f'%{pattern}%',), f"Dateiname: '{pattern}'")
    
    def search_by_date(self):
        """Sucht nach Datumsbereich"""
        start_date = self.search_date_start.get().strip()
        end_date = self.search_date_end.get().strip()
        
        if not start_date or not end_date:
            messagebox.showwarning("Achtung", "Bitte Start- und Enddatum eingeben!")
            return
        
        self.update_results_title(f"🗓️ Zeitraum: {start_date} - {end_date}")
        self.search_files("date_taken BETWEEN ? AND ?", (start_date, end_date), 
                         f"Zeitraum: {start_date} bis {end_date}")
    
    def search_files(self, where_clause, params, search_desc):
        """Allgemeine Suchfunktion"""
        if not self.db:
            return
        
        # Leere Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            cursor = self.db.cursor()
            cursor.execute(f'''
                SELECT file_name, file_path, file_size, date_taken, date_source
                FROM media_hashes 
                WHERE {where_clause}
                ORDER BY date_taken, file_name
            ''', params)
            
            results = cursor.fetchall()
            
            for row in results:
                size_kb = round(row['file_size'] / 1024, 1) if row['file_size'] else 0
                
                self.tree.insert('', tk.END, values=(
                    row['file_name'],
                    row['file_path'],
                    size_kb,
                    row['date_taken'] or '',
                    row['date_source'] or ''
                ))
            
            # Aktualisiere den Titel falls nicht bereits gesetzt
            if not self.results_frame.cget('text').startswith(('🔍', '🗓️')):
                self.update_results_title(f"🔍 Suchergebnisse ({len(results)})")
            
            messagebox.showinfo("Suchergebnisse", f"{len(results)} Dateien gefunden!\nSuche: {search_desc}")
            
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler bei der Suche:\n{e}")
    
    def cleanup_missing(self):
        """Entfernt Einträge für nicht existierende Dateien"""
        if not self.db:
            return
        
        if not messagebox.askyesno("Bestätigung", 
                                  "Möchten Sie nicht existierende Dateien aus der Datenbank entfernen?\n\nDies kann nicht rückgängig gemacht werden!"):
            return
        
        try:
            cursor = self.db.cursor()
            cursor.execute('SELECT id, file_path FROM media_hashes')
            all_files = cursor.fetchall()
            
            removed_count = 0
            for file_record in all_files:
                if not Path(file_record['file_path']).exists():
                    cursor.execute('DELETE FROM media_hashes WHERE id = ?', (file_record['id'],))
                    removed_count += 1
            
            self.db.commit()
            messagebox.showinfo("Aufräumen", f"{removed_count} nicht existierende Einträge entfernt!")
            self.refresh_stats()
            
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Aufräumen:\n{e}")
    
    def export_csv(self):
        """Exportiert Datenbank zu CSV"""
        if not self.db:
            return
        
        from tkinter import filedialog
        import csv
        
        filename = filedialog.asksaveasfilename(
            title="CSV Export speichern",
            defaultextension=".csv",
            filetypes=[("CSV Dateien", "*.csv"), ("Alle Dateien", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            cursor = self.db.cursor()
            cursor.execute('''
                SELECT file_hash, file_name, file_path, file_size, 
                       date_added, date_taken, date_source, media_type
                FROM media_hashes 
                ORDER BY date_taken, file_name
            ''')
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Hash', 'Dateiname', 'Pfad', 'Größe (Bytes)', 
                               'Hinzugefügt', 'Aufgenommen', 'Datumsquelle', 'Medientyp'])
                
                for row in cursor.fetchall():
                    writer.writerow(row)
            
            messagebox.showinfo("Export", f"Datenbank erfolgreich exportiert:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim CSV-Export:\n{e}")
    
    def delete_selected(self):
        """Löscht ausgewählte Einträge"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Auswahl", "Bitte wählen Sie Einträge zum Löschen aus!")
            return
        
        if not messagebox.askyesno("Bestätigung", 
                                  f"Möchten Sie {len(selected_items)} Einträge aus der Datenbank löschen?\n\nDies kann nicht rückgängig gemacht werden!"):
            return
        
        try:
            cursor = self.db.cursor()
            deleted_count = 0
            
            for item in selected_items:
                values = self.tree.item(item, 'values')
                file_path = values[1]  # Pfad ist die zweite Spalte
                
                cursor.execute('DELETE FROM media_hashes WHERE file_path = ?', (file_path,))
                if cursor.rowcount > 0:
                    deleted_count += 1
                    self.tree.delete(item)
            
            self.db.commit()
            messagebox.showinfo("Gelöscht", f"{deleted_count} Einträge erfolgreich gelöscht!")
            self.refresh_stats()
            
            # Aktualisiere Anzeige
            remaining_count = len(self.tree.get_children())
            current_title = self.results_frame.cget('text')
            if "(" in current_title:
                title_base = current_title.split("(")[0].strip()
                self.update_results_title(f"{title_base} ({remaining_count})")
            
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Löschen:\n{e}")
    
    def edit_selected(self):
        """Bearbeitet ausgewählten Eintrag"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Auswahl", "Bitte wählen Sie einen Eintrag zum Bearbeiten aus!")
            return
        
        if len(selected_items) > 1:
            messagebox.showwarning("Auswahl", "Bitte wählen Sie nur einen Eintrag zum Bearbeiten aus!")
            return
        
        item = selected_items[0]
        values = self.tree.item(item, 'values')
        
        # Erstelle Bearbeitungsfenster
        edit_window = tk.Toplevel(self.window)
        edit_window.title("Eintrag bearbeiten")
        edit_window.geometry("500x400")
        edit_window.resizable(False, False)
        
        # Zentriere das Fenster
        edit_window.update_idletasks()
        x = (edit_window.winfo_screenwidth() - edit_window.winfo_width()) // 2
        y = (edit_window.winfo_screenheight() - edit_window.winfo_height()) // 2
        edit_window.geometry(f"+{x}+{y}")
        
        frame = ttk.Frame(edit_window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Hole vollständige Daten aus der Datenbank
        try:
            cursor = self.db.cursor()
            cursor.execute('''
                SELECT file_hash, file_name, file_path, file_size, 
                       date_added, date_taken, date_source, media_type
                FROM media_hashes WHERE file_path = ?
            ''', (values[1],))
            
            db_row = cursor.fetchone()
            if not db_row:
                messagebox.showerror("Fehler", "Eintrag nicht in Datenbank gefunden!")
                edit_window.destroy()
                return
            
            # Eingabefelder
            ttk.Label(frame, text="Dateiname:").grid(row=0, column=0, sticky=tk.W, pady=2)
            name_var = tk.StringVar(value=db_row['file_name'])
            ttk.Entry(frame, textvariable=name_var, width=50).grid(row=0, column=1, pady=2, padx=(10, 0))
            
            ttk.Label(frame, text="Pfad:").grid(row=1, column=0, sticky=tk.W, pady=2)
            path_var = tk.StringVar(value=db_row['file_path'])
            ttk.Entry(frame, textvariable=path_var, width=50).grid(row=1, column=1, pady=2, padx=(10, 0))
            
            ttk.Label(frame, text="Aufnahmedatum:").grid(row=2, column=0, sticky=tk.W, pady=2)
            date_var = tk.StringVar(value=db_row['date_taken'] or '')
            ttk.Entry(frame, textvariable=date_var, width=50).grid(row=2, column=1, pady=2, padx=(10, 0))
            ttk.Label(frame, text="Format: YYYY-MM-DD HH:MM:SS", font=('Arial', 8)).grid(row=3, column=1, sticky=tk.W, padx=(10, 0))
            
            ttk.Label(frame, text="Datumsquelle:").grid(row=4, column=0, sticky=tk.W, pady=2)
            source_var = tk.StringVar(value=db_row['date_source'] or '')
            source_combo = ttk.Combobox(frame, textvariable=source_var, 
                                       values=["FILENAME", "EXIF", "METADATA", "UNKNOWN", "INVALID"], 
                                       width=47)
            source_combo.grid(row=4, column=1, pady=2, padx=(10, 0))
            
            ttk.Label(frame, text="Medientyp:").grid(row=5, column=0, sticky=tk.W, pady=2)
            media_var = tk.StringVar(value=db_row['media_type'] or '')
            media_combo = ttk.Combobox(frame, textvariable=media_var, 
                                      values=["IMAGE", "VIDEO", "AUDIO"], 
                                      width=47)
            media_combo.grid(row=5, column=1, pady=2, padx=(10, 0))
            
            # Schreibgeschützte Felder
            ttk.Label(frame, text="Hash:").grid(row=6, column=0, sticky=tk.W, pady=2)
            ttk.Label(frame, text=db_row['file_hash'][:16] + "...", font=('Courier', 8)).grid(row=6, column=1, sticky=tk.W, pady=2, padx=(10, 0))
            
            ttk.Label(frame, text="Dateigröße:").grid(row=7, column=0, sticky=tk.W, pady=2)
            size_kb = round(db_row['file_size'] / 1024, 1) if db_row['file_size'] else 0
            ttk.Label(frame, text=f"{size_kb} KB").grid(row=7, column=1, sticky=tk.W, pady=2, padx=(10, 0))
            
            ttk.Label(frame, text="Hinzugefügt:").grid(row=8, column=0, sticky=tk.W, pady=2)
            ttk.Label(frame, text=db_row['date_added'] or '').grid(row=8, column=1, sticky=tk.W, pady=2, padx=(10, 0))
            
            # Buttons
            button_frame = ttk.Frame(frame)
            button_frame.grid(row=9, column=0, columnspan=2, pady=20)
            
            def save_changes():
                try:
                    # Validiere Datum falls angegeben
                    date_taken = None
                    if date_var.get().strip():
                        try:
                            date_taken = datetime.fromisoformat(date_var.get().strip()).isoformat()
                        except ValueError:
                            messagebox.showerror("Fehler", "Ungültiges Datumsformat! Verwenden Sie: YYYY-MM-DD HH:MM:SS")
                            return
                    
                    # Aktualisiere Datenbank
                    cursor.execute('''
                        UPDATE media_hashes 
                        SET file_name = ?, file_path = ?, date_taken = ?, 
                            date_source = ?, media_type = ?
                        WHERE file_hash = ?
                    ''', (
                        name_var.get().strip(),
                        path_var.get().strip(),
                        date_taken,
                        source_var.get().strip(),
                        media_var.get().strip(),
                        db_row['file_hash']
                    ))
                    
                    self.db.commit()
                    messagebox.showinfo("Erfolg", "Eintrag erfolgreich aktualisiert!")
                    edit_window.destroy()
                    
                    # Aktualisiere Treeview
                    self.tree.item(item, values=(
                        name_var.get().strip(),
                        path_var.get().strip(),
                        size_kb,
                        date_var.get().strip(),
                        source_var.get().strip()
                    ))
                    
                except Exception as e:
                    messagebox.showerror("Fehler", f"Fehler beim Speichern:\n{e}")
            
            ttk.Button(button_frame, text="💾 Speichern", command=save_changes).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="❌ Abbrechen", command=edit_window.destroy).pack(side=tk.LEFT, padx=5)
            
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Laden der Daten:\n{e}")
            edit_window.destroy()
    
    def update_path(self):
        """Aktualisiert Pfade für ausgewählte Einträge"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Auswahl", "Bitte wählen Sie Einträge aus!")
            return
        
        # Frage nach neuem Basispfad
        new_base_path = filedialog.askdirectory(title="Neuen Basispfad für Dateien auswählen")
        if not new_base_path:
            return
        
        try:
            cursor = self.db.cursor()
            updated_count = 0
            
            for item in selected_items:
                values = self.tree.item(item, 'values')
                old_path = values[1]
                filename = values[0]
                
                # Erstelle neuen Pfad
                new_path = str(Path(new_base_path) / filename)
                
                # Aktualisiere Datenbank
                cursor.execute('UPDATE media_hashes SET file_path = ? WHERE file_path = ?', 
                              (new_path, old_path))
                
                if cursor.rowcount > 0:
                    updated_count += 1
                    # Aktualisiere Treeview
                    new_values = list(values)
                    new_values[1] = new_path
                    self.tree.item(item, values=new_values)
            
            self.db.commit()
            messagebox.showinfo("Aktualisiert", f"{updated_count} Pfade erfolgreich aktualisiert!")
            
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Aktualisieren der Pfade:\n{e}")
    
    def add_manual_entry(self):
        """Fügt manuell einen neuen Eintrag hinzu"""
        # Erstelle Eingabefenster
        add_window = tk.Toplevel(self.window)
        add_window.title("Manuellen Eintrag hinzufügen")
        add_window.geometry("500x350")
        add_window.resizable(False, False)
        
        # Zentriere das Fenster
        add_window.update_idletasks()
        x = (add_window.winfo_screenwidth() - add_window.winfo_width()) // 2
        y = (add_window.winfo_screenheight() - add_window.winfo_height()) // 2
        add_window.geometry(f"+{x}+{y}")
        
        frame = ttk.Frame(add_window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Eingabefelder
        ttk.Label(frame, text="Dateiname:").grid(row=0, column=0, sticky=tk.W, pady=2)
        name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=name_var, width=50).grid(row=0, column=1, pady=2, padx=(10, 0))
        
        ttk.Label(frame, text="Pfad:").grid(row=1, column=0, sticky=tk.W, pady=2)
        path_var = tk.StringVar()
        path_entry = ttk.Entry(frame, textvariable=path_var, width=50)
        path_entry.grid(row=1, column=1, pady=2, padx=(10, 0))
        
        # Datei-Browser Button
        def browse_file():
            filename = filedialog.askopenfilename(title="Datei auswählen")
            if filename:
                path_var.set(filename)
                name_var.set(Path(filename).name)
        
        ttk.Button(frame, text="📁 Durchsuchen", command=browse_file).grid(row=2, column=1, sticky=tk.W, pady=2, padx=(10, 0))
        
        ttk.Label(frame, text="Aufnahmedatum:").grid(row=3, column=0, sticky=tk.W, pady=2)
        date_var = tk.StringVar()
        ttk.Entry(frame, textvariable=date_var, width=50).grid(row=3, column=1, pady=2, padx=(10, 0))
        ttk.Label(frame, text="Format: YYYY-MM-DD HH:MM:SS", font=('Arial', 8)).grid(row=4, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(frame, text="Datumsquelle:").grid(row=5, column=0, sticky=tk.W, pady=2)
        source_var = tk.StringVar(value="MANUAL")
        source_combo = ttk.Combobox(frame, textvariable=source_var, 
                                   values=["MANUAL", "FILENAME", "EXIF", "METADATA", "UNKNOWN"], 
                                   width=47)
        source_combo.grid(row=5, column=1, pady=2, padx=(10, 0))
        
        ttk.Label(frame, text="Medientyp:").grid(row=6, column=0, sticky=tk.W, pady=2)
        media_var = tk.StringVar(value="IMAGE")
        media_combo = ttk.Combobox(frame, textvariable=media_var, 
                                  values=["IMAGE", "VIDEO", "AUDIO"], 
                                  width=47)
        media_combo.grid(row=6, column=1, pady=2, padx=(10, 0))
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=7, column=0, columnspan=2, pady=20)
        
        def add_entry():
            try:
                filename = name_var.get().strip()
                filepath = path_var.get().strip()
                
                if not filename or not filepath:
                    messagebox.showerror("Fehler", "Dateiname und Pfad sind erforderlich!")
                    return
                
                # Prüfe ob Datei existiert
                if not Path(filepath).exists():
                    if not messagebox.askyesno("Warnung", 
                                              "Die Datei existiert nicht am angegebenen Pfad. Trotzdem hinzufügen?"):
                        return
                
                # Berechne Hash falls Datei existiert
                file_hash = "manual_" + hashlib.md5(filepath.encode()).hexdigest()[:16]
                if Path(filepath).exists():
                    try:
                        # Verwende eine vereinfachte Hash-Berechnung
                        hash_md5 = hashlib.md5()
                        with open(filepath, "rb") as f:
                            chunk = f.read(8192)  # Erste 8KB
                            if chunk:
                                hash_md5.update(chunk)
                        file_hash = hash_md5.hexdigest()
                    except Exception:
                        pass  # Verwende manuellen Hash
                
                # Validiere Datum falls angegeben
                date_taken = None
                if date_var.get().strip():
                    try:
                        date_taken = datetime.fromisoformat(date_var.get().strip()).isoformat()
                    except ValueError:
                        messagebox.showerror("Fehler", "Ungültiges Datumsformat! Verwenden Sie: YYYY-MM-DD HH:MM:SS")
                        return
                
                # Hole Dateigröße
                file_size = 0
                if Path(filepath).exists():
                    file_size = Path(filepath).stat().st_size
                
                # Prüfe ob Hash bereits existiert
                cursor = self.db.cursor()
                cursor.execute('SELECT COUNT(*) FROM media_hashes WHERE file_hash = ?', (file_hash,))
                if cursor.fetchone()[0] > 0:
                    if not messagebox.askyesno("Duplikat", 
                                              "Ein Eintrag mit diesem Hash existiert bereits. Trotzdem hinzufügen?"):
                        return
                
                # Füge zur Datenbank hinzu
                cursor.execute('''
                    INSERT INTO media_hashes 
                    (file_hash, file_name, file_path, file_size, media_type, 
                     date_added, date_taken, date_source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    file_hash,
                    filename,
                    filepath,
                    file_size,
                    media_var.get().strip(),
                    datetime.now().isoformat(),
                    date_taken,
                    source_var.get().strip()
                ))
                
                self.db.commit()
                messagebox.showinfo("Erfolg", "Eintrag erfolgreich hinzugefügt!")
                add_window.destroy()
                self.refresh_stats()
                
                # Aktualisiere Anzeige falls gerade "Alle Einträge" angezeigt wird
                if self.results_frame.cget('text').startswith("📊"):
                    self.show_all_entries()
                
            except Exception as e:
                messagebox.showerror("Fehler", f"Fehler beim Hinzufügen:\n{e}")
        
        ttk.Button(button_frame, text="➕ Hinzufügen", command=add_entry).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="❌ Abbrechen", command=add_window.destroy).pack(side=tk.LEFT, padx=5)

def main():
    root = tk.Tk()
    app = ImageSorterGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 