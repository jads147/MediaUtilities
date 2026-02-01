#!/usr/bin/env python3
"""
Image Compressor GUI - Compress images to a target file size (JPEG output)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import io
import logging
from pathlib import Path
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

# Import i18n
from i18n import t, get_language, set_language, get_available_languages


SUPPORTED_IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif',
    '.webp', '.gif'
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


def fmt_size(size_bytes: int) -> str:
    """Format file size to human-readable string."""
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024**3):.1f} GB"
    elif size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024**2):.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


class ImageCompressor:
    """Image compression engine that targets a maximum file size via JPEG quality binary search."""

    def __init__(self, source_dir: str, max_size_mb: float, recursive: bool,
                 num_workers: int, logger: logging.Logger, gui_callback):
        self.source_dir = Path(source_dir)
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)
        self.recursive = recursive
        self.num_workers = max(1, num_workers)
        self.logger = logger
        self.gui_callback = gui_callback

        self.is_running = True
        self._lock = threading.Lock()
        self._completed_count = 0
        self.compressed_files: List[Path] = []
        self.skipped_files: List[Path] = []
        self.failed_files: List[tuple] = []
        self.total_saved_bytes = 0

    def scan_for_images(self) -> List[Path]:
        """Scan source directory for image files."""
        image_files = []
        if self.recursive:
            for f in self.source_dir.rglob('*'):
                if f.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS and f.is_file():
                    image_files.append(f)
        else:
            for f in self.source_dir.glob('*'):
                if f.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS and f.is_file():
                    image_files.append(f)
        image_files.sort(key=lambda p: p.name.lower())
        return image_files

    def compress_image(self, image_path: Path) -> None:
        """Compress a single image to target size using JPEG quality binary search."""
        if not self.is_running:
            return

        try:
            original_size = image_path.stat().st_size

            # If already a JPEG and under limit, skip
            if image_path.suffix.lower() in ('.jpg', '.jpeg') and original_size <= self.max_size_bytes:
                self.logger.info(t("file_already_small",
                                   filename=image_path.name, size=fmt_size(original_size)))
                with self._lock:
                    self.skipped_files.append(image_path)
                return

            # Open and convert to RGB
            img = Image.open(str(image_path))
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Try high quality first
            quality = 95
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=quality, optimize=True)
            result_size = buf.tell()

            if result_size <= self.max_size_bytes:
                # High quality is small enough
                final_quality = quality
                final_data = buf.getvalue()
            else:
                # Binary search for the right quality
                low, high = 1, 94
                final_data = None
                final_quality = 1

                while low <= high:
                    mid = (low + high) // 2
                    buf = io.BytesIO()
                    img.save(buf, format='JPEG', quality=mid, optimize=True)
                    size = buf.tell()

                    if size <= self.max_size_bytes:
                        final_data = buf.getvalue()
                        final_quality = mid
                        low = mid + 1  # Try higher quality
                    else:
                        high = mid - 1  # Need lower quality

                if final_data is None:
                    # Even quality 1 is too large
                    buf = io.BytesIO()
                    img.save(buf, format='JPEG', quality=1, optimize=True)
                    final_data = buf.getvalue()
                    final_quality = 1
                    self.logger.warning(t("target_size_unreachable",
                                          filename=image_path.name,
                                          size=fmt_size(len(final_data))))

            img.close()

            # Determine output path (.jpg extension)
            if image_path.suffix.lower() not in ('.jpg', '.jpeg'):
                new_path = image_path.with_suffix('.jpg')
                # Write new file, then remove old one
                new_path.write_bytes(final_data)
                if new_path != image_path:
                    image_path.unlink()
                    self.logger.info(t("file_not_jpeg_renamed",
                                       old_name=image_path.name, new_name=new_path.name))
                output_path = new_path
            else:
                output_path = image_path
                output_path.write_bytes(final_data)

            new_size = len(final_data)
            saved = original_size - new_size

            self.logger.info(t("file_compressed",
                               filename=output_path.name,
                               old_size=fmt_size(original_size),
                               new_size=fmt_size(new_size),
                               quality=final_quality))

            with self._lock:
                self.compressed_files.append(output_path)
                self.total_saved_bytes += max(0, saved)

        except Exception as e:
            self.logger.error(t("error_compression_failed",
                                filename=image_path.name, error=str(e)))
            with self._lock:
                self.failed_files.append((image_path, str(e)))

    def run(self):
        """Run compression on all found images using thread pool."""
        image_files = self.scan_for_images()
        total = len(image_files)

        if total == 0:
            self.logger.info(t("no_images_found"))
            return

        self.logger.info(f"Found {total} images")
        self.gui_callback(0, total, t("status_compressing"))

        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = {}
            for img_path in image_files:
                if not self.is_running:
                    break
                future = executor.submit(self.compress_image, img_path)
                futures[future] = img_path

            for future in as_completed(futures):
                if not self.is_running:
                    break
                with self._lock:
                    self._completed_count += 1
                    count = self._completed_count
                self.gui_callback(count, total,
                                  t("compressing_file", filename=futures[future].name))

        self.gui_callback(total, total, t("status_compress_complete"))


class ImageCompressorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(t("title_compressor"))
        self.root.geometry("800x600")
        self.root.minsize(750, 550)
        self.root.configure(bg='#f0f0f0')

        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - self.root.winfo_width()) // 2
        y = (self.root.winfo_screenheight() - self.root.winfo_height()) // 2
        self.root.geometry(f"+{x}+{y}")

        # Variables
        self.source_dir = tk.StringVar()
        self.max_size_mb = tk.DoubleVar(value=2.0)
        self.recursive_scan = tk.BooleanVar(value=False)
        self.num_workers = tk.IntVar(value=os.cpu_count() or 4)

        # State
        self.is_running = False
        self.compressor = None

        self.setup_gui()
        self.setup_logging()

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

        title_label = ttk.Label(header_frame, text=t("compressor_title_short"),
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
        folder_frame = ttk.LabelFrame(main_frame, text=t("source_folder_compress").rstrip(':'), padding="8")
        folder_frame.grid(row=1, column=0, pady=(0, 8), sticky=(tk.W, tk.E))
        folder_frame.columnconfigure(1, weight=1)

        ttk.Label(folder_frame, text=t("source_folder_compress")).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(folder_frame, textvariable=self.source_dir).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(folder_frame, text=t("browse"), command=self.browse_source).grid(row=0, column=2)

        # === Settings ===
        settings_frame = ttk.LabelFrame(main_frame, text=t("compression_settings"), padding="8")
        settings_frame.grid(row=2, column=0, pady=(0, 8), sticky=(tk.W, tk.E))

        ttk.Label(settings_frame, text=t("max_file_size_label")).grid(row=0, column=0, sticky=tk.W, pady=2)
        size_spin = ttk.Spinbox(settings_frame, from_=0.1, to=100.0, increment=0.1,
                                textvariable=self.max_size_mb, width=8, format="%.1f")
        size_spin.grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(settings_frame, text="MB", foreground="gray").grid(row=0, column=2, sticky=tk.W)
        ttk.Label(settings_frame, text=t("max_file_size_hint"), foreground="gray").grid(
            row=1, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))

        # === Options ===
        options_frame = ttk.LabelFrame(main_frame, text=t("options_compress"), padding="8")
        options_frame.grid(row=3, column=0, pady=(0, 8), sticky=(tk.W, tk.E))

        ttk.Checkbutton(options_frame, text=t("recursive_scan_compress"),
                        variable=self.recursive_scan).grid(row=0, column=0, sticky=tk.W, pady=1)

        workers_frame = ttk.Frame(options_frame)
        workers_frame.grid(row=1, column=0, sticky=tk.W, pady=1)
        ttk.Label(workers_frame, text=t("num_workers_compress")).pack(side=tk.LEFT)
        ttk.Spinbox(workers_frame, from_=1, to=os.cpu_count() or 16,
                     textvariable=self.num_workers, width=4).pack(side=tk.LEFT, padx=(5, 0))

        # === Buttons ===
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=4, column=0, pady=(0, 8), sticky=(tk.W, tk.E))

        self.start_button = ttk.Button(btn_frame, text=t("start_compression"), command=self.start_compression)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))

        self.stop_button = ttk.Button(btn_frame, text=t("stop_compression"), command=self.stop_compression, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(btn_frame, text=t("clear_log"), command=self.clear_log).pack(side=tk.LEFT, padx=(0, 5))

        # Supported formats info
        ttk.Label(btn_frame, text=t("supported_image_formats"), foreground="gray",
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
        self.logger = logging.getLogger('ImageCompressorGUI')
        self.logger.setLevel(logging.INFO)

        # Clear existing handlers
        self.logger.handlers.clear()

        # GUI handler
        gui_handler = GUILogHandler(self.log_text)
        gui_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S'))
        self.logger.addHandler(gui_handler)

        # File handler
        try:
            file_handler = logging.FileHandler('image_compressor.log', encoding='utf-8')
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(file_handler)
        except Exception:
            pass

    def on_language_change(self, event=None):
        """Handle language change."""
        lang = "en" if self.language_var.get() == "English" else "de"
        set_language(lang)
        messagebox.showinfo("Language", "Please restart the application to apply the language change.")

    def browse_source(self):
        """Open folder dialog for source."""
        folder = filedialog.askdirectory(title=t("select_source_folder_compress"))
        if folder:
            self.source_dir.set(folder)

    def clear_log(self):
        """Clear the log text widget."""
        self.log_text.delete('1.0', tk.END)

    def validate_inputs(self) -> bool:
        """Validate inputs before starting."""
        if not self.source_dir.get():
            messagebox.showwarning(t("warning"), t("error_no_source_compress"))
            return False
        if not Path(self.source_dir.get()).is_dir():
            messagebox.showwarning(t("warning"), t("error_source_not_exists_compress"))
            return False
        return True

    def start_compression(self):
        """Start compression in a separate thread."""
        if not self.validate_inputs():
            return

        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress_bar['value'] = 0
        self.status_var.set(t("status_scanning_images"))
        self.count_var.set("")

        thread = threading.Thread(target=self.run_compression, daemon=True)
        thread.start()

    def stop_compression(self):
        """Stop the running compression."""
        self.is_running = False
        if self.compressor:
            self.compressor.is_running = False
        self.logger.info(t("compression_stopped"))
        self.status_var.set(t("status_compress_stopped"))

    def run_compression(self):
        """Execute compression (runs in worker thread)."""
        try:
            self.compressor = ImageCompressor(
                source_dir=self.source_dir.get(),
                max_size_mb=self.max_size_mb.get(),
                recursive=self.recursive_scan.get(),
                num_workers=self.num_workers.get(),
                logger=self.logger,
                gui_callback=self.update_progress,
            )
            self.compressor.is_running = self.is_running
            self.compressor.run()

            compressed = len(self.compressor.compressed_files)
            skipped = len(self.compressor.skipped_files)
            failed = len(self.compressor.failed_files)
            saved = fmt_size(self.compressor.total_saved_bytes)

            if compressed > 0 or skipped > 0 or failed > 0:
                summary = t("compression_success_msg",
                            compressed=compressed, skipped=skipped,
                            failed=failed, saved=saved)
                self.root.after(0, lambda: messagebox.showinfo(t("compression_summary"), summary))
        except Exception as e:
            self.logger.error(f"Compression error: {e}")
            self.root.after(0, lambda: messagebox.showerror(t("error"), str(e)))
        finally:
            self.is_running = False
            self.root.after(0, self.compression_finished)

    def update_progress(self, current: int, total: int, message: str):
        """Update progress bar (thread-safe via root.after)."""
        def _update():
            if total > 0:
                percent = (current / total) * 100
                self.progress_bar['value'] = percent
                self.count_var.set(t("files_progress_compress", current=current, total=total))
            self.status_var.set(message)
        self.root.after(0, _update)

    def compression_finished(self):
        """Called after compression completes."""
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        if self.compressor and (self.compressor.compressed_files or self.compressor.failed_files):
            self.status_var.set(t("status_compress_complete"))
            self.progress_bar['value'] = 100


def main():
    root = tk.Tk()
    app = ImageCompressorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
