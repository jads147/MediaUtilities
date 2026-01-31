#!/usr/bin/env python3
"""
RAW to PNG Converter GUI - Convert RAW image files to compressed PNG format
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import shutil
import logging
from pathlib import Path
from typing import List, Optional
from PIL import Image
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


class RawConverter:
    """RAW to PNG conversion engine."""

    def __init__(self, source_dir: str, output_dir: Optional[str], compression_level: int,
                 bit_depth: int, resize_mode: str, max_width: int, max_height: int,
                 resize_percentage: int, recursive: bool, color_profile: str,
                 move_originals: bool, logger: logging.Logger, gui_callback):
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
        self.logger = logger
        self.gui_callback = gui_callback

        self.is_running = True
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
        """Build the output PNG path. In-place mode saves next to the RAW file."""
        output_name = raw_path.stem + '.png'
        if self.output_dir is None:
            # In-place: save PNG in the same directory as the RAW file
            return raw_path.parent / output_name
        else:
            # Custom output folder: preserve subfolder structure
            try:
                relative = raw_path.parent.relative_to(self.source_dir)
            except ValueError:
                relative = Path()
            return self.output_dir / relative / output_name

    def convert_single_file(self, raw_path: Path):
        """Convert one RAW file to PNG."""
        output_path = self.build_output_path(raw_path)

        # Skip if output already exists
        if output_path.exists():
            self.logger.info(t("file_skipped", filename=raw_path.name))
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
            # rawpy returns uint16 array for 16-bit
            # Pillow needs mode 'I;16' per channel or we use 'RGB' with uint8
            # For 16-bit PNG: convert channels individually
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

        # Save as PNG
        img.save(str(output_path), 'PNG', compress_level=self.compression_level)

        self.converted_files.append(raw_path)
        self.logger.info(t("file_converted", src=raw_path.name, dst=output_path.name))

    def move_converted_originals(self):
        """Move successfully converted RAW files to _converted subfolder."""
        moved = 0
        for raw_path in self.converted_files:
            if not self.is_running:
                break
            try:
                converted_dir = raw_path.parent / '_converted'
                converted_dir.mkdir(exist_ok=True)
                dest = converted_dir / raw_path.name
                shutil.move(str(raw_path), str(dest))
                self.logger.info(t("moving_file", filename=raw_path.name))
                moved += 1
            except PermissionError:
                self.logger.error(t("error_permission", path=str(raw_path)))
            except Exception as e:
                self.logger.error(t("error_move_failed", filename=raw_path.name, error=str(e)))
        if moved > 0:
            self.logger.info(t("originals_moved", count=moved))

    def run(self):
        """Main execution: scan -> convert -> move originals."""
        self.logger.info(t("status_scanning"))
        raw_files = self.scan_for_raw_files()
        total = len(raw_files)

        if total == 0:
            self.logger.info(t("no_raw_files_found"))
            self.gui_callback(0, 0, t("no_raw_files_found"))
            return

        self.logger.info(f"Found {total} RAW file(s)")
        self.gui_callback(0, total, t("status_converting"))

        for i, raw_path in enumerate(raw_files):
            if not self.is_running:
                break
            self.gui_callback(i, total, t("converting_file", filename=raw_path.name))
            try:
                self.convert_single_file(raw_path)
            except PermissionError:
                self.logger.error(t("error_permission", path=str(raw_path)))
                self.failed_files.append((raw_path, "Permission denied"))
            except Exception as e:
                self.logger.error(t("error_conversion_failed", filename=raw_path.name, error=str(e)))
                self.failed_files.append((raw_path, str(e)))

        self.gui_callback(total, total, t("status_converting"))

        # Move originals if enabled
        if self.move_originals and self.is_running and self.converted_files:
            self.gui_callback(total, total, t("status_moving"))
            self.move_converted_originals()


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

        # State
        self.is_running = False
        self.converter: Optional[RawConverter] = None

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

        # PNG Compression
        ttk.Label(conv_frame, text=t("png_compression")).grid(row=0, column=0, sticky=tk.W, pady=2)
        comp_spin = ttk.Spinbox(conv_frame, from_=0, to=9, textvariable=self.compression_level, width=5)
        comp_spin.grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(conv_frame, text=t("compression_hint"), foreground="gray").grid(
            row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))

        # Bit Depth
        ttk.Label(conv_frame, text=t("bit_depth_label")).grid(row=2, column=0, sticky=tk.W, pady=2)
        bd_frame = ttk.Frame(conv_frame)
        bd_frame.grid(row=2, column=1, sticky=tk.W)
        ttk.Radiobutton(bd_frame, text=t("bit_depth_8"), variable=self.bit_depth, value="8").pack(side=tk.LEFT)
        ttk.Radiobutton(bd_frame, text=t("bit_depth_16"), variable=self.bit_depth, value="16").pack(side=tk.LEFT, padx=(10, 0))

        # Color Profile
        ttk.Label(conv_frame, text=t("color_profile_label")).grid(row=3, column=0, sticky=tk.W, pady=2)
        self.color_combo = ttk.Combobox(conv_frame, textvariable=self.color_profile, width=18, state="readonly")
        self.color_combo['values'] = ["srgb", "adobe_rgb"]
        self.color_combo.grid(row=3, column=1, sticky=tk.W, padx=5)

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

        # === Buttons ===
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=4, column=0, pady=(0, 8), sticky=(tk.W, tk.E))

        self.start_button = ttk.Button(btn_frame, text=t("start_conversion"), command=self.start_conversion)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        if not HAS_RAWPY:
            self.start_button.config(state=tk.DISABLED)

        self.stop_button = ttk.Button(btn_frame, text=t("stop_conversion"), command=self.stop_conversion, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(btn_frame, text=t("clear_log"), command=self.clear_log).pack(side=tk.LEFT)

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
        """Stop the running conversion."""
        self.is_running = False
        if self.converter:
            self.converter.is_running = False
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
                logger=self.logger,
                gui_callback=self.update_progress
            )
            self.converter.is_running = self.is_running
            self.converter.run()

            if self.is_running:
                converted = len(self.converter.converted_files)
                failed = len(self.converter.failed_files)
                skipped = len(self.converter.skipped_files)
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
        if self.is_running is False and self.converter:
            if self.converter.converted_files or self.converter.failed_files:
                self.status_var.set(t("status_complete"))
                self.progress_bar['value'] = 100


def main():
    root = tk.Tk()
    app = RawConverterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
