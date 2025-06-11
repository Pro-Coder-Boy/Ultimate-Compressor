import sys
import os
import subprocess
import shutil
import tempfile
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import ctypes
import threading
import logging
import uuid

# --- Conditional Logging Setup ---
_HAS_ERROR_OCCURRED = False
log_file_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'compressor_log.txt')

def setup_logging():
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.DEBUG, 
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename=log_file_path,
            filemode='w'
        )

def log_error(message, exc_info=False):
    global _HAS_ERROR_OCCURRED
    if not _HAS_ERROR_OCCURRED:
        setup_logging()
    _HAS_ERROR_OCCURRED = True
    logging.error(message, exc_info=exc_info)

try:
    from PIL import Image
    from PIL import BmpImagePlugin, IcoImagePlugin
except ImportError:
    log_error("Pillow library not found.")
    messagebox.showerror("Dependency Error", "The 'Pillow' library was not found.\nPlease install it by running: pip install Pillow")
    sys.exit(1)

# --- String Constants ---
STRINGS = {
    "app_title": "Ultimate Image Compressor", "status_ready": "Ready",
    "status_processing": "Processing file {current}/{total}: {filename}", "status_done": "Operation complete.",
    "status_estimating": "Estimating size...", "status_resized": "Resized to {w}x{h}",
    "status_finding_quality": "Finding best quality for < {size} KB...", "status_estimated_size": "Estimated size: ~{size:.1f} KB",
    "status_already_optimized": "Already Optimized", "error_title": "Error", "success_title": "Success",
    "report_title": "Compression Report", "unsupported_type": "Unsupported file type",
    "overwrite_format_error": "Cannot overwrite file when changing its format.", "resize_label": "1. Resize (Optional)",
    "width_label": "Width:", "height_label": "Height:", "original_dims_label": "Original:",
    "aspect_ratio_label": "Keep Aspect Ratio", "compression_label": "2. Compression Settings",
    "mode_quality": "Target Quality", "mode_size": "Target File Size (JPEG/WEBP only)",
    "quality_label": "Quality (1-100):", "size_label": "Target Size (KB):",
    "output_options_label": "3. Output Options", "output_dir_label": "Save to:",
    "suffix_label": "Filename Suffix (English only):", "output_format_label": "Convert Format:",
    "overwrite_label": "Overwrite original file", "keep_original_format": "Keep Original",
    "original_folder": "Original Folder", "compress_button": "Compress Files", "browse_button": "Browse...",
    "files_label": "Files to Process", "no_file_selected": "Please select a file from the list.",
    "headless_success": "{count} file(s) processed successfully.",
    "max_png_label": "Enable Maximum PNG Compression (Slow)",
    "auto_convert_png_label": "Auto-convert opaque PNG to JPG for best size"
}

# --- Helper & Core Logic ---
def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    # FIX: Make path resolution robust, independent of working directory
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Fallback for running as a script: use the script's own directory
        base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(base_path, relative_path)

def get_tool_path(tool_name):
    path = get_resource_path(os.path.join('tools', tool_name))
    if not os.path.exists(path):
        log_error(f"Tool not found at expected path: {path}")
        messagebox.showwarning(STRINGS["error_title"], f"{tool_name} not found. This feature will be disabled.")
        return None
    return path

