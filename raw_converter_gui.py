#!/usr/bin/env python3
"""
RAW Image Converter GUI - Convert RAW image files to PNG, JPEG, or WebP format
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import shutil
import logging
import time
import random
import tempfile
from pathlib import Path
from typing import List, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageTk
import numpy as np

# Import i18n
from i18n import t, get_language, set_language, get_available_languages

# RAW processing (optional import with graceful fallback)
try:
    import rawpy
    HAS_RAWPY = True
except ImportError:
    HAS_RAWPY = False


SUPPORTED_RAW_EXTENSIONS = {
    '.cr2', '.cr3', '.crw', '.nef', '.arw', '.dng',
    '.orf', '.rw2', '.pef', '.srw', '.raf', '.3fr',
    '.kdc', '.dcr', '.mrw', '.erf', '.mef', '.mos',
    '.nrw', '.rwl', '.sr2', '.x3f'
}


class GUILogHandler(logging.Handler):
    """Logging handler that writes to a Tkinter ScrolledText widget."""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.see(tk.END)
        self.text_widget.after(0, append)


FORMAT_EXTENSIONS = {
    'png': '.png',
    'jpeg': '.jpg',
    'webp': '.webp',
}


class RawConverter:
    """RAW image conversion engine supporting PNG, JPEG, and WebP output."""

    def __init__(self, source_dir: str, output_dir: Optional[str], compression_level: int,
                 bit_depth: int, resize_mode: str, max_width: int, max_height: int,
                 resize_percentage: int, recursive: bool, color_profile: str,
                 move_originals: bool, num_workers: int,
                 logger: logging.Logger, gui_callback,
                 output_format: str = 'png', jpeg_quality: int = 92,
                 webp_quality: int = 90):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir) if output_dir else None
        self.compression_level = compression_level
        self.bit_depth = bit_depth
        self.resize_mode = resize_mode
        self.max_width = max_width
        self.max_height = max_height
        self.resize_percentage = resize_percentage
        self.recursive = recursive
        self.color_profile = color_profile
        self.move_originals = move_originals
        self.num_workers = max(1, num_workers)
        self.logger = logger
        self.gui_callback = gui_callback
        self.output_format = output_format
        self.jpeg_quality = jpeg_quality
        self.webp_quality = webp_quality

        self.is_running = True
        self._lock = threading.Lock()
        self._completed_count = 0
        self.converted_files: List[Path] = []
        self.failed_files: List[tuple] = []
        self.skipped_files: List[Path] = []

    def scan_for_raw_files(self) -> List[Path]:
        """Scan source directory for RAW files."""
        raw_files = []
        if self.recursive:
            for f in self.source_dir.rglob('*'):
                if f.suffix.lower() in SUPPORTED_RAW_EXTENSIONS and f.is_file():
                    raw_files.append(f)
        else:
            for f in self.source_dir.glob('*'):
                if f.suffix.lower() in SUPPORTED_RAW_EXTENSIONS and f.is_file():
                    raw_files.append(f)
        raw_files.sort(key=lambda p: p.name.lower())
        return raw_files

    def build_output_path(self, raw_path: Path) -> Path:
        """Build the output path with the correct extension for the chosen format."""
        ext = FORMAT_EXTENSIONS.get(self.output_format, '.png')
        output_name = raw_path.stem + ext
        if self.output_dir is None:
            return raw_path.parent / output_name
        else:
            try:
                relative = raw_path.parent.relative_to(self.source_dir)
            except ValueError:
                relative = Path()
            return self.output_dir / relative / output_name

    def convert_single_file(self, raw_path: Path):
        """Convert one RAW file to PNG, then move original if enabled."""
        output_path = self.build_output_path(raw_path)

        # Skip if output already exists
        if output_path.exists():
            self.logger.info(t("file_skipped", filename=raw_path.name))
            with self._lock:
                self.skipped_files.append(raw_path)
            return

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with rawpy.imread(str(raw_path)) as raw:
            # Determine color space
            if self.color_profile == "adobe_rgb":
                output_color = rawpy.ColorSpace.AdobeRGB
            else:
                output_color = rawpy.ColorSpace.sRGB

            # Postprocess
            rgb = raw.postprocess(
                output_bps=self.bit_depth,
                use_camera_wb=True,
                no_auto_bright=False,
                output_color=output_color
            )

        # Create Pillow image
        if self.bit_depth == 16:
            img = Image.fromarray(rgb, mode='RGB')
        else:
            img = Image.fromarray(rgb)

        # Resize
        if self.resize_mode == "max_dim":
            img.thumbnail((self.max_width, self.max_height), Image.LANCZOS)
        elif self.resize_mode == "percentage" and self.resize_percentage != 100:
            factor = self.resize_percentage / 100.0
            new_size = (max(1, int(img.width * factor)), max(1, int(img.height * factor)))
            img = img.resize(new_size, Image.LANCZOS)

        # Save in chosen format
        if self.output_format == 'jpeg':
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            img.save(str(output_path), 'JPEG', quality=self.jpeg_quality, optimize=True)
        elif self.output_format == 'webp':
            img.save(str(output_path), 'WEBP', quality=self.webp_quality, method=4)
        else:
            img.save(str(output_path), 'PNG', compress_level=self.compression_level)

        with self._lock:
            self.converted_files.append(raw_path)
        self.logger.info(t("file_converted", src=raw_path.name, dst=output_path.name))

        # Move original immediately after successful conversion
        if self.move_originals:
            self._move_single_original(raw_path)

    def _move_single_original(self, raw_path: Path):
        """Move a single RAW file to _converted subfolder."""
        try:
            converted_dir = raw_path.parent / '_converted'
            converted_dir.mkdir(exist_ok=True)
            dest = converted_dir / raw_path.name
            shutil.move(str(raw_path), str(dest))
        except PermissionError:
            self.logger.error(t("error_permission", path=str(raw_path)))
        except Exception as e:
            self.logger.error(t("error_move_failed", filename=raw_path.name, error=str(e)))

    def _process_file(self, raw_path: Path, total: int):
        """Process a single file: convert + move. Called from thread pool."""
        if not self.is_running:
            return
        self.gui_callback(self._completed_count, total,
                          t("converting_file", filename=raw_path.name))
        try:
            self.convert_single_file(raw_path)
        except PermissionError:
            self.logger.error(t("error_permission", path=str(raw_path)))
            with self._lock:
                self.failed_files.append((raw_path, "Permission denied"))
        except Exception as e:
            self.logger.error(t("error_conversion_failed", filename=raw_path.name, error=str(e)))
            with self._lock:
                self.failed_files.append((raw_path, str(e)))
        finally:
            with self._lock:
                self._completed_count += 1
            self.gui_callback(self._completed_count, total, t("status_converting"))

    def run(self):
        """Main execution: scan -> convert (parallel) -> move happens per-file."""
        self.logger.info(t("status_scanning"))
        raw_files = self.scan_for_raw_files()
        total = len(raw_files)

        if total == 0:
            self.logger.info(t("no_raw_files_found"))
            self.gui_callback(0, 0, t("no_raw_files_found"))
            return

        self.logger.info(f"Found {total} RAW file(s) — using {self.num_workers} thread(s)")
        self.gui_callback(0, total, t("status_converting"))
        self._completed_count = 0

        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = []
            for raw_path in raw_files:
                if not self.is_running:
                    break
                futures.append(executor.submit(self._process_file, raw_path, total))

            # Wait for completion, allow cancel
            for future in as_completed(futures):
                if not self.is_running:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

        self.gui_callback(self._completed_count, total, t("status_complete"))


class FormatBenchmark:
    """Benchmark engine: converts sample RAW files to PNG, JPEG, and WebP for comparison."""

    def __init__(self, source_dir: str, recursive: bool, bit_depth: int,
                 color_profile: str, resize_mode: str, max_width: int,
                 max_height: int, resize_percentage: int,
                 compression_level: int, jpeg_quality: int, webp_quality: int,
                 logger: logging.Logger, gui_callback, sample_count: int = 10):
        self.source_dir = Path(source_dir)
        self.recursive = recursive
        self.bit_depth = bit_depth
        self.color_profile = color_profile
        self.resize_mode = resize_mode
        self.max_width = max_width
        self.max_height = max_height
        self.resize_percentage = resize_percentage
        self.compression_level = compression_level
        self.jpeg_quality = jpeg_quality
        self.webp_quality = webp_quality
        self.logger = logger
        self.gui_callback = gui_callback
        self.sample_count = sample_count
        self.is_running = True
        self.benchmark_dir = self.source_dir / '_benchmark'

    def scan_for_raw_files(self) -> List[Path]:
        raw_files = []
        pattern = self.source_dir.rglob('*') if self.recursive else self.source_dir.glob('*')
        for f in pattern:
            if f.suffix.lower() in SUPPORTED_RAW_EXTENSIONS and f.is_file():
                raw_files.append(f)
        return raw_files

    def run(self) -> Optional[Dict]:
        """Run benchmark and return results dict with file paths (files are NOT deleted)."""
        raw_files = self.scan_for_raw_files()
        if not raw_files:
            self.logger.info(t("benchmark_no_files"))
            return None

        samples = random.sample(raw_files, min(self.sample_count, len(raw_files)))
        total_raw = len(raw_files)

        self.benchmark_dir.mkdir(exist_ok=True)

        results = {
            'total_raw_files': total_raw,
            'sample_count': len(samples),
            'benchmark_dir': self.benchmark_dir,
            'samples': []
        }

        formats = [
            ('png', '.png', 'PNG'),
            ('jpeg', '.jpg', 'JPEG'),
            ('webp', '.webp', 'WEBP'),
        ]

        for idx, raw_path in enumerate(samples):
            if not self.is_running:
                break

            self.gui_callback(idx, len(samples),
                              t("benchmark_running", current=idx + 1, total=len(samples)))
            self.logger.info(f"Benchmark: {raw_path.name} ({idx + 1}/{len(samples)})")

            try:
                with rawpy.imread(str(raw_path)) as raw:
                    if self.color_profile == "adobe_rgb":
                        output_color = rawpy.ColorSpace.AdobeRGB
                    else:
                        output_color = rawpy.ColorSpace.sRGB

                    rgb = raw.postprocess(
                        output_bps=self.bit_depth,
                        use_camera_wb=True,
                        no_auto_bright=False,
                        output_color=output_color
                    )

                if self.bit_depth == 16:
                    img = Image.fromarray(rgb, mode='RGB')
                else:
                    img = Image.fromarray(rgb)

                if self.resize_mode == "max_dim":
                    img.thumbnail((self.max_width, self.max_height), Image.LANCZOS)
                elif self.resize_mode == "percentage" and self.resize_percentage != 100:
                    factor = self.resize_percentage / 100.0
                    new_size = (max(1, int(img.width * factor)), max(1, int(img.height * factor)))
                    img = img.resize(new_size, Image.LANCZOS)

                sample_result = {
                    'name': raw_path.stem,
                    'formats': {}
                }

                for fmt_key, fmt_ext, fmt_pil in formats:
                    if not self.is_running:
                        break

                    out_path = self.benchmark_dir / f"{raw_path.stem}_{fmt_key}{fmt_ext}"

                    start_time = time.perf_counter()

                    if fmt_key == 'jpeg':
                        save_img = img.convert('RGB') if img.mode == 'RGBA' else img
                        save_img.save(str(out_path), fmt_pil, quality=self.jpeg_quality, optimize=True)
                    elif fmt_key == 'webp':
                        img.save(str(out_path), fmt_pil, quality=self.webp_quality, method=4)
                    else:
                        img.save(str(out_path), fmt_pil, compress_level=self.compression_level)

                    elapsed = time.perf_counter() - start_time
                    file_size = os.path.getsize(str(out_path))

                    sample_result['formats'][fmt_key] = {
                        'path': out_path,
                        'size': file_size,
                        'time': elapsed,
                    }

                results['samples'].append(sample_result)

            except Exception as e:
                self.logger.error(f"Benchmark error for {raw_path.name}: {e}")

        self.gui_callback(len(samples), len(samples), t("benchmark_complete"))
        return results

    def cleanup(self):
        """Delete all benchmark files."""
        if self.benchmark_dir.exists():
            shutil.rmtree(str(self.benchmark_dir))


class BenchmarkResultsDialog:
    """Dialog showing benchmark results with side-by-side image comparison."""

    THUMB_SIZE = (350, 250)

    def __init__(self, parent, results: Dict, cleanup_callback):
        self.results = results
        self.cleanup_callback = cleanup_callback
        self.current_index = 0
        self.photo_refs = []  # prevent GC of PhotoImage

        self.win = tk.Toplevel(parent)
        self.win.title(t("benchmark_results_title"))
        self.win.geometry("1200x750")
        self.win.minsize(900, 600)
        self.win.transient(parent)
        self.win.grab_set()

        self._build_ui()
        self._show_stats()
        self._show_image(0)

    def _fmt_size(self, size_bytes: int) -> str:
        if size_bytes >= 1024 * 1024 * 1024:
            return f"{size_bytes / (1024**3):.1f} GB"
        elif size_bytes >= 1024 * 1024:
            return f"{size_bytes / (1024**2):.1f} MB"
        elif size_bytes >= 1024:
            return f"{size_bytes / 1024:.1f} KB"
        return f"{size_bytes} B"

    def _build_ui(self):
        main = ttk.Frame(self.win, padding="10")
        main.pack(fill=tk.BOTH, expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(2, weight=1)

        # --- Stats table ---
        stats_frame = ttk.LabelFrame(main, text=t("benchmark_results_title"), padding="8")
        stats_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 8))

        cols = (t("benchmark_format"), t("benchmark_avg_size"), t("benchmark_avg_time"),
                t("benchmark_total_estimate", count=self.results['total_raw_files']))
        self.stats_tree = ttk.Treeview(stats_frame, columns=cols, show='headings', height=3)
        for c in cols:
            self.stats_tree.heading(c, text=c)
            self.stats_tree.column(c, width=180, anchor=tk.CENTER)
        self.stats_tree.pack(fill=tk.X)

        # --- Navigation ---
        nav_frame = ttk.Frame(main)
        nav_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))

        self.prev_btn = ttk.Button(nav_frame, text=t("benchmark_prev"), command=self._prev_image)
        self.prev_btn.pack(side=tk.LEFT)

        self.nav_label = ttk.Label(nav_frame, text="", font=('Arial', 10, 'bold'))
        self.nav_label.pack(side=tk.LEFT, expand=True)

        self.next_btn = ttk.Button(nav_frame, text=t("benchmark_next"), command=self._next_image)
        self.next_btn.pack(side=tk.RIGHT)

        # --- Image comparison area ---
        img_frame = ttk.Frame(main)
        img_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        img_frame.columnconfigure(0, weight=1)
        img_frame.columnconfigure(1, weight=1)
        img_frame.columnconfigure(2, weight=1)
        img_frame.rowconfigure(1, weight=1)

        self.img_labels = {}
        self.img_canvases = {}
        self.info_labels = {}

        for col_idx, fmt in enumerate(['png', 'jpeg', 'webp']):
            header = ttk.Label(img_frame, text=fmt.upper(), font=('Arial', 12, 'bold'))
            header.grid(row=0, column=col_idx, pady=(0, 3))

            canvas = tk.Canvas(img_frame, bg='#2a2a2a', highlightthickness=0)
            canvas.grid(row=1, column=col_idx, sticky=(tk.W, tk.E, tk.N, tk.S), padx=3)
            self.img_canvases[fmt] = canvas

            info = ttk.Label(img_frame, text="", font=('Consolas', 9))
            info.grid(row=2, column=col_idx, pady=(3, 0))
            self.info_labels[fmt] = info

        # --- Buttons ---
        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=3, column=0, pady=(10, 0), sticky=(tk.W, tk.E))

        ttk.Button(btn_frame, text=t("benchmark_delete_files"),
                   command=self._delete_files).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text=t("benchmark_close"),
                   command=self._on_close).pack(side=tk.RIGHT)

        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

    def _show_stats(self):
        samples = self.results['samples']
        if not samples:
            return

        total_raw = self.results['total_raw_files']

        for fmt in ['png', 'jpeg', 'webp']:
            sizes = [s['formats'][fmt]['size'] for s in samples if fmt in s['formats']]
            times = [s['formats'][fmt]['time'] for s in samples if fmt in s['formats']]

            if not sizes:
                continue

            avg_size = sum(sizes) / len(sizes)
            avg_time = sum(times) / len(times)
            est_total = avg_size * total_raw

            cols = self.stats_tree['columns']
            self.stats_tree.insert('', tk.END, values=(
                fmt.upper(),
                self._fmt_size(int(avg_size)),
                f"{avg_time:.2f}s",
                f"~{self._fmt_size(int(est_total))}",
            ))

    def _show_image(self, index: int):
        samples = self.results['samples']
        if not samples:
            return

        self.current_index = max(0, min(index, len(samples) - 1))
        sample = samples[self.current_index]

        self.nav_label.config(text=t("benchmark_image_of",
                                      current=self.current_index + 1, total=len(samples)))
        self.prev_btn.config(state=tk.NORMAL if self.current_index > 0 else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if self.current_index < len(samples) - 1 else tk.DISABLED)

        self.photo_refs.clear()

        for fmt in ['png', 'jpeg', 'webp']:
            canvas = self.img_canvases[fmt]
            canvas.delete("all")

            if fmt not in sample['formats']:
                continue

            info = sample['formats'][fmt]
            path = info['path']

            try:
                img = Image.open(str(path))
                # Fit to canvas size
                canvas.update_idletasks()
                cw = max(canvas.winfo_width(), 200)
                ch = max(canvas.winfo_height(), 200)
                img.thumbnail((cw, ch), Image.LANCZOS)

                photo = ImageTk.PhotoImage(img)
                self.photo_refs.append(photo)

                canvas.create_image(cw // 2, ch // 2, image=photo, anchor=tk.CENTER)
            except Exception:
                canvas.create_text(100, 100, text="Error", fill="red")

            self.info_labels[fmt].config(
                text=f"{sample['name']}  |  {self._fmt_size(info['size'])}  |  {info['time']:.2f}s"
            )

    def _prev_image(self):
        self._show_image(self.current_index - 1)

    def _next_image(self):
        self._show_image(self.current_index + 1)

    def _delete_files(self):
        if messagebox.askyesno(t("benchmark_title"), t("benchmark_confirm_delete"),
                               parent=self.win):
            self.cleanup_callback()
            self.win.destroy()

    def _on_close(self):
        if messagebox.askyesno(t("benchmark_title"), t("benchmark_confirm_delete"),
                               parent=self.win):
            self.cleanup_callback()
        self.win.destroy()


class RawConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(t("title_raw_converter"))
        self.root.geometry("900x750")
        self.root.minsize(850, 700)
        self.root.configure(bg='#f0f0f0')

        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - self.root.winfo_width()) // 2
        y = (self.root.winfo_screenheight() - self.root.winfo_height()) // 2
        self.root.geometry(f"+{x}+{y}")

        # Variables
        self.source_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.output_mode = tk.StringVar(value="in_place")  # "in_place" or "custom"
        self.compression_level = tk.IntVar(value=6)
        self.bit_depth = tk.StringVar(value="8")
        self.resize_mode = tk.StringVar(value="none")
        self.max_width = tk.IntVar(value=4000)
        self.max_height = tk.IntVar(value=3000)
        self.resize_percentage = tk.IntVar(value=100)
        self.recursive_scan = tk.BooleanVar(value=False)
        self.color_profile = tk.StringVar(value="srgb")
        self.move_originals_var = tk.BooleanVar(value=True)
        self.num_workers = tk.IntVar(value=os.cpu_count() or 4)
        self.output_format = tk.StringVar(value="png")
        self.jpeg_quality = tk.IntVar(value=92)
        self.webp_quality = tk.IntVar(value=90)

        # State
        self.is_running = False
        self.converter: Optional[RawConverter] = None
        self.benchmark: Optional[FormatBenchmark] = None

        self.setup_gui()
        self.setup_logging()

        # Check rawpy availability
        if not HAS_RAWPY:
            self.root.after(100, lambda: messagebox.showwarning(
                t("warning"), t("error_rawpy_not_installed")))

    def setup_gui(self):
        """Create the GUI elements."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # === Header ===
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, pady=(0, 15), sticky=(tk.W, tk.E))

        title_label = ttk.Label(header_frame, text=t("raw_converter_title_short"),
                                font=('Arial', 16, 'bold'))
        title_label.pack(side=tk.LEFT)

        # Language selector
        lang_frame = ttk.Frame(header_frame)
        lang_frame.pack(side=tk.RIGHT)
        ttk.Label(lang_frame, text=t("language") + ":").pack(side=tk.LEFT)
        self.language_var = tk.StringVar(value="English" if get_language() == "en" else "Deutsch")
        lang_combo = ttk.Combobox(lang_frame, textvariable=self.language_var,
                                  values=["English", "Deutsch"], width=10, state="readonly")
        lang_combo.pack(side=tk.LEFT, padx=(5, 0))
        lang_combo.bind("<<ComboboxSelected>>", self.on_language_change)

        # === Folder Selection ===
        folder_frame = ttk.LabelFrame(main_frame, text=t("source_folder_raw").rstrip(':'), padding="8")
        folder_frame.grid(row=1, column=0, pady=(0, 8), sticky=(tk.W, tk.E))
        folder_frame.columnconfigure(1, weight=1)

        ttk.Label(folder_frame, text=t("source_folder_raw")).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(folder_frame, textvariable=self.source_dir).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(folder_frame, text=t("browse"), command=self.browse_source).grid(row=0, column=2)

        # Output mode selection
        ttk.Separator(folder_frame, orient=tk.HORIZONTAL).grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        ttk.Label(folder_frame, text=t("output_mode_label"), font=('Arial', 9, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=(0, 2))

        ttk.Radiobutton(folder_frame, text=t("output_in_place"),
                        variable=self.output_mode, value="in_place",
                        command=self.toggle_output_widgets).grid(row=3, column=0, columnspan=3, sticky=tk.W)

        ttk.Radiobutton(folder_frame, text=t("output_custom"),
                        variable=self.output_mode, value="custom",
                        command=self.toggle_output_widgets).grid(row=4, column=0, columnspan=3, sticky=tk.W)

        self.output_row_frame = ttk.Frame(folder_frame)
        self.output_row_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=(20, 0), pady=(2, 0))
        self.output_row_frame.columnconfigure(1, weight=1)

        self.output_label = ttk.Label(self.output_row_frame, text=t("output_folder_raw"))
        self.output_label.grid(row=0, column=0, sticky=tk.W)
        self.output_entry = ttk.Entry(self.output_row_frame, textvariable=self.output_dir)
        self.output_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        self.output_browse_btn = ttk.Button(self.output_row_frame, text=t("browse"), command=self.browse_output)
        self.output_browse_btn.grid(row=0, column=2)

        self.toggle_output_widgets()

        # === Settings: two columns ===
        settings_row = ttk.Frame(main_frame)
        settings_row.grid(row=2, column=0, pady=(0, 8), sticky=(tk.W, tk.E))
        settings_row.columnconfigure(0, weight=1)
        settings_row.columnconfigure(1, weight=1)

        # -- Left: Conversion Settings --
        conv_frame = ttk.LabelFrame(settings_row, text=t("conversion_settings"), padding="8")
        conv_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 4))

        # Output Format
        ttk.Label(conv_frame, text=t("output_format_label")).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.format_combo = ttk.Combobox(conv_frame, textvariable=self.output_format, width=25, state="readonly")
        self.format_combo['values'] = ["png", "jpeg", "webp"]
        self.format_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
        self.format_combo.bind("<<ComboboxSelected>>", self.on_format_change)

        # Format description
        self.format_desc_label = ttk.Label(conv_frame, text=t("format_png"), foreground="gray")
        self.format_desc_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))

        # PNG Compression (shown when format=png)
        self.png_settings_frame = ttk.Frame(conv_frame)
        self.png_settings_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E))
        ttk.Label(self.png_settings_frame, text=t("png_compression")).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.comp_spin = ttk.Spinbox(self.png_settings_frame, from_=0, to=9, textvariable=self.compression_level, width=5)
        self.comp_spin.grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(self.png_settings_frame, text=t("compression_hint"), foreground="gray").grid(
            row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))

        # JPEG Quality (shown when format=jpeg)
        self.jpeg_settings_frame = ttk.Frame(conv_frame)
        self.jpeg_settings_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E))
        ttk.Label(self.jpeg_settings_frame, text=t("jpeg_quality_label")).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.jpeg_spin = ttk.Spinbox(self.jpeg_settings_frame, from_=1, to=100, textvariable=self.jpeg_quality, width=5)
        self.jpeg_spin.grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(self.jpeg_settings_frame, text=t("jpeg_quality_hint"), foreground="gray").grid(
            row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))

        # WebP Quality (shown when format=webp)
        self.webp_settings_frame = ttk.Frame(conv_frame)
        self.webp_settings_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E))
        ttk.Label(self.webp_settings_frame, text=t("webp_quality_label")).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.webp_spin = ttk.Spinbox(self.webp_settings_frame, from_=1, to=100, textvariable=self.webp_quality, width=5)
        self.webp_spin.grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(self.webp_settings_frame, text=t("webp_quality_hint"), foreground="gray").grid(
            row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))

        # Bit Depth
        ttk.Label(conv_frame, text=t("bit_depth_label")).grid(row=3, column=0, sticky=tk.W, pady=2)
        bd_frame = ttk.Frame(conv_frame)
        bd_frame.grid(row=3, column=1, sticky=tk.W)
        ttk.Radiobutton(bd_frame, text=t("bit_depth_8"), variable=self.bit_depth, value="8").pack(side=tk.LEFT)
        ttk.Radiobutton(bd_frame, text=t("bit_depth_16"), variable=self.bit_depth, value="16").pack(side=tk.LEFT, padx=(10, 0))

        # Color Profile
        ttk.Label(conv_frame, text=t("color_profile_label")).grid(row=4, column=0, sticky=tk.W, pady=2)
        self.color_combo = ttk.Combobox(conv_frame, textvariable=self.color_profile, width=18, state="readonly")
        self.color_combo['values'] = ["srgb", "adobe_rgb"]
        self.color_combo.grid(row=4, column=1, sticky=tk.W, padx=5)

        # Initialize format-specific visibility
        self.on_format_change()

        # -- Right: Resize Options --
        resize_frame = ttk.LabelFrame(settings_row, text=t("resize_options"), padding="8")
        resize_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(4, 0))

        ttk.Radiobutton(resize_frame, text=t("resize_none"),
                        variable=self.resize_mode, value="none",
                        command=self.toggle_resize_widgets).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=2)

        ttk.Radiobutton(resize_frame, text=t("resize_max_dim"),
                        variable=self.resize_mode, value="max_dim",
                        command=self.toggle_resize_widgets).grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=2)

        dim_frame = ttk.Frame(resize_frame)
        dim_frame.grid(row=2, column=0, columnspan=3, sticky=tk.W, padx=(20, 0))
        ttk.Label(dim_frame, text=t("max_width_label")).pack(side=tk.LEFT)
        self.width_spin = ttk.Spinbox(dim_frame, from_=100, to=20000, textvariable=self.max_width, width=7)
        self.width_spin.pack(side=tk.LEFT, padx=(2, 10))
        ttk.Label(dim_frame, text=t("max_height_label")).pack(side=tk.LEFT)
        self.height_spin = ttk.Spinbox(dim_frame, from_=100, to=20000, textvariable=self.max_height, width=7)
        self.height_spin.pack(side=tk.LEFT, padx=(2, 0))

        ttk.Radiobutton(resize_frame, text=t("resize_percentage"),
                        variable=self.resize_mode, value="percentage",
                        command=self.toggle_resize_widgets).grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=2)

        pct_frame = ttk.Frame(resize_frame)
        pct_frame.grid(row=4, column=0, columnspan=3, sticky=tk.W, padx=(20, 0))
        ttk.Label(pct_frame, text=t("percentage_label")).pack(side=tk.LEFT)
        self.pct_spin = ttk.Spinbox(pct_frame, from_=1, to=200, textvariable=self.resize_percentage, width=5)
        self.pct_spin.pack(side=tk.LEFT, padx=(2, 2))
        ttk.Label(pct_frame, text="%").pack(side=tk.LEFT)

        self.toggle_resize_widgets()

        # === Options ===
        options_frame = ttk.LabelFrame(main_frame, text=t("options_raw"), padding="8")
        options_frame.grid(row=3, column=0, pady=(0, 8), sticky=(tk.W, tk.E))

        ttk.Checkbutton(options_frame, text=t("recursive_scan"),
                        variable=self.recursive_scan).grid(row=0, column=0, sticky=tk.W, pady=1)
        ttk.Checkbutton(options_frame, text=t("move_originals"),
                        variable=self.move_originals_var).grid(row=1, column=0, sticky=tk.W, pady=1)

        workers_frame = ttk.Frame(options_frame)
        workers_frame.grid(row=2, column=0, sticky=tk.W, pady=1)
        ttk.Label(workers_frame, text=t("num_workers_label")).pack(side=tk.LEFT)
        ttk.Spinbox(workers_frame, from_=1, to=os.cpu_count() or 16,
                     textvariable=self.num_workers, width=4).pack(side=tk.LEFT, padx=(5, 0))

        # === Buttons ===
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=4, column=0, pady=(0, 8), sticky=(tk.W, tk.E))

        self.start_button = ttk.Button(btn_frame, text=t("start_conversion"), command=self.start_conversion)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        if not HAS_RAWPY:
            self.start_button.config(state=tk.DISABLED)

        self.stop_button = ttk.Button(btn_frame, text=t("stop_conversion"), command=self.stop_conversion, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(btn_frame, text=t("clear_log"), command=self.clear_log).pack(side=tk.LEFT, padx=(0, 5))

        self.benchmark_button = ttk.Button(btn_frame, text=t("benchmark_btn"), command=self.start_benchmark)
        self.benchmark_button.pack(side=tk.LEFT, padx=(0, 5))
        if not HAS_RAWPY:
            self.benchmark_button.config(state=tk.DISABLED)

        # Supported formats info
        ttk.Label(btn_frame, text=t("supported_raw_formats"), foreground="gray",
                  font=('Arial', 8)).pack(side=tk.RIGHT)

        # === Progress ===
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=5, column=0, pady=(0, 5), sticky=(tk.W, tk.E))
        progress_frame.columnconfigure(0, weight=1)

        self.status_var = tk.StringVar(value=t("status_ready"))
        ttk.Label(progress_frame, textvariable=self.status_var, font=('Arial', 9, 'bold')).grid(
            row=0, column=0, sticky=tk.W)

        self.count_var = tk.StringVar(value="")
        ttk.Label(progress_frame, textvariable=self.count_var).grid(row=0, column=1, sticky=tk.E)

        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=400)
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(3, 0))

        # === Log Output ===
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="5")
        log_frame.grid(row=6, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, wrap=tk.WORD,
                                                   font=('Consolas', 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    def setup_logging(self):
        """Set up logging to GUI and file."""
        self.logger = logging.getLogger('RawConverterGUI')
        self.logger.setLevel(logging.INFO)

        # Clear existing handlers
        self.logger.handlers.clear()

        # GUI handler
        gui_handler = GUILogHandler(self.log_text)
        gui_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S'))
        self.logger.addHandler(gui_handler)

        # File handler
        try:
            file_handler = logging.FileHandler('raw_converter_gui.log', encoding='utf-8')
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(file_handler)
        except Exception:
            pass

    def on_language_change(self, event=None):
        """Handle language change."""
        lang = "en" if self.language_var.get() == "English" else "de"
        set_language(lang)
        messagebox.showinfo("Language", "Please restart the application to apply the language change.")

    def on_format_change(self, event=None):
        """Show/hide format-specific settings based on selected output format."""
        fmt = self.output_format.get()

        self.png_settings_frame.grid_remove()
        self.jpeg_settings_frame.grid_remove()
        self.webp_settings_frame.grid_remove()

        if fmt == 'png':
            self.png_settings_frame.grid()
            self.format_desc_label.config(text=t("format_png"))
        elif fmt == 'jpeg':
            self.jpeg_settings_frame.grid()
            self.format_desc_label.config(text=t("format_jpeg"))
        elif fmt == 'webp':
            self.webp_settings_frame.grid()
            self.format_desc_label.config(text=t("format_webp"))

    def browse_source(self):
        """Open folder dialog for source."""
        folder = filedialog.askdirectory(title=t("select_source_folder_raw"))
        if folder:
            self.source_dir.set(folder)

    def browse_output(self):
        """Open folder dialog for output."""
        folder = filedialog.askdirectory(title=t("select_output_folder_raw"))
        if folder:
            self.output_dir.set(folder)

    def toggle_output_widgets(self):
        """Enable/disable output folder widgets based on output mode."""
        if self.output_mode.get() == "custom":
            state = tk.NORMAL
        else:
            state = tk.DISABLED
        self.output_entry.config(state=state)
        self.output_browse_btn.config(state=state)

    def toggle_resize_widgets(self):
        """Enable/disable resize widgets based on mode selection."""
        mode = self.resize_mode.get()
        dim_state = tk.NORMAL if mode == "max_dim" else tk.DISABLED
        pct_state = tk.NORMAL if mode == "percentage" else tk.DISABLED

        self.width_spin.config(state=dim_state)
        self.height_spin.config(state=dim_state)
        self.pct_spin.config(state=pct_state)

    def clear_log(self):
        """Clear the log text widget."""
        self.log_text.delete('1.0', tk.END)

    def validate_inputs(self) -> bool:
        """Validate inputs before starting conversion."""
        if not self.source_dir.get():
            messagebox.showwarning(t("warning"), t("error_no_source_raw"))
            return False
        if not Path(self.source_dir.get()).is_dir():
            messagebox.showwarning(t("warning"), t("error_source_not_exists_raw"))
            return False
        if self.output_mode.get() == "custom" and not self.output_dir.get():
            messagebox.showwarning(t("warning"), t("error_no_output_raw"))
            return False
        if not HAS_RAWPY:
            messagebox.showerror(t("error"), t("error_rawpy_not_installed"))
            return False
        return True

    def start_conversion(self):
        """Start conversion in a separate thread."""
        if not self.validate_inputs():
            return

        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress_bar['value'] = 0
        self.status_var.set(t("status_scanning"))
        self.count_var.set("")

        thread = threading.Thread(target=self.run_conversion, daemon=True)
        thread.start()

    def stop_conversion(self):
        """Stop the running conversion or benchmark."""
        self.is_running = False
        if self.converter:
            self.converter.is_running = False
        if self.benchmark:
            self.benchmark.is_running = False
        self.logger.info(t("conversion_stopped"))
        self.status_var.set(t("status_stopped"))

    def run_conversion(self):
        """Execute conversion (runs in worker thread)."""
        try:
            output = self.output_dir.get() if self.output_mode.get() == "custom" else None
            self.converter = RawConverter(
                source_dir=self.source_dir.get(),
                output_dir=output,
                compression_level=self.compression_level.get(),
                bit_depth=int(self.bit_depth.get()),
                resize_mode=self.resize_mode.get(),
                max_width=self.max_width.get(),
                max_height=self.max_height.get(),
                resize_percentage=self.resize_percentage.get(),
                recursive=self.recursive_scan.get(),
                color_profile=self.color_profile.get(),
                move_originals=self.move_originals_var.get(),
                num_workers=self.num_workers.get(),
                logger=self.logger,
                gui_callback=self.update_progress,
                output_format=self.output_format.get(),
                jpeg_quality=self.jpeg_quality.get(),
                webp_quality=self.webp_quality.get(),
            )
            self.converter.is_running = self.is_running
            self.converter.run()

            converted = len(self.converter.converted_files)
            failed = len(self.converter.failed_files)
            skipped = len(self.converter.skipped_files)
            if converted > 0 or failed > 0:
                summary = t("conversion_success_msg",
                            converted=converted, failed=failed, skipped=skipped)
                self.root.after(0, lambda: messagebox.showinfo(t("conversion_summary"), summary))
        except Exception as e:
            self.logger.error(f"Conversion error: {e}")
            self.root.after(0, lambda: messagebox.showerror(t("error"), str(e)))
        finally:
            self.is_running = False
            self.root.after(0, self.conversion_finished)

    def update_progress(self, current: int, total: int, message: str):
        """Update progress bar (thread-safe via root.after)."""
        def _update():
            if total > 0:
                percent = (current / total) * 100
                self.progress_bar['value'] = percent
                self.count_var.set(t("files_progress", current=current, total=total))
            self.status_var.set(message)
        self.root.after(0, _update)

    def conversion_finished(self):
        """Called after conversion completes."""
        self.start_button.config(state=tk.NORMAL if HAS_RAWPY else tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        self.benchmark_button.config(state=tk.NORMAL if HAS_RAWPY else tk.DISABLED)
        if self.is_running is False and self.converter:
            if self.converter.converted_files or self.converter.failed_files:
                self.status_var.set(t("status_complete"))
                self.progress_bar['value'] = 100

    def start_benchmark(self):
        """Start benchmark in a separate thread."""
        if not self.source_dir.get():
            messagebox.showwarning(t("warning"), t("error_no_source_raw"))
            return
        if not Path(self.source_dir.get()).is_dir():
            messagebox.showwarning(t("warning"), t("error_source_not_exists_raw"))
            return
        if not HAS_RAWPY:
            messagebox.showerror(t("error"), t("error_rawpy_not_installed"))
            return

        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.benchmark_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress_bar['value'] = 0
        self.status_var.set(t("benchmark_running", current=0, total="?"))
        self.count_var.set("")

        thread = threading.Thread(target=self.run_benchmark, daemon=True)
        thread.start()

    def run_benchmark(self):
        """Execute benchmark (runs in worker thread)."""
        try:
            self.benchmark = FormatBenchmark(
                source_dir=self.source_dir.get(),
                recursive=self.recursive_scan.get(),
                bit_depth=int(self.bit_depth.get()),
                color_profile=self.color_profile.get(),
                resize_mode=self.resize_mode.get(),
                max_width=self.max_width.get(),
                max_height=self.max_height.get(),
                resize_percentage=self.resize_percentage.get(),
                compression_level=self.compression_level.get(),
                jpeg_quality=self.jpeg_quality.get(),
                webp_quality=self.webp_quality.get(),
                logger=self.logger,
                gui_callback=self.update_progress,
            )
            self.benchmark.is_running = self.is_running
            results = self.benchmark.run()

            if results and results['samples']:
                self.root.after(0, lambda: self._show_benchmark_results(results))
            elif not results:
                self.root.after(0, lambda: messagebox.showinfo(
                    t("benchmark_title"), t("benchmark_no_files")))
        except Exception as e:
            self.logger.error(f"Benchmark error: {e}")
            self.root.after(0, lambda: messagebox.showerror(t("error"), str(e)))
        finally:
            self.is_running = False
            self.root.after(0, self._benchmark_finished)

    def _show_benchmark_results(self, results):
        """Open the benchmark results dialog."""
        BenchmarkResultsDialog(self.root, results, self._cleanup_benchmark)

    def _cleanup_benchmark(self):
        """Delete benchmark files."""
        if self.benchmark:
            self.benchmark.cleanup()
            self.logger.info(t("benchmark_delete_files"))

    def _benchmark_finished(self):
        """Called after benchmark completes."""
        self.start_button.config(state=tk.NORMAL if HAS_RAWPY else tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        self.benchmark_button.config(state=tk.NORMAL if HAS_RAWPY else tk.DISABLED)
        self.status_var.set(t("benchmark_complete"))
        self.progress_bar['value'] = 100


def main():
    root = tk.Tk()
    app = RawConverterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
