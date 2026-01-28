#!/usr/bin/env python3
"""
Media Timeline Viewer - Interactive horizontal timeline for sorted media
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import subprocess
from pathlib import Path
from datetime import datetime
import threading
import json
from concurrent.futures import ThreadPoolExecutor
import queue
import time

# Import i18n
from i18n import t, get_language, set_language, get_available_languages

# Try to import OpenCV for video thumbnails
try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    print(t("opencv_not_available"))

class TimelineViewer:
    def __init__(self, root):
        self.root = root
        self.root.title(t("title_timeline"))
        self.root.geometry("1400x800")
        self.root.configure(bg='#2c3e50')

        # Variablen
        self.base_dirs = []  # Liste von Ordnern (unterstützt mehrere)
        self.dir_entry_var = tk.StringVar()  # Für das Eingabefeld
        self.timeline_data = {}
        self.timeline_items = []  # (year, month, day, files, x_pos, item_width)
        self.thumbnail_cache = {}
        self.selected_item = None
        self.size_scale = 1.0
        self.view_start_year = None
        self.view_end_year = None
        
        # Navigation für ausgewählte Items
        self.selected_thumbnail_offset = 0  # Offset für angezeigte Thumbnails
        
        # Timer für verzögerte Timeline-Updates
        self.timeline_update_timer = None
        
        # Canvas-Einstellungen
        self.timeline_height = 300
        self.item_width = 320
        self.item_height = 300
        self.item_spacing = 35
        self.year_height = 50
        self.month_height = 40
        
        # Thumbnail-Einstellungen
        self.thumbnail_size = (160, 120)
        self.max_thumbnails = 4  # Maximal 4 Thumbnails pro Zeitraum
        self.max_cache_size = 500  # Maximale Anzahl gecachter Thumbnails
        
        # Threading
        self.thumbnail_queue = queue.Queue()
        self.loading_thumbnails = set()
        
        # UI-Setup
        self.setup_ui()
        self.start_thumbnail_worker()
        
        # Bind Events
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind("<Left>", self.navigate_thumbnails_left)
        self.root.bind("<Right>", self.navigate_thumbnails_right)
        self.root.focus_set()  # Fokus für Tastatur-Events
        
    def setup_ui(self):
        """Creates the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Header area
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        # Title
        title_label = ttk.Label(header_frame, text=t("timeline_title_short"),
                               font=('Arial', 16, 'bold'))
        title_label.pack(side=tk.LEFT)

        # Language selector
        lang_frame = ttk.Frame(header_frame)
        lang_frame.pack(side=tk.LEFT, padx=(20, 0))

        ttk.Label(lang_frame, text="🌐").pack(side=tk.LEFT)
        self.language_var = tk.StringVar(value="English" if get_language() == "en" else "Deutsch")
        lang_combo = ttk.Combobox(lang_frame, textvariable=self.language_var,
                                  values=["English", "Deutsch"], width=10, state="readonly")
        lang_combo.pack(side=tk.LEFT, padx=(5, 0))
        lang_combo.bind("<<ComboboxSelected>>", self.on_language_change)

        # Folder selection (supports multiple folders)
        folder_frame = ttk.LabelFrame(main_frame, text=t("folders_multiple"), padding="5")
        folder_frame.pack(fill=tk.X, pady=(0, 10))

        # Listbox für Ordner
        list_frame = ttk.Frame(folder_frame)
        list_frame.pack(fill=tk.X, expand=True)

        self.folder_listbox = tk.Listbox(list_frame, height=3, selectmode=tk.SINGLE)
        self.folder_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        folder_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.folder_listbox.yview)
        folder_scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.folder_listbox.config(yscrollcommand=folder_scrollbar.set)

        # Buttons for folder management
        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(side=tk.LEFT, padx=(5, 0))

        ttk.Button(btn_frame, text="➕ " + t("add"),
                  command=self.add_directory).pack(fill=tk.X, pady=1)
        ttk.Button(btn_frame, text="➖ " + t("remove"),
                  command=self.remove_directory).pack(fill=tk.X, pady=1)
        ttk.Button(btn_frame, text="🔄 " + t("load"),
                  command=self.load_timeline).pack(fill=tk.X, pady=1)

        # Size controls
        size_frame = ttk.Frame(header_frame)
        size_frame.pack(side=tk.RIGHT, padx=(20, 0))

        ttk.Label(size_frame, text=t("size")).pack(side=tk.LEFT)
        
        # Größen-Schieber
        self.size_scale_var = tk.DoubleVar(value=1.0)
        self.size_slider = ttk.Scale(size_frame, from_=0.3, to=2.5, 
                                    variable=self.size_scale_var, 
                                    orient=tk.HORIZONTAL, length=150,
                                    command=self.on_size_change)
        self.size_slider.pack(side=tk.LEFT, padx=5)
        
        self.size_label = ttk.Label(size_frame, text="100%", width=6)
        self.size_label.pack(side=tk.LEFT, padx=5)
        
        # Info panel
        info_frame = ttk.LabelFrame(main_frame, text=t("information"), padding="5")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        self.info_label = ttk.Label(info_frame, text=t("select_folder_with_sorted_media"))
        self.info_label.pack(side=tk.LEFT)

        self.stats_label = ttk.Label(info_frame, text="")
        self.stats_label.pack(side=tk.RIGHT)

        # Timeline frame
        timeline_frame = ttk.LabelFrame(main_frame, text=t("timeline"), padding="5")
        timeline_frame.pack(fill=tk.BOTH, expand=True)
        
        # Timeline-Canvas mit Scrollbars
        canvas_frame = ttk.Frame(timeline_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # Vertikale Scrollbar
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical")
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Horizontale Scrollbar
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient="horizontal")
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Canvas
        self.timeline_canvas = tk.Canvas(canvas_frame,
                                       bg='#34495e',
                                       yscrollcommand=v_scrollbar.set,
                                       xscrollcommand=h_scrollbar.set)
        self.timeline_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar-Konfiguration
        v_scrollbar.config(command=self.timeline_canvas.yview)
        h_scrollbar.config(command=self.timeline_canvas.xview)
        
        # Canvas-Events
        self.timeline_canvas.bind("<Configure>", self.on_canvas_configure)
        self.timeline_canvas.bind("<Button-1>", self.on_canvas_click)
        self.timeline_canvas.bind("<Double-Button-1>", self.on_canvas_double_click)
        self.timeline_canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.timeline_canvas.bind("<Motion>", self.on_mouse_motion)
        
        # Detail panel
        detail_frame = ttk.LabelFrame(main_frame, text=t("details"), padding="5")
        detail_frame.pack(fill=tk.X, pady=(10, 0))

        self.detail_label = ttk.Label(detail_frame, text=t("click_for_details"))
        self.detail_label.pack(side=tk.LEFT)

        # Navigation buttons
        nav_frame = ttk.Frame(detail_frame)
        nav_frame.pack(side=tk.RIGHT, padx=(10, 0))

        ttk.Button(nav_frame, text="⬅️ " + t("previous"),
                  command=self.navigate_thumbnails_left).pack(side=tk.LEFT, padx=2)

        self.nav_label = ttk.Label(nav_frame, text="")
        self.nav_label.pack(side=tk.LEFT, padx=10)

        ttk.Button(nav_frame, text=t("next") + " ➡️",
                  command=self.navigate_thumbnails_right).pack(side=tk.LEFT, padx=2)

        ttk.Button(nav_frame, text="🖼️ " + t("show_images"),
                  command=self.show_selected_images).pack(side=tk.LEFT, padx=(10, 0))
        
    def on_language_change(self, event=None):
        """Handle language change"""
        lang = "en" if self.language_var.get() == "English" else "de"
        set_language(lang)
        messagebox.showinfo(t("info"), "Please restart the application to apply the language change.")

    def add_directory(self):
        """Adds a folder to the list"""
        folder = filedialog.askdirectory(title=t("select_folder_title"))
        if folder and folder not in self.base_dirs:
            self.base_dirs.append(folder)
            self.folder_listbox.insert(tk.END, folder)

    def remove_directory(self):
        """Removes the selected folder from the list"""
        selection = self.folder_listbox.curselection()
        if selection:
            index = selection[0]
            self.folder_listbox.delete(index)
            del self.base_dirs[index]

    def load_timeline(self):
        """Loads timeline data from all folders"""
        if not self.base_dirs:
            messagebox.showerror(t("error"), t("error_add_folder"))
            return

        # Validate all folders
        invalid_dirs = [d for d in self.base_dirs if not os.path.exists(d)]
        if invalid_dirs:
            messagebox.showerror(t("error"), t("error_invalid_folders", folders=', '.join(invalid_dirs)))
            return

        self.info_label.config(text=t("loading_timeline"))
        self.root.update()

        # Lade Daten in separatem Thread
        thread = threading.Thread(target=self._load_timeline_data, args=(self.base_dirs,))
        thread.daemon = True
        thread.start()
        
    def _load_timeline_data(self, directories):
        """Lädt Timeline-Daten im Hintergrund aus allen Ordnern"""
        try:
            timeline_data = self.scan_directories(directories)

            # Aktualisiere UI im Hauptthread
            self.root.after(0, self._timeline_data_loaded, timeline_data)

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror(t("error"), t("error_loading", error=str(e))))
            
    def _timeline_data_loaded(self, timeline_data):
        """Callback wenn Timeline-Daten geladen wurden"""
        self.timeline_data = timeline_data
        self.create_timeline()
        
        # Statistiken aktualisieren
        total_files = sum(len(data.get('files', [])) for data in timeline_data.values())
        total_periods = len(timeline_data)
        
        self.stats_label.config(text=t("media_in_periods", files=total_files, periods=total_periods))
        self.info_label.config(text=t("timeline_loaded"))
        
    def scan_directories(self, directories):
        """Scannt alle Verzeichnisse und erstellt kombinierte Timeline-Daten"""
        timeline_data = {}

        # Unterstützte Medienformate
        image_formats = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif', '.webp'}
        video_formats = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
        audio_formats = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma'}
        supported_formats = image_formats | video_formats | audio_formats

        # Scanne alle Ordner
        for directory in directories:
            base_path = Path(directory)
            if not base_path.exists():
                continue

            # Scanne Jahre
            for year_dir in base_path.iterdir():
                if year_dir.is_dir() and year_dir.name.isdigit():
                    year = year_dir.name

                    # Scanne Monate
                    for month_dir in year_dir.iterdir():
                        if month_dir.is_dir() and not month_dir.name.startswith('_'):
                            month = month_dir.name

                            # Sammle alle Medien-Dateien
                            files = []

                            # Prüfe auf Tages-Struktur
                            has_day_folders = any(
                                item.is_dir() and item.name.lstrip('0').isdigit()
                                for item in month_dir.iterdir()
                            )

                            if has_day_folders:
                                # Tages-Struktur
                                for day_dir in month_dir.iterdir():
                                    if day_dir.is_dir() and day_dir.name.lstrip('0').isdigit():
                                        day_files = [
                                            f for f in day_dir.iterdir()
                                            if f.is_file() and f.suffix.lower() in supported_formats
                                        ]
                                        files.extend(day_files)
                            else:
                                # Monats-Struktur
                                files = [
                                    f for f in month_dir.iterdir()
                                    if f.is_file() and f.suffix.lower() in supported_formats
                                ]

                            if files:
                                period_key = f"{year}-{month}"
                                # Kombiniere mit bereits existierenden Daten
                                if period_key in timeline_data:
                                    timeline_data[period_key]['files'].extend(files)
                                    timeline_data[period_key]['count'] += len(files)
                                else:
                                    timeline_data[period_key] = {
                                        'year': year,
                                        'month': month,
                                        'files': files,
                                        'count': len(files),
                                        'date': datetime.strptime(f"{year}-{month.split('-')[0]:0>2}", "%Y-%m")
                                    }

        # Sortiere nach Datum
        sorted_data = {}
        for key in sorted(timeline_data.keys(),
                         key=lambda x: timeline_data[x]['date']):
            sorted_data[key] = timeline_data[key]

        return sorted_data
        
    def create_timeline(self):
        """Erstellt die Timeline-Visualisierung"""
        if not self.timeline_data:
            return
            
        # Canvas löschen
        self.timeline_canvas.delete("all")
        self.timeline_items.clear()
        
        # Thumbnail-Queue leeren um alte Requests zu vermeiden
        while not self.thumbnail_queue.empty():
            try:
                self.thumbnail_queue.get_nowait()
            except queue.Empty:
                break
                
        # Foto-Referenzen neu initialisieren
        self._photo_refs = []
        
        # Timeline-Größe berechnen
        total_items = len(self.timeline_data)
        canvas_width = max(1400, total_items * (self.item_width + self.item_spacing) * self.size_scale)
        
        # Berechne maximale Item-Höhe für Canvas-Höhe
        max_item_height = self.item_height * self.size_scale
        for data in self.timeline_data.values():
            files_count = min(len(data['files']), self.max_thumbnails)
            if files_count > 0:
                thumb_rows = (files_count + 1) // 2
                thumb_height = 90 * self.size_scale
                thumb_spacing = 10 * self.size_scale
                thumb_margin = 5 * self.size_scale
                
                needed_thumb_height = thumb_rows * (thumb_height + thumb_spacing) + thumb_margin * 2
                
                # Mindesthöhe für Header und Footer
                header_footer_height = 100 * self.size_scale
                item_height = max(header_footer_height, needed_thumb_height + header_footer_height)
                max_item_height = max(max_item_height, item_height)
        
        canvas_height = max(500, self.timeline_height + max_item_height + 100)
        
        # Jahre und Monate gruppieren
        years = {}
        for key, data in self.timeline_data.items():
            year = data['year']
            if year not in years:
                years[year] = []
            years[year].append((key, data))
        
        # Zeichne Timeline
        current_x = 50
        
        for year, months in years.items():
            # Jahr-Header
            year_x = current_x
            year_width = len(months) * (self.item_width + self.item_spacing) * self.size_scale - self.item_spacing
            
            # Jahr-Hintergrund
            self.timeline_canvas.create_rectangle(
                year_x - 10, 20, year_x + year_width + 10, 60,
                fill='#3498db', outline='#2980b9', width=2, tags="year"
            )
            
            # Jahr-Text
            self.timeline_canvas.create_text(
                year_x + year_width/2, 40,
                text=year, fill='white', font=('Arial', 14, 'bold'), tags="year"
            )
            
            # Monate zeichnen
            for month_key, month_data in months:
                self.create_timeline_item(month_key, month_data, current_x, 80)
                current_x += (self.item_width + self.item_spacing) * self.size_scale
        
        # Canvas-Scroll-Region aktualisieren
        self.timeline_canvas.configure(scrollregion=self.timeline_canvas.bbox("all"))
        
    def create_timeline_item(self, key, data, x, y):
        """Erstellt ein Timeline-Item"""
        item_width = self.item_width * self.size_scale
        
        # Berechne benötigte Höhe basierend auf Thumbnail-Größe
        files_count = min(len(data['files']), self.max_thumbnails)
        if files_count > 0:
            thumb_rows = (files_count + 1) // 2
            thumb_height = 90 * self.size_scale
            thumb_spacing = 10 * self.size_scale
            thumb_margin = 5 * self.size_scale
            
            needed_thumb_height = thumb_rows * (thumb_height + thumb_spacing) + thumb_margin * 2
            
            # Mindesthöhe für Header und Footer
            header_footer_height = 100 * self.size_scale
            item_height = max(header_footer_height, needed_thumb_height + header_footer_height)
        else:
            item_height = self.item_height * self.size_scale
        
        # Item-Hintergrund
        rect = self.timeline_canvas.create_rectangle(
            x, y, x + item_width, y + item_height,
            fill='#ecf0f1', outline='#bdc3c7', width=2,
            tags=f"item_{key}"
        )
        
        # Titel (Monat)
        month_name = data['month'].split('-')[1] if '-' in data['month'] else data['month']
        title = self.timeline_canvas.create_text(
            x + item_width/2, y + 20,
            text=month_name, fill='#2c3e50', 
            font=('Arial', int(14 * self.size_scale), 'bold'),
            tags=f"item_{key}"
        )
        
        # Anzahl Dateien
        count_text = self.timeline_canvas.create_text(
            x + item_width/2, y + item_height - 25,
            text=t("media_count", count=data['count']), fill='#7f8c8d',
            font=('Arial', int(12 * self.size_scale)),
            tags=f"item_{key}"
        )
        
        # Thumbnail-Bereich
        thumb_area_y = y + 50
        thumb_area_height = item_height - 100
        
        # Lade Thumbnails
        self.load_thumbnails_for_item(key, data, x + 5, thumb_area_y, item_width - 10, thumb_area_height)
        
        # Item in Liste speichern
        self.timeline_items.append({
            'key': key,
            'data': data,
            'x': x,
            'y': y,
            'width': item_width,
            'height': item_height,
            'rect': rect
        })
        
    def load_thumbnails_for_item(self, key, data, x, y, width, height):
        """Lädt Thumbnails für ein Timeline-Item"""
        all_files = data['files']
        
        # Sortiere Dateien: Bilder zuerst, dann Videos, dann Audio
        image_formats = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif', '.webp'}
        video_formats = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
        
        images = [f for f in all_files if f.suffix.lower() in image_formats]
        videos = [f for f in all_files if f.suffix.lower() in video_formats]
        audio = [f for f in all_files if f not in images and f not in videos]
        
        # Bevorzuge Bilder für Thumbnails - berücksichtige Offset
        all_sorted_files = images + videos + audio
        start_idx = self.selected_thumbnail_offset if self.selected_item and self.selected_item['key'] == key else 0
        files = all_sorted_files[start_idx:start_idx + self.max_thumbnails]
        
        if not files:
            return
            
        # Thumbnail-Größe berechnen - größere Thumbnails
        thumb_cols = min(2, len(files))
        thumb_rows = (len(files) + 1) // 2
        
        # Basis-Thumbnail-Größe mit Skalierung (konsistent mit Item-Höhen-Berechnung)
        base_thumb_width = 120 * self.size_scale
        base_thumb_height = 90 * self.size_scale
        
        # Verfügbaren Platz berücksichtigen (mit skaliertem Spacing)
        thumb_spacing = int(10 * self.size_scale)
        available_thumb_width = (width // thumb_cols) - thumb_spacing
        available_thumb_height = (height // thumb_rows) - thumb_spacing
        
        # Priorisiere skalierte Größe, aber beschränke auf verfügbaren Platz
        thumb_width = int(min(base_thumb_width, max(available_thumb_width, 80)))
        thumb_height = int(min(base_thumb_height, max(available_thumb_height, 60)))
        
        # Thumbnails laden
        thumb_margin = int(5 * self.size_scale)
        
        for i, file_path in enumerate(files):
            col = i % thumb_cols
            row = i // thumb_cols
            
            thumb_x = x + col * (thumb_width + thumb_spacing) + thumb_margin
            thumb_y = y + row * (thumb_height + thumb_spacing) + thumb_margin
            
            # Thumbnail-Request in Queue einreihen
            self.thumbnail_queue.put({
                'file_path': file_path,
                'x': thumb_x,
                'y': thumb_y,
                'width': thumb_width,
                'height': thumb_height,
                'key': key,
                'index': i,
                'size_scale': self.size_scale  # Für eindeutige Cache-Keys
            })
            
    def start_thumbnail_worker(self):
        """Startet Thumbnail-Worker-Thread"""
        def worker():
            while True:
                try:
                    request = self.thumbnail_queue.get(timeout=1)
                    if request is None:  # Shutdown-Signal
                        break
                        
                    self.load_single_thumbnail(request)
                    self.thumbnail_queue.task_done()
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"Thumbnail-Worker Fehler: {e}")
                    
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        
    def load_single_thumbnail(self, request):
        """Lädt ein einzelnes Thumbnail"""
        try:
            file_path = request['file_path']
            width = int(request['width'])
            height = int(request['height'])
            size_scale = request.get('size_scale', 1.0)
            
            # Cache-Key enthält Pfad, Größe und Skalierung
            cache_key = f"{file_path}_{width}x{height}_{size_scale:.2f}"
            
            # Prüfe Cache
            if cache_key in self.thumbnail_cache:
                photo = self.thumbnail_cache[cache_key]
            else:
                # Lade und resize Bild
                if file_path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif', '.webp'}:
                    image = Image.open(file_path)
                    image.thumbnail((width, height), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(image)
                    self.thumbnail_cache[cache_key] = photo
                    self.cleanup_cache_if_needed()
                elif file_path.suffix.lower() in {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma'}:
                    # Musik-Emoji für Audiodateien
                    from PIL import ImageDraw, ImageFont
                    placeholder = Image.new('RGB', (width, height), color='#3498db')
                    draw = ImageDraw.Draw(placeholder)
                    
                    # Musik-Emoji in der Mitte
                    try:
                        # Verwende größere Schrift für das Emoji
                        font_size = min(width, height) // 3
                        font = ImageFont.truetype("seguiemj.ttf", font_size)
                        music_emoji = "🎵"
                        
                        # Zentriere das Emoji
                        bbox = draw.textbbox((0, 0), music_emoji, font=font)
                        text_width = bbox[2] - bbox[0]
                        text_height = bbox[3] - bbox[1]
                        
                        x = (width - text_width) // 2
                        y = (height - text_height) // 2
                        
                        draw.text((x, y), music_emoji, font=font, fill='white')
                    except:
                        # Fallback ohne Emoji-Font
                        draw.text((width//2 - 20, height//2 - 10), "♪", font=None, fill='white')
                    
                    photo = ImageTk.PhotoImage(placeholder)
                    self.thumbnail_cache[cache_key] = photo
                    self.cleanup_cache_if_needed()
                elif file_path.suffix.lower() in {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}:
                    # Video-Thumbnail extrahieren
                    video_thumbnail = self.extract_video_thumbnail(file_path, width, height)
                    if video_thumbnail:
                        photo = ImageTk.PhotoImage(video_thumbnail)
                        self.thumbnail_cache[cache_key] = photo
                        self.cleanup_cache_if_needed()
                    else:
                        # Fallback-Platzhalter für Videos
                        from PIL import ImageDraw, ImageFont
                        placeholder = Image.new('RGB', (width, height), color='#e74c3c')
                        draw = ImageDraw.Draw(placeholder)
                        
                        # Video-Icon in der Mitte
                        try:
                            # Verwende größere Schrift für das Emoji
                            font_size = min(width, height) // 3
                            font = ImageFont.truetype("seguiemj.ttf", font_size)
                            video_emoji = "🎬"
                            
                            # Zentriere das Emoji
                            bbox = draw.textbbox((0, 0), video_emoji, font=font)
                            text_width = bbox[2] - bbox[0]
                            text_height = bbox[3] - bbox[1]
                            
                            x = (width - text_width) // 2
                            y = (height - text_height) // 2
                            
                            draw.text((x, y), video_emoji, font=font, fill='white')
                        except:
                            # Fallback ohne Emoji-Font
                            draw.text((width//2 - 10, height//2 - 10), "▶", font=None, fill='white')
                        
                        photo = ImageTk.PhotoImage(placeholder)
                        self.thumbnail_cache[cache_key] = photo
                        self.cleanup_cache_if_needed()
                else:
                    # Placeholder für andere Dateitypen
                    placeholder = Image.new('RGB', (width, height), color='#95a5a6')
                    photo = ImageTk.PhotoImage(placeholder)
                    self.thumbnail_cache[cache_key] = photo
                    self.cleanup_cache_if_needed()
            
            # Thumbnail im Hauptthread anzeigen
            self.root.after(0, self._display_thumbnail, request, photo)
            
        except Exception as e:
            print(f"Fehler beim Laden des Thumbnails {file_path}: {e}")
            
    def cleanup_cache_if_needed(self):
        """Bereinigt den Thumbnail-Cache wenn er zu groß wird"""
        if len(self.thumbnail_cache) > self.max_cache_size:
            # Entferne die ältesten 20% der Cache-Einträge
            items_to_remove = len(self.thumbnail_cache) // 5
            keys_to_remove = list(self.thumbnail_cache.keys())[:items_to_remove]
            
            for key in keys_to_remove:
                del self.thumbnail_cache[key]
            
    def extract_video_thumbnail(self, file_path, width, height):
        """Extrahiert ein Thumbnail aus einem Video"""
        if not HAS_OPENCV:
            return None
            
        try:
            # Öffne Video-Datei
            cap = cv2.VideoCapture(str(file_path))
            
            if not cap.isOpened():
                return None
                
            # Gehe zu ca. 10% der Video-Länge für ein interessanteres Frame
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames > 0:
                frame_pos = min(total_frames // 10, 30)  # Maximal 30 Frames vorspulen
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
            
            # Lese Frame
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                return None
                
            # Konvertiere von BGR zu RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Erstelle PIL-Image
            pil_image = Image.fromarray(frame_rgb)
            
            # Resize auf gewünschte Größe
            pil_image.thumbnail((width, height), Image.Resampling.LANCZOS)
            
            # Füge Play-Button-Overlay hinzu
            overlay = self.add_play_button_overlay(pil_image)
            
            return overlay
            
        except Exception as e:
            print(f"Fehler beim Extrahieren des Video-Thumbnails {file_path}: {e}")
            return None
            
    def add_play_button_overlay(self, image):
        """Fügt ein Play-Button-Overlay zum Video-Thumbnail hinzu"""
        try:
            from PIL import ImageDraw, ImageFont
            
            # Erstelle eine Kopie des Bildes
            overlay_image = image.copy()
            draw = ImageDraw.Draw(overlay_image)
            
            width, height = overlay_image.size
            
            # Halbtransparenter Kreis für Play-Button
            center_x = width // 2
            center_y = height // 2
            radius = min(width, height) // 8
            
            # Kreis-Hintergrund (halbtransparent)
            circle_bbox = [
                center_x - radius, center_y - radius,
                center_x + radius, center_y + radius
            ]
            
            # Zeichne halbtransparenten Kreis
            circle_img = Image.new('RGBA', overlay_image.size, (0, 0, 0, 0))
            circle_draw = ImageDraw.Draw(circle_img)
            circle_draw.ellipse(circle_bbox, fill=(0, 0, 0, 128))
            
            # Kombiniere mit Original
            if overlay_image.mode != 'RGBA':
                overlay_image = overlay_image.convert('RGBA')
            overlay_image = Image.alpha_composite(overlay_image, circle_img)
            
            # Zeichne Play-Symbol (Dreieck)
            triangle_size = radius // 2
            triangle_points = [
                (center_x - triangle_size//2, center_y - triangle_size),
                (center_x - triangle_size//2, center_y + triangle_size),
                (center_x + triangle_size, center_y)
            ]
            
            # Zurück zu RGB für finale Darstellung
            final_image = Image.new('RGB', overlay_image.size, (255, 255, 255))
            final_image.paste(overlay_image, mask=overlay_image.split()[-1] if overlay_image.mode == 'RGBA' else None)
            
            # Zeichne Play-Symbol
            draw = ImageDraw.Draw(final_image)
            draw.polygon(triangle_points, fill='white')
            
            return final_image
            
        except Exception as e:
            print(f"Fehler beim Hinzufügen des Play-Button-Overlays: {e}")
            return image
            
    def _display_thumbnail(self, request, photo):
        """Zeigt Thumbnail im Canvas an"""
        try:
            self.timeline_canvas.create_image(
                request['x'], request['y'],
                anchor=tk.NW, image=photo,
                tags=f"thumb_{request['key']}_{request['index']}"
            )
            
            # Referenz behalten (wichtig für tkinter)
            if not hasattr(self, '_photo_refs'):
                self._photo_refs = []
            self._photo_refs.append(photo)
            
        except Exception as e:
            print(f"Fehler beim Anzeigen des Thumbnails: {e}")
            
    def on_size_change(self, value):
        """Callback für Größen-Schieber"""
        self.size_scale = float(value)
        self.size_label.config(text=f"{int(self.size_scale * 100)}%")
        
        # Verzögerte Timeline-Aktualisierung für bessere Performance
        if self.timeline_update_timer:
            self.root.after_cancel(self.timeline_update_timer)
        self.timeline_update_timer = self.root.after(50, self.create_timeline)
        
    def on_canvas_configure(self, event):
        """Canvas-Größe geändert"""
        pass
        
    def on_canvas_click(self, event):
        """Canvas-Klick"""
        # Konvertiere Canvas-Koordinaten
        x = self.timeline_canvas.canvasx(event.x)
        y = self.timeline_canvas.canvasy(event.y)
        
        # Finde geklicktes Item
        for item in self.timeline_items:
            if (item['x'] <= x <= item['x'] + item['width'] and
                item['y'] <= y <= item['y'] + item['height']):
                
                self.select_timeline_item(item)
                break
        else:
            self.deselect_timeline_item()
            
    def on_canvas_double_click(self, event):
        """Canvas-Doppelklick"""
        self.show_selected_images()
        
    def on_mouse_wheel(self, event):
        """Mausrad für horizontales Scrollen und Größenanpassung"""
        if event.state & 0x4:  # Ctrl gedrückt
            # Größenanpassung
            if event.delta > 0:
                new_size = min(2.5, self.size_scale * 1.1)
            else:
                new_size = max(0.3, self.size_scale / 1.1)
            
            self.size_scale_var.set(new_size)
            self.size_scale = new_size
            self.size_label.config(text=f"{int(self.size_scale * 100)}%")
            self.create_timeline()
        else:
            # Horizontaler Scroll
            self.timeline_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
            
    def on_mouse_motion(self, event):
        """Maus-Bewegung für Tooltip"""
        pass  # Später für Tooltips
        
    def select_timeline_item(self, item):
        """Wählt Timeline-Item aus"""
        # Vorherige Auswahl entfernen
        self.deselect_timeline_item()
        
        # Neue Auswahl
        self.selected_item = item
        self.selected_thumbnail_offset = 0  # Reset offset bei neuer Auswahl
        
        # Highlight
        self.timeline_canvas.create_rectangle(
            item['x'] - 3, item['y'] - 3,
            item['x'] + item['width'] + 3, item['y'] + item['height'] + 3,
            outline='#e74c3c', width=3, tags="selection"
        )
        
        # Detail-Info aktualisieren
        data = item['data']
        self.detail_label.config(
            text=t("selected_period", month=data['month'], year=data['year'], count=data['count'])
        )
        
        # Navigation-Info aktualisieren
        self.update_navigation_info()
        
    def deselect_timeline_item(self):
        """Removes timeline selection"""
        self.timeline_canvas.delete("selection")
        self.selected_item = None
        self.selected_thumbnail_offset = 0
        self.detail_label.config(text=t("click_for_details"))
        self.nav_label.config(text="")
        
    def show_selected_images(self):
        """Shows selected images in new window"""
        if not self.selected_item:
            messagebox.showinfo(t("info"), t("select_period_first"))
            return
            
        # Öffne Bilder-Viewer-Fenster
        self.open_image_viewer(self.selected_item['data'])
        
    def open_image_viewer(self, data):
        """Opens image viewer for selected period"""
        viewer_window = tk.Toplevel(self.root)
        viewer_window.title(f"{t('media_viewer')} - {data['month']} {data['year']}")
        viewer_window.geometry("800x600")

        frame = ttk.Frame(viewer_window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=f"{data['month']} {data['year']}",
                 font=('Arial', 14, 'bold')).pack(pady=(0, 10))

        # Scrollbare Liste
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)

        # Dateien hinzufügen
        for file_path in data['files']:
            listbox.insert(tk.END, file_path.name)

        # Create context menu
        context_menu = tk.Menu(listbox, tearoff=0)
        context_menu.add_command(label=t("open_file"), command=lambda: self._open_selected_file(listbox, data))
        context_menu.add_command(label=t("show_in_folder"), command=lambda: self._show_in_folder(listbox, data))

        def show_context_menu(event):
            # Wähle Item unter dem Cursor aus
            index = listbox.nearest(event.y)
            if index >= 0:
                listbox.selection_clear(0, tk.END)
                listbox.selection_set(index)
                listbox.activate(index)
                context_menu.tk_popup(event.x_root, event.y_root)

        listbox.bind("<Button-3>", show_context_menu)

        # Doppelklick zum Öffnen
        def open_file(event):
            selection = listbox.curselection()
            if selection:
                file_path = data['files'][selection[0]]
                os.startfile(file_path)  # Windows

        listbox.bind("<Double-Button-1>", open_file)

    def _open_selected_file(self, listbox, data):
        """Öffnet die ausgewählte Datei"""
        selection = listbox.curselection()
        if selection:
            file_path = data['files'][selection[0]]
            os.startfile(file_path)

    def _show_in_folder(self, listbox, data):
        """Öffnet den Ordner der ausgewählten Datei im Explorer"""
        selection = listbox.curselection()
        if selection:
            file_path = data['files'][selection[0]]
            # Windows Explorer öffnen und Datei markieren
            subprocess.run(['explorer', '/select,', str(file_path)])
        
    def navigate_thumbnails_left(self, event=None):
        """Navigiert zu vorherigen Thumbnails"""
        if not self.selected_item:
            return
            
        self.selected_thumbnail_offset = max(0, self.selected_thumbnail_offset - self.max_thumbnails)
        self.refresh_selected_item()
        
    def navigate_thumbnails_right(self, event=None):
        """Navigiert zu nächsten Thumbnails"""
        if not self.selected_item:
            return
            
        data = self.selected_item['data']
        total_files = len(data['files'])
        
        if self.selected_thumbnail_offset + self.max_thumbnails < total_files:
            self.selected_thumbnail_offset += self.max_thumbnails
            self.refresh_selected_item()
            
    def refresh_selected_item(self):
        """Aktualisiert die Thumbnails für das ausgewählte Item"""
        if not self.selected_item:
            return
            
        # Lösche alte Thumbnails
        key = self.selected_item['key']
        for i in range(self.max_thumbnails):
            self.timeline_canvas.delete(f"thumb_{key}_{i}")
        
        # Lade neue Thumbnails
        item = self.selected_item
        thumb_area_y = item['y'] + 50
        thumb_area_height = item['height'] - 100
        self.load_thumbnails_for_item(key, item['data'], item['x'] + 5, thumb_area_y, 
                                    item['width'] - 10, thumb_area_height)
        
        # Navigation-Info aktualisieren
        self.update_navigation_info()
        
    def update_navigation_info(self):
        """Aktualisiert die Navigation-Information"""
        if not self.selected_item:
            self.nav_label.config(text="")
            return
            
        data = self.selected_item['data']
        total_files = len(data['files'])
        current_start = self.selected_thumbnail_offset + 1
        current_end = min(self.selected_thumbnail_offset + self.max_thumbnails, total_files)
        
        self.nav_label.config(text=t("showing_range", start=current_start, end=current_end, total=total_files))

    def on_closing(self):
        """Beim Schließen des Fensters"""
        # Timer stoppen
        if self.timeline_update_timer:
            self.root.after_cancel(self.timeline_update_timer)
            
        # Thumbnail-Worker stoppen
        self.thumbnail_queue.put(None)
        self.root.destroy()


def main():
    root = tk.Tk()
    app = TimelineViewer(root)
    root.mainloop()


if __name__ == "__main__":
    main() 