class ImageProcessor:
    def __init__(self, status_callback=None): self.status_callback = status_callback
    def _update_status(self, message):
        if self.status_callback: self.status_callback(message)
    def _run_tool(self, command):
        tool_name = os.path.basename(command[0])
        try:
            result = subprocess.run(command, check=False, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if tool_name == 'pngquant.exe' and result.returncode in [98, 99]: return True, "Already Optimized"
            if result.returncode != 0: raise subprocess.CalledProcessError(result.returncode, command, output=result.stdout, stderr=result.stderr)
            return True, "Success"
        except subprocess.CalledProcessError as e:
            stderr_msg = e.stderr.decode(encoding='utf-8', errors='replace').strip() if e.stderr else ""
            stdout_msg = e.stdout.decode(encoding='utf-8', errors='replace').strip() if e.stdout else ""
            error_output = stderr_msg or stdout_msg or "No output from tool."
            full_error_msg = f"Error from {tool_name} (code {e.returncode}):\n{error_output}"; log_error(full_error_msg)
            return False, full_error_msg
        except FileNotFoundError: log_error(f"Tool not found: {tool_name}"); return False, f"Tool not found: {tool_name}"
        except Exception as e: log_error(f"An unexpected error occurred while running tool: {e}", exc_info=True); return False, str(e)
    def is_png_fully_opaque(self, file_path):
        try:
            with Image.open(file_path) as img:
                if img.mode == 'P':
                    if 'transparency' in img.info: return False
                if 'A' in img.getbands(): return not any(pixel < 255 for pixel in img.getchannel('A').getdata())
                return True
        except Exception as e: log_error(f"Could not check transparency for {os.path.basename(file_path)}: {e}"); return False
    def compress_jpeg(self, in_path, out_path, quality):
        cjpeg_path = get_tool_path('cjpeg.exe');
        if not cjpeg_path: return False, "cjpeg.exe not found."
        return self._run_tool([cjpeg_path, "-quality", str(quality), "-progressive", "-outfile", out_path, in_path])
    def compress_webp(self, in_path, out_path, quality):
        cwebp_path = get_tool_path('cwebp.exe');
        if not cwebp_path: return False, "cwebp.exe not found."
        return self._run_tool([cwebp_path, "-q", str(quality), in_path, "-o", out_path])
    def find_best_quality(self, in_path, target_kb, compress_func):
        self._update_status(STRINGS["status_finding_quality"].format(size=target_kb)); target_bytes = target_kb * 1024
        low, high, best_quality = 1, 100, -1
        for _ in range(8):
            if low > high: break
            q = (low + high) // 2
            with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as temp_out: temp_out_name = temp_out.name
            try:
                is_success, _ = compress_func(in_path, temp_out_name, q)
                if is_success and os.path.exists(temp_out_name):
                    if os.path.getsize(temp_out_name) <= target_bytes: best_quality, low = q, q + 1
                    else: high = q - 1
                else: high = q - 1
            finally:
                if os.path.exists(temp_out_name): os.remove(temp_out_name)
        return best_quality if best_quality != -1 else 1
    def compress_png(self, in_path, out_path, quality_range="60-80", use_zopfli=True):
        pngquant_path, zopflipng_path = get_tool_path('pngquant.exe'), get_tool_path('zopflipng.exe')
        if not pngquant_path or not zopflipng_path: return False, "PNG tools (pngquant/zopflipng) not found."
        temp_path = out_path if not use_zopfli else os.path.join(tempfile.gettempdir(), f"quant_{os.path.basename(out_path)}")
        try:
            p_command = [pngquant_path, '--force', '--strip', '--quality', quality_range, '--speed=1', '--output', temp_path, in_path]
            quant_success, quant_msg = self._run_tool(p_command)
            if not quant_success: return False, quant_msg
            if quant_msg == "Already Optimized":
                if not use_zopfli: shutil.copy2(in_path, out_path)
                else:
                    zopflipng_path = get_tool_path('zopflipng.exe')
                    if not zopflipng_path: return False, "zopflipng.exe not found."
                    z_command = [zopflipng_path, '-y', '--iterations=15', in_path, out_path]
                    return self._run_tool(z_command)
                return True, quant_msg
            if use_zopfli:
                zopflipng_path = get_tool_path('zopflipng.exe')
                if not zopflipng_path: return False, "zopflipng.exe not found."
                z_command = [zopflipng_path, '-y', '--iterations=15', temp_path, out_path]
                return self._run_tool(z_command)
            else: return True, "Success"
        finally:
            if use_zopfli and os.path.exists(temp_path): os.remove(temp_path)
    def _safe_copy_for_processing(self, file_path):
        try:
            file_path.encode('ascii'); return file_path, None
        except UnicodeEncodeError:
            _, ext = os.path.splitext(file_path)
            safe_name = f"temp_{uuid.uuid4().hex}{ext}"; safe_path = os.path.join(tempfile.gettempdir(), safe_name)
            shutil.copy2(file_path, safe_path)
            logging.info(f"Copied non-ASCII filename to safe temp path '{safe_path}'")
            return safe_path, safe_path
    def _convert_image(self, source_path, target_format):
        temp_converted_path = os.path.join(tempfile.gettempdir(), f"converted_{uuid.uuid4().hex}.{target_format}")
        with Image.open(source_path) as img:
            save_options = {}
            if target_format in ['jpeg', 'jpg']:
                if img.mode == 'RGBA': img = img.convert('RGB')
                save_options['quality'] = 98
            elif target_format == 'png':
                if img.mode != 'RGBA': img = img.convert('RGBA')
            img.save(temp_converted_path, **save_options)
        return temp_converted_path

    def process_file(self, file_path, options):
        original_basename = os.path.basename(file_path); file_name, file_ext_orig = os.path.splitext(original_basename)
        should_overwrite = options.get('overwrite', False)
        target_format_str = options.get("format", STRINGS["keep_original_format"])
        is_converting_format = target_format_str != STRINGS["keep_original_format"]
        target_format = target_format_str.lower() if is_converting_format else file_ext_orig.lower().replace('.', '')
        if options.get("auto_convert_png") and file_ext_orig.lower() == '.png' and not is_converting_format:
            if self.is_png_fully_opaque(file_path): target_format, is_converting_format = "jpeg", True
        if should_overwrite and is_converting_format:
            msg = STRINGS["overwrite_format_error"]; log_error(msg); return False, msg
        final_output_path = file_path if should_overwrite else os.path.join(
            options.get('output_dir', os.path.dirname(file_path)) if options.get('output_dir') != STRINGS["original_folder"] else os.path.dirname(file_path),
            f"{file_name}{options.get('suffix', '-tiny')}.{target_format}")
        with tempfile.NamedTemporaryFile(suffix=f".{target_format}", delete=False) as temp_out: temp_output_path = temp_out.name
        current_path, temp_files = file_path, [temp_output_path]
        try:
            current_path, safe_copy = self._safe_copy_for_processing(current_path)
            if safe_copy: temp_files.append(safe_copy)
            if options.get("resize_enabled") and options.get("width", 0) > 0 and options.get("height", 0) > 0:
                _, file_ext = os.path.splitext(current_path)
                temp_resized = os.path.join(tempfile.gettempdir(), f"resized_{uuid.uuid4().hex}{file_ext}")
                with Image.open(current_path) as img: img.resize((options["width"], options["height"]), Image.Resampling.LANCZOS).save(temp_resized)
                current_path, temp_files = temp_resized, temp_files + [temp_resized]
                self._update_status(STRINGS["status_resized"].format(w=options["width"], h=options["height"]))
            
            current_ext_no_dot = os.path.splitext(current_path)[1].lower().strip('.')
            if current_ext_no_dot != target_format:
                temp_converted = self._convert_image(current_path, target_format)
                current_path, temp_files = temp_converted, temp_files + [temp_converted]
                
            quality, is_success, message = options.get("quality", 75), False, "An unknown compression error occurred."
            if target_format in ['jpeg', 'jpg']:
                if options.get("mode") == "size": quality = self.find_best_quality(current_path, options["target_size"], self.compress_jpeg)
                is_success, message = self.compress_jpeg(current_path, temp_output_path, quality)
                if is_success: message = f"'{original_basename}' -> JPEG, quality {quality}."
            elif target_format == 'png':
                quality_range = f"{quality-10}-{quality}" if quality > 10 else f"0-{quality}"; use_zopfli = options.get("max_png", False)
                is_success, message = self.compress_png(current_path, temp_output_path, quality_range, use_zopfli=use_zopfli)
                if is_success and message == "Already Optimized": message = f"'{original_basename}' is already optimized."
                elif is_success: message = f"'{original_basename}' compressed to PNG."
            elif target_format == 'webp':
                if options.get("mode") == "size": quality = self.find_best_quality(current_path, options["target_size"], self.compress_webp)
                is_success, message = self.compress_webp(current_path, temp_output_path, quality)
                if is_success: message = f"'{original_basename}' -> WEBP, quality {quality}."
            elif target_format == 'ico':
                with Image.open(current_path) as img: img.save(temp_output_path, format='ICO', sizes=[(32,32), (48,48), (64,64)])
                is_success, message = True, f"'{original_basename}' -> ICO."
            else: return False, STRINGS["unsupported_type"]
            if is_success:
                if message != f"'{original_basename}' is already optimized.": shutil.move(temp_output_path, final_output_path)
                temp_files.remove(temp_output_path); return True, message
            else: return False, message
        except Exception as e: log_error(f"A fatal error occurred during processing: {e}", exc_info=True); return False, f"An unexpected error occurred: {e}"
        finally:
            for f in temp_files:
                if os.path.exists(f): os.remove(f)

# --- The GUI ---
class UltimateCompressorGUI(tk.Tk):
    def __init__(self, files):
        super().__init__(); self.files, self.processor, self.after_id = list(files), ImageProcessor(self.update_status), None
        self.original_dims, self.is_updating_dims = {}, False
        self.title(STRINGS["app_title"]); self.geometry("450x780"); self.minsize(420, 750)
        self.create_widgets(); self.toggle_comp_widgets()
        if self.files: self.file_listbox.select_set(0); self.on_file_select(None)
    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10"); main_frame.pack(fill=tk.BOTH, expand=True)
        self._create_file_list(main_frame); self._create_resize_frame(main_frame)
        self._create_compression_frame(main_frame); self._create_output_frame(main_frame)
        self.compress_button = ttk.Button(main_frame, text=STRINGS["compress_button"], command=self.start_compression); self.compress_button.pack(fill=tk.X, pady=15, ipady=5)
        self._create_status_bar(main_frame)
    def _create_file_list(self, parent):
        frame = ttk.LabelFrame(parent, text=STRINGS["files_label"], padding="10"); frame.pack(fill=tk.X, pady=5)
        self.file_listbox = tk.Listbox(frame, height=5, exportselection=False); self.file_listbox.pack(fill=tk.X, expand=True, side=tk.LEFT, pady=5, padx=5)
        for f in self.files: self.file_listbox.insert(tk.END, os.path.basename(f))
        self.file_listbox.bind('<<ListboxSelect>>', self.on_file_select)
    def _create_resize_frame(self, parent):
        frame = ttk.LabelFrame(parent, text=STRINGS["resize_label"], padding="10"); frame.pack(fill=tk.X, pady=5)
        self.resize_enabled, self.keep_aspect_ratio = tk.BooleanVar(), tk.BooleanVar(value=True)
        self.width_var, self.height_var = tk.IntVar(), tk.IntVar()
        self.width_var.trace_add("write", self.on_dimension_change); self.height_var.trace_add("write", self.on_dimension_change)
        ttk.Checkbutton(frame, text="Enable Resizing", variable=self.resize_enabled, command=self.toggle_resize_widgets).pack(anchor='w')
        widgets_frame = ttk.Frame(frame); widgets_frame.pack(fill=tk.X)
        ttk.Label(widgets_frame, text=STRINGS["width_label"]).grid(row=0, column=0, padx=5, pady=2, sticky='e')
        self.width_entry = ttk.Entry(widgets_frame, textvariable=self.width_var, width=8, state='disabled'); self.width_entry.grid(row=0, column=1, padx=5, pady=2)
        ttk.Label(widgets_frame, text=STRINGS["height_label"]).grid(row=1, column=0, padx=5, pady=2, sticky='e')
        self.height_entry = ttk.Entry(widgets_frame, textvariable=self.height_var, width=8, state='disabled'); self.height_entry.grid(row=1, column=1, padx=5, pady=2)
        self.original_dims_var = tk.StringVar(value="N/A"); ttk.Label(widgets_frame, text=STRINGS["original_dims_label"]).grid(row=0, column=2, padx=(10,5), pady=2, sticky='e')
        ttk.Label(widgets_frame, textvariable=self.original_dims_var).grid(row=0, column=3, padx=5, pady=2, sticky='w')
        self.aspect_ratio_cb = ttk.Checkbutton(widgets_frame, text=STRINGS["aspect_ratio_label"], variable=self.keep_aspect_ratio, state='disabled'); self.aspect_ratio_cb.grid(row=1, column=2, columnspan=2, sticky='w', padx=10)
    def _create_compression_frame(self, parent):
        frame = ttk.LabelFrame(parent, text=STRINGS["compression_label"], padding="10"); frame.pack(fill=tk.X, pady=5)
        self.comp_mode, self.quality_var, self.size_var = tk.StringVar(value="quality"), tk.IntVar(value=75), tk.IntVar(value=150)
        self.quality_var.trace_add("write", self.on_quality_change)
        self.auto_convert_png_var = tk.BooleanVar(value=True)
        self.auto_convert_png_check = ttk.Checkbutton(frame, text=STRINGS["auto_convert_png_label"], variable=self.auto_convert_png_var, command=self.on_quality_change)
        self.auto_convert_png_check.pack(anchor='w')
        ttk.Radiobutton(frame, text=STRINGS["mode_quality"], variable=self.comp_mode, value="quality", command=self.toggle_comp_widgets).pack(anchor='w')
        q_frame = ttk.Frame(frame, padding=(25, 0, 0, 0)); q_frame.pack(fill=tk.X)
        ttk.Label(q_frame, text=STRINGS["quality_label"]).pack(side=tk.LEFT, pady=2); self.quality_entry = ttk.Entry(q_frame, textvariable=self.quality_var, width=8); self.quality_entry.pack(side=tk.LEFT, padx=5, pady=2)
        self.max_png_var = tk.BooleanVar(value=False); self.max_png_check = ttk.Checkbutton(q_frame, text=STRINGS["max_png_label"], variable=self.max_png_var, command=self.on_quality_change); self.max_png_check.pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(frame, text=STRINGS["mode_size"], variable=self.comp_mode, value="size", command=self.toggle_comp_widgets).pack(anchor='w', pady=(5,0))
        s_frame = ttk.Frame(frame, padding=(25, 0, 0, 0)); s_frame.pack(fill=tk.X)
        ttk.Label(s_frame, text=STRINGS["size_label"]).pack(side=tk.LEFT, pady=2); self.size_entry = ttk.Entry(s_frame, textvariable=self.size_var, width=8); self.size_entry.pack(side=tk.LEFT, padx=5, pady=2)
    def _create_output_frame(self, parent):
        frame = ttk.LabelFrame(parent, text=STRINGS["output_options_label"], padding="10"); frame.pack(fill=tk.X, pady=5)
        self.overwrite_var = tk.BooleanVar(value=False); ttk.Checkbutton(frame, text=STRINGS["overwrite_label"], variable=self.overwrite_var, command=self.toggle_output_widgets).pack(anchor='w')
        self.output_widgets_frame = ttk.Frame(frame, padding=(0,5,0,0)); self.output_widgets_frame.pack(fill=tk.X)
        top_frame = ttk.Frame(self.output_widgets_frame); top_frame.pack(fill=tk.X)
        self.suffix_var = tk.StringVar(value="-tiny"); ttk.Label(top_frame, text=STRINGS["suffix_label"]).pack(side=tk.LEFT, padx=(0,5)); self.suffix_entry = ttk.Entry(top_frame, textvariable=self.suffix_var, width=15); self.suffix_entry.pack(side=tk.LEFT)
        self.format_var = tk.StringVar(value=STRINGS["keep_original_format"]); self.format_var.trace_add("write", self.on_quality_change)
        ttk.Label(top_frame, text=STRINGS["output_format_label"]).pack(side=tk.LEFT, padx=(15,5)); formats = [STRINGS["keep_original_format"], "JPEG", "PNG", "WEBP", "ICO"]; self.format_combo = ttk.Combobox(top_frame, textvariable=self.format_var, values=formats, state="readonly", width=15); self.format_combo.pack(side=tk.LEFT)
        dir_frame = ttk.Frame(self.output_widgets_frame); dir_frame.pack(fill=tk.X, pady=(5,0))
        self.output_dir_var = tk.StringVar(value=STRINGS["original_folder"]); ttk.Label(dir_frame, text=STRINGS["output_dir_label"]).pack(side=tk.LEFT, padx=(0,5))
        self.dir_entry = ttk.Entry(dir_frame, textvariable=self.output_dir_var, state='readonly'); self.dir_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.browse_btn = ttk.Button(dir_frame, text=STRINGS["browse_button"], command=self.browse_output_dir); self.browse_btn.pack(side=tk.LEFT, padx=(5,0))
    def _create_status_bar(self, parent):
        status_frame = ttk.Frame(parent, relief=tk.SUNKEN, padding=2); status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_var = tk.StringVar(value=STRINGS["status_ready"]); ttk.Label(status_frame, textvariable=self.status_var, anchor='w').pack(side=tk.LEFT)
        self.estimated_size_var = tk.StringVar(value=""); ttk.Label(status_frame, textvariable=self.estimated_size_var, anchor='e', font=("Segoe UI", 9, "bold"), foreground="blue").pack(side=tk.RIGHT)
    def on_dimension_change(self, *args):
        if self.is_updating_dims or not self.resize_enabled.get() or not self.keep_aspect_ratio.get(): return
        self.is_updating_dims = True
        try:
            widget, sel_idx = self.focus_get(), self.file_listbox.curselection()[0]; f_path = self.files[sel_idx]
            orig_w, orig_h = self.original_dims[f_path]
            if widget == self.width_entry: new_w = self.width_var.get();
            if new_w > 0: self.height_var.set(int(new_w * orig_h / orig_w))
            elif widget == self.height_entry: new_h = self.height_var.get();
            if new_h > 0: self.width_var.set(int(new_h * orig_w / orig_h))
            self.on_quality_change()
        except (IndexError, KeyError, ValueError, tk.TclError): pass
        finally: self.is_updating_dims = False
    def browse_output_dir(self):
        directory = filedialog.askdirectory(title="Select Output Folder");
        if directory: self.output_dir_var.set(directory)
    def toggle_resize_widgets(self):
        state = 'normal' if self.resize_enabled.get() else 'disabled';
        for w in [self.width_entry, self.height_entry, self.aspect_ratio_cb]: w.config(state=state)
        self.on_file_select(None)
    def _update_options_state(self):
        is_quality_mode = self.comp_mode.get() == "quality"
        try:
            sel_idx = self.file_listbox.curselection()[0]; f_path = self.files[sel_idx]
            target_format_str = self.format_var.get(); target_format = target_format_str.lower() if target_format_str != STRINGS["keep_original_format"] else os.path.splitext(f_path)[1].lower().replace('.', '')
            is_png_output = (target_format == 'png')
            self.max_png_check.config(state='normal' if is_png_output and is_quality_mode else 'disabled')
            is_png_input = os.path.splitext(f_path)[1].lower() == '.png'
            self.auto_convert_png_check.config(state='normal' if is_png_input else 'disabled')
            if not is_png_input: self.auto_convert_png_var.set(False)
        except IndexError:
            self.max_png_check.config(state='disabled'); self.auto_convert_png_check.config(state='disabled')
    def toggle_comp_widgets(self):
        is_quality_mode = self.comp_mode.get() == "quality";
        self.quality_entry.config(state='normal' if is_quality_mode else 'disabled');
        self.size_entry.config(state='disabled' if is_quality_mode else 'normal');
        self._update_options_state()
        if is_quality_mode: self.on_quality_change()
        else: self.estimated_size_var.set("")
    def toggle_output_widgets(self):
        state = 'disabled' if self.overwrite_var.get() else 'normal'
        for w in [self.suffix_entry, self.format_combo, self.dir_entry, self.browse_btn]: w.config(state=state)
    def on_quality_change(self, *args):
        self._update_options_state()
        if self.after_id: self.after_cancel(self.after_id)
        if self.comp_mode.get() == 'quality': self.after_id = self.after(500, self.start_estimation_thread)
    def on_file_select(self, event):
        try:
            sel_idx = self.file_listbox.curselection()[0]; f_path = self.files[sel_idx]
            with Image.open(f_path) as img:
                w, h = img.size; self.original_dims[f_path] = (w, h)
                self.original_dims_var.set(f"{w} x {h} px")
                if not self.resize_enabled.get(): self.width_var.set(w); self.height_var.set(h)
        except (IndexError, FileNotFoundError): self.original_dims_var.set("N/A")
        self._update_options_state()
        if self.comp_mode.get() == 'quality': self.on_quality_change()
    def start_estimation_thread(self):
        if not self.file_listbox.curselection(): return
        self.update_status(STRINGS["status_estimating"]); self.estimated_size_var.set("...")
        threading.Thread(target=self._run_estimation_in_thread, daemon=True).start()
    def _run_estimation_in_thread(self):
        try:
            sel_idx = self.file_listbox.curselection()[0]; f_path = self.files[sel_idx]; quality = self.quality_var.get()
            if not 1 <= quality <= 100: raise ValueError("Quality out of range")
            options = {"resize_enabled": self.resize_enabled.get(), "width": self.width_var.get(), "height": self.height_var.get()}
            target_format_str = self.format_var.get(); target_format = target_format_str.lower() if target_format_str != STRINGS["keep_original_format"] else os.path.splitext(f_path)[1].lower().replace('.', '')
            original_ext = os.path.splitext(f_path)[1].lower()
            if self.auto_convert_png_var.get() and original_ext == '.png':
                if self.processor.is_png_fully_opaque(f_path): target_format = "jpeg"
            current_path, temp_files = f_path, []
            safe_path, safe_copy = self.processor._safe_copy_for_processing(current_path)
            if safe_copy: current_path, temp_files = safe_path, temp_files + [safe_copy]
            if options["resize_enabled"] and options["width"] > 0 and options["height"] > 0:
                temp_resized = os.path.join(tempfile.gettempdir(), f"temp_estimate_{uuid.uuid4().hex}{original_ext}")
                with Image.open(current_path) as img: img.resize((options["width"], options["height"]), Image.Resampling.LANCZOS).save(temp_resized)
                current_path, temp_files = temp_resized, temp_files + [temp_resized]
            
            current_ext_no_dot = os.path.splitext(current_path)[1].lower().strip('.')
            if current_ext_no_dot != target_format:
                temp_converted = self.processor._convert_image(current_path, target_format)
                current_path = temp_converted; temp_files.append(temp_converted)

            with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as temp_out: temp_out_name = temp_out.name
            temp_files.append(temp_out_name)
            is_success, msg = False, ""
            if target_format in ['jpg', 'jpeg']: is_success, msg = self.processor.compress_jpeg(current_path, temp_out_name, quality)
            elif target_format == 'png':
                q_range = f"{quality-10}-{quality}" if quality > 10 else f"0-{quality}"; use_zopfli = self.max_png_var.get(); is_success, msg = self.processor.compress_png(current_path, temp_out_name, q_range, use_zopfli)
            elif target_format == 'webp': is_success, msg = self.processor.compress_webp(current_path, temp_out_name, quality)
            elif target_format == 'ico':
                with Image.open(current_path) as img: img.save(temp_out_name, format='ICO', sizes=[(32,32), (48,48), (64,64)]); is_success = True
            
            if is_success:
                if msg == "Already Optimized": self.after(0, self.update_estimated_size_label, os.path.getsize(current_path) / 1024)
                else: self.after(0, self.update_estimated_size_label, os.path.getsize(temp_out_name) / 1024)
            else: self.after(0, self.update_estimated_size_label, -1)
        except (IndexError, ValueError): self.after(0, self.update_estimated_size_label, -1)
        except Exception as e: log_error(f"Estimation Thread Error: {e}", exc_info=True); self.after(0, self.update_estimated_size_label, -1)
        finally:
            for f in temp_files:
                if os.path.exists(f): os.remove(f)
    def update_estimated_size_label(self, size_kb):
        if size_kb >= 0: self.estimated_size_var.set(f"~{size_kb:.1f} KB")
        else: self.estimated_size_var.set("Error")
        self.update_status(STRINGS["status_ready"])
    def start_compression(self):
        if not self.files: messagebox.showwarning("No Files", "Please add files to process."); return
        options = {"resize_enabled": self.resize_enabled.get(), "width": self.width_var.get(), "height": self.height_var.get(),
                   "keep_aspect_ratio": self.keep_aspect_ratio.get(), "mode": self.comp_mode.get(), "quality": self.quality_var.get(),
                   "target_size": self.size_var.get(), "output_dir": self.output_dir_var.get(), "suffix": self.suffix_var.get(),
                   "format": self.format_var.get(), "overwrite": self.overwrite_var.get(), "max_png": self.max_png_var.get(),
                   "auto_convert_png": self.auto_convert_png_var.get()}
        self.compress_button.config(state='disabled'); success_msgs, error_msgs = [], []
        for i, file_path in enumerate(self.files):
            self.update_status(STRINGS["status_processing"].format(current=i+1, total=len(self.files), filename=os.path.basename(file_path)))
            is_success, msg = self.processor.process_file(file_path, options); (success_msgs if is_success else error_msgs).append(msg)
        self.update_status(STRINGS["status_done"]); self.compress_button.config(state='normal')
        report = ""
        if success_msgs: report += f"Successfully processed {len(success_msgs)} file(s):\n" + "\n".join(success_msgs)
        if error_msgs:
            report += f"\n\nEncountered {len(error_msgs)} error(s):\n" + "\n".join(error_msgs); messagebox.showerror(STRINGS["report_title"], report)
        elif success_msgs: messagebox.showinfo(STRINGS["report_title"], report)
        self.destroy()
    def update_status(self, message): self.status_var.set(message); self.update_idletasks()

# --- Main Dispatcher ---
def main():
    is_shift_pressed = ctypes.windll.user32.GetAsyncKeyState(0x10) & 0x8000 != 0
    
    # FIX: Filter command-line arguments to only include actual files
    potential_files = sys.argv[1:]
    files_to_process = []
    for f in potential_files:
        # This filters out arguments like "--shift" and ensures the path is a file
        if os.path.isfile(f):
            files_to_process.append(f)

    if is_shift_pressed or not files_to_process:
        if not files_to_process:
            temp_root = tk.Tk()
            temp_root.withdraw()
            files_to_process = filedialog.askopenfilenames(
                parent=temp_root,
                title="Select Images to Compress",
                filetypes=[("Image Files", "*.jpg *.jpeg *.png *.webp")]
            )
            temp_root.destroy()
            if not files_to_process:
                return

        app = UltimateCompressorGUI(files_to_process)
        app.mainloop()
    else:
        processor = ImageProcessor()
        options = {"mode": "quality", "quality": 75, "resize_enabled": False, "output_dir": STRINGS["original_folder"], 
                   "suffix": "-tiny", "format": STRINGS["keep_original_format"], "overwrite": False, "max_png": False, "auto_convert_png": True} 
        success_count, error_msgs = 0, []
        for file_path in files_to_process:
            is_success, msg = processor.process_file(file_path, options)
            if is_success: success_count += 1
            else: error_msgs.append(f"- {os.path.basename(file_path)}:\n  {msg}")
        
        if not error_msgs and success_count > 0:
            messagebox.showinfo(STRINGS["success_title"], STRINGS["headless_success"].format(count=success_count))
        elif error_msgs:
            report = ""
            if success_count > 0: report += f"Successfully processed {success_count} file(s).\n\n"
            report += f"Encountered {len(error_msgs)} error(s):\n" + "\n".join(error_msgs)
            messagebox.showerror(STRINGS["report_title"], report)

if __name__ == "__main__":
    try: main()
    except Exception as e:
        log_error(f"A top-level exception occurred: {e}", exc_info=True)
        messagebox.showerror("Fatal Error", f"A fatal error occurred. Please check 'compressor_log.txt' for details.")
