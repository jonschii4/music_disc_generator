import os
import re
import json
import hashlib
import math
import time
import subprocess
import shutil
import sys
import traceback
import importlib
import tempfile
import zipfile
import urllib.request
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    Image = importlib.import_module("PIL.Image")
    ImageTk = importlib.import_module("PIL.ImageTk")
except ImportError:
    Image = ImageTk = None


# ============================================================
# TkinterDnD2 support
# ============================================================

HAS_DND = False
DND_FILES = None
TkinterDnD = None

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except Exception:
    HAS_DND = False


# ============================================================
# Minecraft languages
# ============================================================

MC_LANGUAGES = [
    "en_us",
    "de_de",
    "fr_fr",
    "es_es",
    "ja_jp",
    "ru_ru",
    "zh_cn",
    "pt_br",
    "it_it",
    "nl_nl",
    "pl_pl",
    "ko_kr"
]


# ============================================================
# Audio format colors
# ============================================================

AUDIO_FORMAT_COLORS = {
    ".ogg": ("#2e7d32", "OGG"),
    ".wav": ("#c62828", "WAV"),
    ".mp3": ("#1565c0", "MP3"),
    ".flac": ("#f57f17", "FLAC"),
    ".m4a": ("#6a1b9a", "M4A"),
    ".aac": ("#00838f", "AAC"),
    ".ogg_default": ("#424242", "AUDIO")
}

FFMPEG_DOWNLOAD_URL = (
    "https://www.gyan.dev/ffmpeg/builds/packages/"
    "ffmpeg-9.0.2-essentials_build.zip"
)
FFMPEG_DOWNLOAD_SHA256 = (
    "60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba"
)


# ============================================================
# Tooltip
# ============================================================

class ToolTip:
    """Creates a hover tooltip for a widget."""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None

        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return

        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background="#252526",
            foreground="#ffffff",
            relief=tk.SOLID,
            borderwidth=1,
            font=("Segoe UI", 9, "normal"),
            padx=6,
            pady=4
        )

        label.pack()

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


# ============================================================
# Music Disc Card
# ============================================================

class MusicDiscCard(ttk.LabelFrame):
    """UI Card representing an individual Music Disc entry."""

    def __init__(
        self,
        parent,
        card_id,
        remove_callback,
        app_reference,
        blank_text_fields=False
    ):
        super().__init__(
            parent,
            text=f" Music Disc #{card_id} ",
            padding=12
        )

        self.card_id = card_id
        self.remove_callback = remove_callback
        self.app = app_reference
        self.blank_text_fields = blank_text_fields

        self.lang_entries = []
        self.preview_photo = None
        self.recipe_config = {
            "type": "Crafting (Shaped)",
            "inputs": {},
        }

        self.setup_ui()

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------

    def setup_ui(self):

        btn_remove = ttk.Button(
            self,
            text="💿 -",
            command=lambda: self.remove_callback(self)
        )
        btn_remove.grid(
            row=0,
            column=3,
            sticky="e",
            pady=(0, 6)
        )

        lbl_desc_type = ttk.Label(
            self,
            text="Description Mode:",
            font=("Segoe UI", 9, "bold")
        )
        lbl_desc_type.grid(
            row=1,
            column=0,
            sticky="w",
            pady=(6, 4)
        )

        self.combo_desc_type = ttk.Combobox(
            self,
            values=["string", "lang"],
            state="readonly",
            width=12
        )
        self.combo_desc_type.set("string")
        self.combo_desc_type.grid(
            row=1,
            column=1,
            sticky="w",
            pady=(6, 4)
        )
        self.combo_desc_type.bind(
            "<<ComboboxSelected>>",
            self.on_desc_type_change
        )

        # ----------------------------------------------------
        # String description mode
        # ----------------------------------------------------

        self.frame_string_mode = ttk.Frame(self)
        self.frame_string_mode.grid(
            row=2,
            column=0,
            columnspan=4,
            sticky="ew",
            pady=4
        )

        lbl_string_val = ttk.Label(
            self.frame_string_mode,
            text="Description Text:"
        )
        lbl_string_val.pack(
            side=tk.LEFT,
            padx=(0, 10)
        )

        self.entry_string_desc = tk.Entry(
            self.frame_string_mode,
            width=40
        )
        if not self.blank_text_fields:
            self.entry_string_desc.insert(
                0,
                "Author - Title"
            )
        self.entry_string_desc.pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True
        )

        # ----------------------------------------------------
        # Language localization mode
        # ----------------------------------------------------

        self.frame_lang_mode = ttk.Frame(self)

        lbl_lang_info = ttk.Label(
            self.frame_lang_mode,
            text="Language Translations:",
            font=("Segoe UI", 9, "bold")
        )
        lbl_lang_info.pack(
            anchor="w",
            pady=(2, 4)
        )

        self.lang_container = ttk.Frame(
            self.frame_lang_mode
        )
        self.lang_container.pack(
            fill=tk.X,
            expand=True,
            pady=2
        )

        btn_add_lang = ttk.Button(
            self.frame_lang_mode,
            text="+ Add Language Entry",
            command=self.add_lang_row
        )
        btn_add_lang.pack(
            anchor="w",
            pady=(4, 6)
        )

        self.add_lang_row(
            default_lang="en_us",
            blank_fields=self.blank_text_fields
        )

        # ----------------------------------------------------
        # Comparator output
        # ----------------------------------------------------

        lbl_comp = ttk.Label(
            self,
            text="Comparator Output:"
        )
        lbl_comp.grid(
            row=4,
            column=0,
            sticky="w",
            pady=4
        )

        self.combo_comp = ttk.Combobox(
            self,
            values=[str(i) for i in range(16)],
            state="readonly",
            width=10
        )
        self.combo_comp.current(15)
        self.combo_comp.grid(
            row=4,
            column=1,
            sticky="w",
            pady=4
        )

        # ----------------------------------------------------
        # Sound file
        # ----------------------------------------------------

        lbl_sound = ttk.Label(
            self,
            text="Sound File:"
        )
        lbl_sound.grid(
            row=5,
            column=0,
            sticky="w",
            pady=4
        )

        sound_input_frame = ttk.Frame(self)
        sound_input_frame.grid(
            row=5,
            column=1,
            sticky="ew",
            pady=4,
            padx=(0, 5)
        )

        self.lbl_sound_icon = tk.Label(
            sound_input_frame,
            text="🎵",
            font=("Segoe UI Symbol", 12),
            fg="#4e9a06"
        )
        self.lbl_sound_icon.pack(
            side=tk.LEFT,
            padx=(0, 6)
        )

        self.entry_sound = tk.Entry(
            sound_input_frame
        )
        self.entry_sound.pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True
        )
        self.entry_sound.bind(
            "<KeyRelease>",
            self.update_sound_icon
        )

        btn_browse_sound = ttk.Button(
            self,
            text="Browse...",
            command=self.browse_sound
        )
        btn_browse_sound.grid(
            row=5,
            column=2,
            sticky="e",
            pady=4
        )

        # ----------------------------------------------------
        # Sound range
        # ----------------------------------------------------

        lbl_range = ttk.Label(
            self,
            text="Sound Range:"
        )
        lbl_range.grid(
            row=6,
            column=0,
            sticky="w",
            pady=4
        )

        self.entry_range = tk.Entry(self)
        self.entry_range.insert(0, "16")
        self.entry_range.grid(
            row=6,
            column=1,
            columnspan=2,
            sticky="ew",
            pady=4
        )

        # ----------------------------------------------------
        # Texture
        # ----------------------------------------------------

        lbl_texture = ttk.Label(
            self,
            text="Texture File:"
        )
        lbl_texture.grid(
            row=7,
            column=0,
            sticky="w",
            pady=4
        )

        texture_input_frame = ttk.Frame(self)
        texture_input_frame.grid(
            row=7,
            column=1,
            sticky="ew",
            pady=4,
            padx=(0, 5)
        )

        self.entry_texture = tk.Entry(
            texture_input_frame
        )
        self.entry_texture.pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True
        )
        self.entry_texture.bind(
            "<KeyRelease>",
            self.update_texture_preview
        )

        btn_browse_texture = ttk.Button(
            self,
            text="Browse...",
            command=self.browse_texture
        )
        btn_browse_texture.grid(
            row=7,
            column=2,
            sticky="e",
            pady=4
        )

        self.preview_canvas = tk.Canvas(
            self,
            width=32,
            height=32,
            bg="#1e1e1e",
            highlightthickness=1,
            highlightbackground="#3c3c3c"
        )
        self.preview_canvas.grid(
            row=7,
            column=3,
            padx=(12, 0),
            pady=4
        )

        ToolTip(
            self.preview_canvas,
            "Disc Texture Preview (32x32)"
        )

        # ----------------------------------------------------
        # Namespace
        # ----------------------------------------------------

        lbl_namespace = ttk.Label(
            self,
            text="Namespace:"
        )
        lbl_namespace.grid(
            row=8,
            column=0,
            sticky="w",
            pady=4
        )

        self.entry_namespace = tk.Entry(self)
        self.entry_namespace.insert(
            0,
            "custom_discs"
        )
        self.entry_namespace.grid(
            row=8,
            column=1,
            columnspan=2,
            sticky="ew",
            pady=4
        )
        self.entry_namespace.bind(
            "<KeyRelease>",
            lambda event: self.app.update_recipe_disc_dropdown()
        )

        ToolTip(
            self.entry_namespace,
            "Must be lower_case_only without spaces or special characters"
        )

        # ----------------------------------------------------
        # Options
        # ----------------------------------------------------

        options_frame = ttk.LabelFrame(
            self,
            text=" Disc Configurations ",
            padding=8
        )
        options_frame.grid(
            row=9,
            column=0,
            columnspan=4,
            sticky="ew",
            pady=(10, 4)
        )

        self.var_create_func = tk.BooleanVar(
            value=True
        )

        ttk.Checkbutton(
            options_frame,
            text="Create Function File",
            variable=self.var_create_func
        ).pack(
            anchor="w",
            pady=2
        )

        self.var_recipe = tk.BooleanVar(
            value=False
        )

        ttk.Checkbutton(
            options_frame,
            text="Enable Custom Recipe",
            variable=self.var_recipe,
            command=self.app.update_recipe_tab_visibility
        ).pack(
            anchor="w",
            pady=2
        )

        self.var_creeper_loot = tk.BooleanVar(
            value=False
        )

        ttk.Checkbutton(
            options_frame,
            text="Generate Creeper Loot Table Template",
            variable=self.var_creeper_loot
        ).pack(
            anchor="w",
            pady=2
        )

        self.columnconfigure(
            1,
            weight=1
        )

        # ----------------------------------------------------
        # Drag & Drop
        # ----------------------------------------------------

        if HAS_DND and getattr(
            self.app,
            "dnd_enabled",
            False
        ):
            try:
                self.entry_sound.drop_target_register(
                    DND_FILES
                )
                self.entry_sound.dnd_bind(
                    "<<Drop>>",
                    self.on_drop_sound
                )

                self.entry_texture.drop_target_register(
                    DND_FILES
                )
                self.entry_texture.dnd_bind(
                    "<<Drop>>",
                    self.on_drop_texture
                )

                self.drop_target_register(
                    DND_FILES
                )
                self.dnd_bind(
                    "<<Drop>>",
                    self.on_drop_card_generic
                )
            except Exception:
                pass

    # --------------------------------------------------------
    # Description mode
    # --------------------------------------------------------

    def on_desc_type_change(self, event=None):

        mode = self.combo_desc_type.get()

        if mode == "string":
            self.frame_lang_mode.grid_forget()

            self.frame_string_mode.grid(
                row=2,
                column=0,
                columnspan=4,
                sticky="ew",
                pady=4
            )

        else:
            self.frame_string_mode.grid_forget()

            self.frame_lang_mode.grid(
                row=2,
                column=0,
                columnspan=4,
                sticky="ew",
                pady=4
            )

    # --------------------------------------------------------
    # Sound icon
    # --------------------------------------------------------

    def update_sound_icon(self, event=None):

        path = (
            self.entry_sound
            .get()
            .strip()
            .strip('"{}\'')
        )

        ext = os.path.splitext(path)[1].lower()

        color, label = AUDIO_FORMAT_COLORS.get(
            ext,
            AUDIO_FORMAT_COLORS[".ogg_default"]
        )

        self.lbl_sound_icon.config(
            fg=color
        )

        ToolTip(
            self.lbl_sound_icon,
            f"Format: {label}" if ext else "Audio File Icon"
        )

    # --------------------------------------------------------
    # Texture preview
    # --------------------------------------------------------

    def update_texture_preview(self, event=None):

        path = (
            self.entry_texture
            .get()
            .strip()
            .strip('"{}\'')
        )

        self.preview_canvas.delete("all")

        if (
            Image is not None
            and ImageTk is not None
            and
            os.path.exists(path)
            and path.lower().endswith(".png")
        ):
            try:
                img = Image.open(path).convert("RGBA")

                img = img.resize(
                    (32, 32),
                    Image.Resampling.NEAREST
                )

                self.preview_photo = ImageTk.PhotoImage(
                    img
                )

                self.preview_canvas.create_image(
                    16,
                    16,
                    image=self.preview_photo
                )

            except Exception:
                self.preview_canvas.create_text(
                    16,
                    16,
                    text="ERR",
                    fill="#ff5555",
                    font=("Segoe UI", 8, "bold")
                )

        else:
            self.preview_canvas.create_text(
                16,
                16,
                text="None",
                fill="#888888",
                font=("Segoe UI", 7)
            )

    # --------------------------------------------------------
    # Drag & drop
    # --------------------------------------------------------

    def on_drop_sound(self, event):

        files = self.parse_dnd_files(
            event.data
        )

        if files:
            self.entry_sound.delete(
                0,
                tk.END
            )

            self.entry_sound.insert(
                0,
                files[0]
            )

            self.update_sound_icon()

    def on_drop_texture(self, event):

        files = self.parse_dnd_files(
            event.data
        )

        if files:
            self.entry_texture.delete(
                0,
                tk.END
            )

            self.entry_texture.insert(
                0,
                files[0]
            )

            self.update_texture_preview()

    def on_drop_card_generic(self, event):

        files = self.parse_dnd_files(
            event.data
        )

        for f in files:

            ext = os.path.splitext(
                f
            )[1].lower()

            if ext in [
                ".ogg",
                ".mp3",
                ".wav",
                ".flac",
                ".m4a"
            ]:
                self.entry_sound.delete(
                    0,
                    tk.END
                )

                self.entry_sound.insert(
                    0,
                    f
                )

                self.update_sound_icon()

            elif ext == ".png":
                self.entry_texture.delete(
                    0,
                    tk.END
                )

                self.entry_texture.insert(
                    0,
                    f
                )

                self.update_texture_preview()

    def parse_dnd_files(self, data):

        if not data:
            return []

        pattern = r'\{([^}]+)\}|(\S+)'

        matches = re.findall(
            pattern,
            data
        )

        return [
            m[0] if m[0] else m[1]
            for m in matches
        ]

    # --------------------------------------------------------
    # Language rows
    # --------------------------------------------------------

    def add_lang_row(self, default_lang=None, blank_fields=False):

        frame = ttk.Frame(
            self.lang_container
        )
        frame.pack(
            fill=tk.X,
            pady=2
        )

        lang_combo = ttk.Combobox(
            frame,
            values=MC_LANGUAGES,
            state="readonly",
            width=8
        )

        lang_combo.set(
            default_lang
            if default_lang in MC_LANGUAGES
            else "en_us"
        )

        lang_combo.pack(
            side=tk.LEFT,
            padx=(0, 5)
        )

        key_entry = tk.Entry(
            frame,
            width=24
        )

        if not blank_fields:
            key_entry.insert(
                0,
                f"item.custom_discs.disc_{self.card_id}.desc"
            )

        key_entry.pack(
            side=tk.LEFT,
            padx=(0, 5)
        )

        val_entry = tk.Entry(
            frame,
            width=22
        )

        if not blank_fields:
            val_entry.insert(
                0,
                "Author - Title"
            )

        val_entry.pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True,
            padx=(0, 5)
        )

        entry_dict = {
            "frame": frame,
            "lang": lang_combo,
            "key": key_entry,
            "val": val_entry
        }

        btn_remove = ttk.Button(
            frame,
            text="X",
            width=3,
            command=lambda: self.remove_lang_row(
                frame,
                entry_dict
            )
        )

        btn_remove.pack(
            side=tk.RIGHT
        )

        self.lang_entries.append(
            entry_dict
        )

    def remove_lang_row(
        self,
        frame,
        entry_dict
    ):

        if len(self.lang_entries) <= 1:
            messagebox.showwarning(
                "Warning",
                "Language mode requires at least one translation entry."
            )
            return

        frame.destroy()

        self.lang_entries.remove(
            entry_dict
        )

    # --------------------------------------------------------
    # File dialogs
    # --------------------------------------------------------

    def browse_sound(self):

        filename = filedialog.askopenfilename(
            title="Select Sound File",
            filetypes=[
                (
                    "Audio Files",
                    "*.ogg *.mp3 *.wav *.flac *.m4a"
                ),
                (
                    "All Files",
                    "*.*"
                )
            ]
        )

        if filename:
            self.entry_sound.delete(
                0,
                tk.END
            )

            self.entry_sound.insert(
                0,
                filename
            )

            self.update_sound_icon()

    def browse_texture(self):

        filename = filedialog.askopenfilename(
            title="Select Texture File",
            filetypes=[
                (
                    "PNG Files",
                    "*.png"
                ),
                (
                    "All Files",
                    "*.*"
                )
            ]
        )

        if filename:
            self.entry_texture.delete(
                0,
                tk.END
            )

            self.entry_texture.insert(
                0,
                filename
            )

            self.update_texture_preview()


# ============================================================
# Main Application
# ============================================================

# IMPORTANT:
# If tkinterdnd2 is installed, inherit from TkinterDnD.Tk.
# Otherwise inherit from normal tk.Tk.
#
# This fixes the original initialization problem where the
# application inherited from tk.Tk but manually initialized
# TkinterDnD.Tk.

if HAS_DND:
    BaseTk = TkinterDnD.Tk
else:
    BaseTk = tk.Tk


class MusicDiscMakerApp(BaseTk):

    def __init__(self):

        # Properly initialize the selected Tk base class.
        super().__init__()

        self.dnd_enabled = HAS_DND

        self.title(
            "Minecraft Music Disc Maker v1.0"
        )

        self.geometry(
            "860x940"
        )

        self.minsize(
            760,
            800
        )

        # ----------------------------------------------------
        # Theme
        # ----------------------------------------------------

        self.style = ttk.Style()

        try:
            if "clam" in self.style.theme_names():
                self.style.theme_use("clam")
        except Exception:
            pass

        self.style.configure(
            ".",
            background="#111111",
            foreground="#ffffff",
            fieldbackground="#242424",
            darkcolor="#080808",
            lightcolor="#777777",
            bordercolor="#555555"
        )

        self.style.configure(
            "TNotebook",
            background="#111111",
            borderwidth=0
        )

        self.style.configure(
            "TNotebook.Tab",
            background="#242424",
            foreground="#ffffff",
            padding=[14, 8],
            font=("Segoe UI", 10, "bold")
        )

        self.style.map(
            "TNotebook.Tab",
            background=[
                ("selected", "#3d8b45"),
                ("active", "#333333")
            ],
            foreground=[
                ("selected", "#ffffff")
            ]
        )

        self.style.configure(
            "TButton",
            background="#333333",
            foreground="#ffffff",
            borderwidth=1,
            focusthickness=2,
            focuscolor="#79c66b",
            font=("Segoe UI", 9, "bold")
        )

        self.style.map(
            "TButton",
            background=[
                ("active", "#4a4a4a"),
                ("pressed", "#222222")
            ],
            foreground=[
                ("active", "#ffffff")
            ]
        )

        self.style.configure(
            "TLabelframe",
            background="#111111",
            foreground="#ffffff",
            bordercolor="#555555"
        )

        self.style.configure(
            "TLabelframe.Label",
            background="#111111",
            foreground="#ffffff",
            font=("Segoe UI", 10, "bold")
        )

        self.style.configure(
            "TLabel",
            background="#111111",
            foreground="#ffffff",
            font=("Segoe UI", 9)
        )

        # Keep readonly Combobox selections visible when the dropdown
        # is closed, including when the widget does not have focus.
        self.style.configure(
            "TCombobox",
            foreground="#ffffff",
            fieldbackground="#242424",
            background="#333333"
        )

        self.style.map(
            "TCombobox",
            foreground=[
                ("readonly", "#ffffff"),
                ("disabled", "#aaaaaa")
            ],
            fieldbackground=[
                ("readonly", "#242424"),
                ("disabled", "#1a1a1a")
            ]
        )

        self.style.configure(
            "TCheckbutton",
            background="#111111",
            foreground="#ffffff",
            indicatorcolor="#242424",
            font=("Segoe UI", 9)
        )

        self.style.map(
            "TCheckbutton",
            background=[
                ("active", "#111111")
            ],
            indicatorcolor=[
                (("selected",), "#3d8b45"),
                (("!selected",), "#242424")
            ]
        )

        self.configure(
            bg="#111111"
        )

        # ----------------------------------------------------
        # Application state
        # ----------------------------------------------------

        self.disc_cards = []
        self.card_counter = 0
        self.last_add_time = 0.0

        # ----------------------------------------------------
        # Build UI
        # ----------------------------------------------------

        self.setup_ui()

    # ========================================================
    # Main UI
    # ========================================================

    def setup_ui(self):

        master_frame = ttk.Frame(
            self,
            padding=12
        )

        master_frame.pack(
            fill=tk.BOTH,
            expand=True
        )

        header = tk.Frame(
            master_frame,
            bg="#2e7d32",
            padx=18,
            pady=12,
            highlightbackground="#81c784",
            highlightthickness=1
        )
        header.pack(fill=tk.X, pady=(0, 12))

        tk.Label(
            header,
            text="💿  MUSIC DISC MAKER",
            bg="#2e7d32",
            fg="#ffffff",
            font=("Segoe UI", 14, "bold")
        ).pack(side=tk.LEFT)

        tk.Label(
            header,
            text="Build a soundtrack for your world",
            bg="#2e7d32",
            fg="#e8f5e9",
            font=("Segoe UI", 9)
        ).pack(side=tk.RIGHT, padx=(8, 0))

        self.notebook = ttk.Notebook(
            master_frame
        )

        self.notebook.pack(
            fill=tk.BOTH,
            expand=True
        )

        # ----------------------------------------------------
        # Music Disc tab
        # ----------------------------------------------------

        self.tab_discs = ttk.Frame(
            self.notebook,
            padding=10
        )

        self.notebook.add(
            self.tab_discs,
            text=" 🎵 Music Discs "
        )

        # ----------------------------------------------------
        # Recipe tab
        # ----------------------------------------------------

        self.tab_recipe = ttk.Frame(
            self.notebook,
            padding=15
        )

        # ----------------------------------------------------
        # Settings tab
        # ----------------------------------------------------

        self.tab_settings = ttk.Frame(
            self.notebook,
            padding=15
        )

        self.notebook.add(
            self.tab_settings,
            text=" ⚙ Settings "
        )

        self.setup_settings_tab()
        self.setup_discs_tab()
        self.setup_recipe_tab()

        # ----------------------------------------------------
        # Bottom action bar
        # ----------------------------------------------------

        action_frame = ttk.Frame(
            master_frame,
            padding=(0, 12, 0, 0)
        )

        action_frame.pack(
            fill=tk.X
        )

        generate_frame = ttk.Frame(action_frame)
        generate_frame.pack(anchor="center")

        self.btn_generate = tk.Canvas(
            generate_frame,
            width=300,
            height=50,
            bg="#111111",
            highlightthickness=0,
            cursor="hand2",
            takefocus=True
        )

        self._draw_generate_button("#43a047")

        self.generate_progress = ttk.Progressbar(
            generate_frame,
            mode="determinate",
            maximum=100,
            style="Generate.Horizontal.TProgressbar"
        )
        self.generate_progress["value"] = 0
        self.generate_progress.pack(
            fill=tk.X,
            pady=(0, 6)
        )
        self.generate_progress.pack_forget()

        self.btn_generate.pack()

        self.style.configure(
            "Generate.Horizontal.TProgressbar",
            troughcolor="#242424",
            background="#43a047",
            bordercolor="#555555",
            lightcolor="#66bb6a",
            darkcolor="#2e7d32"
        )

        # Add first disc.
        self.add_disc_card()

    # ========================================================
    # Settings
    # ========================================================

    def setup_settings_tab(self):

        lbl_format_header = ttk.Label(
            self.tab_settings,
            text="Minecraft Format & Target Version:",
            font=("Segoe UI", 10, "bold")
        )

        lbl_format_header.pack(
            anchor="w",
            pady=(0, 5)
        )

        format_options = [
            "1.21.1",
            "1.21.2",
            "1.21.3",
            "1.21.4",
            "26.0",
            "26.1",
            "26.2",
            "26.3 (Latest)"
        ]

        self.combo_format = ttk.Combobox(
            self.tab_settings,
            values=format_options,
            state="readonly",
            width=25
        )

        self.combo_format.current(
            len(format_options) - 1
        )

        self.combo_format.pack(
            anchor="w",
            pady=(0, 15)
        )

        lbl_pack_name = ttk.Label(
            self.tab_settings,
            text="Pack Name:",
            font=("Segoe UI", 9, "bold")
        )
        lbl_pack_name.pack(
            anchor="w",
            pady=(0, 5)
        )

        self.entry_pack_name = ttk.Entry(
            self.tab_settings,
            width=35
        )
        self.entry_pack_name.insert(0, "music_disc_pack")
        self.entry_pack_name.pack(
            anchor="w",
            pady=(0, 10)
        )

        ttk.Separator(
            self.tab_settings,
            orient="horizontal"
        ).pack(
            fill=tk.X,
            pady=10
        )

        lbl_build_opts = ttk.Label(
            self.tab_settings,
            text="Package Build Options:",
            font=("Segoe UI", 10, "bold")
        )

        lbl_build_opts.pack(
            anchor="w",
            pady=(0, 10)
        )

        self.var_gen_zip = tk.BooleanVar(
            value=True
        )

        self.var_convert_ffmpeg = tk.BooleanVar(
            value=True
        )

        self.var_legacy_datapack = tk.BooleanVar(
            value=False
        )

        ttk.Checkbutton(
            self.tab_settings,
            text="Generate ZIP Archive File",
            variable=self.var_gen_zip
        ).pack(
            anchor="w",
            pady=4
        )

        convert_ffmpeg_checkbox = ttk.Checkbutton(
            self.tab_settings,
            text="Convert Audio Files automatically (FFmpeg; download if missing)",
            variable=self.var_convert_ffmpeg
        )
        convert_ffmpeg_checkbox.pack(
            anchor="w",
            pady=4
        )
        ToolTip(
            convert_ffmpeg_checkbox,
            "If FFmpeg is not installed, download a portable copy beside "
            "this script the first time audio conversion is needed."
        )

        ttk.Checkbutton(
            self.tab_settings,
            text="Use Legacy Datapack Format Structure",
            variable=self.var_legacy_datapack
        ).pack(
            anchor="w",
            pady=4
        )

    # ========================================================
    # Music Disc tab
    # ========================================================

    def setup_discs_tab(self):

        container = ttk.Frame(
            self.tab_discs
        )

        container.pack(
            fill=tk.BOTH,
            expand=True
        )

        self.canvas = tk.Canvas(
            container,
            bg="#1d2b24",
            highlightthickness=0
        )

        scrollbar = ttk.Scrollbar(
            container,
            orient="vertical",
            command=self.canvas.yview
        )

        self.scroll_frame = ttk.Frame(
            self.canvas
        )

        self.btn_add_disc = ttk.Button(
            self.scroll_frame,
            text="💿 +",
            width=8,
            command=self.add_disc_card_debounced
        )
        self.btn_add_disc.pack(
            pady=(2, 8)
        )
        self.btn_add_disc.bind("<Enter>", self.show_add_disc_tooltip)
        self.btn_add_disc.bind("<Leave>", self.hide_add_disc_tooltip)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window(
            (0, 0),
            window=self.scroll_frame,
            anchor="nw"
        )

        self.canvas.configure(
            yscrollcommand=scrollbar.set
        )

        self.canvas.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True
        )

        scrollbar.pack(
            side=tk.RIGHT,
            fill=tk.Y
        )

    # ========================================================
    # Recipe tab
    # ========================================================

    def setup_recipe_tab(self):

        top_frame = ttk.Frame(
            self.tab_recipe
        )

        top_frame.pack(
            fill=tk.X,
            pady=(0, 10)
        )

        lbl_target = ttk.Label(
            top_frame,
            text="Output Music Disc:",
            font=("Segoe UI", 9, "bold")
        )

        lbl_target.grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 10)
        )

        self.combo_recipe_disc = ttk.Combobox(
            top_frame,
            state="readonly",
            width=30
        )
        self.combo_recipe_disc.bind(
            "<<ComboboxSelected>>",
            self.on_recipe_disc_selected
        )

        self.combo_recipe_disc.grid(
            row=0,
            column=1,
            sticky="w",
            pady=5
        )

        lbl_type = ttk.Label(
            top_frame,
            text="Recipe Type:",
            font=("Segoe UI", 9, "bold")
        )

        lbl_type.grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 10)
        )

        self.recipe_types = [
            "Crafting (Shaped)",
            "Crafting (Shapeless)",
            "Smelting (Furnace)",
            "Blast Furnace",
            "Smoker"
        ]

        self.combo_recipe_type = ttk.Combobox(
            top_frame,
            values=self.recipe_types,
            state="readonly",
            width=30
        )

        self.combo_recipe_type.current(0)

        self.combo_recipe_type.grid(
            row=1,
            column=1,
            sticky="w",
            pady=5
        )

        self.combo_recipe_type.bind(
            "<<ComboboxSelected>>",
            self.on_recipe_type_selected
        )

        ttk.Separator(
            self.tab_recipe,
            orient="horizontal"
        ).pack(
            fill=tk.X,
            pady=10
        )

        self.gui_container = ttk.Frame(
            self.tab_recipe
        )

        self.gui_container.pack(
            fill=tk.BOTH,
            expand=True
        )

        self.grid_entries = []
        self._recipe_dropdown_cards = []
        self.active_recipe_card = None
        self.active_recipe_type = self.combo_recipe_type.get()

        self.render_recipe_gui()

    # ========================================================
    # Recipe visibility
    # ========================================================

    def update_recipe_tab_visibility(self):

        has_recipe = any(
            card.var_recipe.get()
            for card in self.disc_cards
        )

        tabs = self.notebook.tabs()

        tab_recipe_id = str(
            self.tab_recipe
        )

        if has_recipe and tab_recipe_id not in tabs:

            self.notebook.insert(
                1,
                self.tab_recipe,
                text=" 📖 Recipes "
            )

        elif not has_recipe and tab_recipe_id in tabs:

            self.notebook.forget(
                self.tab_recipe
            )

        self.update_recipe_disc_dropdown()

    # ========================================================
    # Recipe dropdown
    # ========================================================

    def update_recipe_disc_dropdown(self):
        if (
            self.active_recipe_card is not None
            and self.active_recipe_card in self.disc_cards
        ):
            self._save_visible_recipe()

        selected_card = self.active_recipe_card
        self._recipe_dropdown_cards = [
            card for card in self.disc_cards if card.var_recipe.get()
        ]
        disc_names = [
            f"Music Disc #{card.card_id} ({card.entry_namespace.get()})"
            for card in self._recipe_dropdown_cards
        ]
        self.combo_recipe_disc["values"] = disc_names

        if not self._recipe_dropdown_cards:
            self.combo_recipe_disc.set("")
            self.active_recipe_card = None
            self._clear_recipe_editor()
            return

        if selected_card not in self._recipe_dropdown_cards:
            selected_card = self._recipe_dropdown_cards[0]

        selected_index = self._recipe_dropdown_cards.index(selected_card)
        self.combo_recipe_disc.current(selected_index)
        if selected_card is not self.active_recipe_card:
            self._load_recipe_for_card(selected_card)

    # ========================================================
    # Recipe GUI
    # ========================================================

    def render_recipe_gui(self, event=None):

        for widget in self.gui_container.winfo_children():
            widget.destroy()

        self.grid_entries.clear()

        selected_type = self.active_recipe_type

        if selected_type == "Crafting (Shaped)":
            config = self._recipe_config_for(self.active_recipe_card)
            saved_grid = config["inputs"].get(selected_type)

            grid_frame = ttk.Frame(
                self.gui_container
            )

            grid_frame.pack(
                anchor="w"
            )

            for r in range(3):

                row_entries = []

                for c in range(3):

                    entry = tk.Entry(
                        grid_frame,
                        width=20,
                        justify="center"
                    )

                    value = (
                        saved_grid[r][c]
                        if saved_grid
                        else "minecraft:air"
                    )
                    entry.insert(0, value)

                    entry.grid(
                        row=r,
                        column=c,
                        padx=4,
                        pady=4
                    )

                    row_entries.append(
                        entry
                    )

                self.grid_entries.append(
                    row_entries
                )

        else:
            config = self._recipe_config_for(self.active_recipe_card)
            saved_ingredient = config["inputs"].get(
                selected_type,
                "minecraft:raw_gold"
            )

            furnace_frame = ttk.Frame(
                self.gui_container
            )

            furnace_frame.pack(
                anchor="w"
            )

            ttk.Label(
                furnace_frame,
                text="Input Item ID:"
            ).grid(
                row=0,
                column=0,
                sticky="w",
                pady=4
            )

            entry_in = tk.Entry(
                furnace_frame,
                width=32
            )

            entry_in.insert(0, saved_ingredient)

            entry_in.grid(
                row=0,
                column=1,
                sticky="w",
                pady=4,
                padx=5
            )

            self.grid_entries.append(
                entry_in
            )

    def _recipe_config_for(self, card):
        if card is None:
            return {"type": self.combo_recipe_type.get(), "inputs": {}}
        return card.recipe_config

    def _save_visible_recipe(self):
        card = self.active_recipe_card
        if card is None or not self.grid_entries:
            return

        config = self._recipe_config_for(card)
        selected_type = self.active_recipe_type
        if selected_type == "Crafting (Shaped)":
            config["inputs"][selected_type] = [
                [entry.get() for entry in row]
                for row in self.grid_entries
            ]
        else:
            config["inputs"][selected_type] = self.grid_entries[0].get()
        config["type"] = selected_type

    def _clear_recipe_editor(self):
        for widget in self.gui_container.winfo_children():
            widget.destroy()
        self.grid_entries.clear()

    def _load_recipe_for_card(self, card):
        self.active_recipe_card = card
        config = self._recipe_config_for(card)
        selected_type = config["type"]
        if selected_type not in self.recipe_types:
            selected_type = self.recipe_types[0]
            config["type"] = selected_type
        self.active_recipe_type = selected_type
        self.combo_recipe_type.set(selected_type)
        self.render_recipe_gui()

    def on_recipe_disc_selected(self, event=None):
        selected_index = self.combo_recipe_disc.current()
        if not 0 <= selected_index < len(self._recipe_dropdown_cards):
            return
        self._save_visible_recipe()
        selected_card = self._recipe_dropdown_cards[selected_index]
        if selected_card is not self.active_recipe_card:
            self._load_recipe_for_card(selected_card)

    def on_recipe_type_selected(self, event=None):
        self._save_visible_recipe()
        selected_type = self.combo_recipe_type.get()
        if selected_type not in self.recipe_types:
            return
        self.active_recipe_type = selected_type
        if self.active_recipe_card is not None:
            self.active_recipe_card.recipe_config["type"] = selected_type
        self.render_recipe_gui()

    # ========================================================
    # Add disc
    # ========================================================

    def add_disc_card_debounced(self):

        current_time = time.time()

        if current_time - self.last_add_time < 0.25:
            return

        self.last_add_time = current_time

        self.btn_add_disc.config(
            state="disabled"
        )

        self.add_disc_card(blank_text_fields=True)

        self.after(
            250,
            lambda: self.btn_add_disc.config(
                state="normal"
            )
        )

    def show_add_disc_tooltip(self, event):
        tooltip = tk.Toplevel(self)
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(
            f"+{event.widget.winfo_rootx()}+{event.widget.winfo_rooty() + event.widget.winfo_height()}"
        )
        tk.Label(
            tooltip,
            text="Add another disc",
            bg="#242424",
            fg="#ffffff",
            padx=6,
            pady=3
        ).pack()
        self._add_disc_tooltip = tooltip

    def hide_add_disc_tooltip(self, event=None):
        tooltip = getattr(self, "_add_disc_tooltip", None)
        if tooltip is not None:
            tooltip.destroy()
            self._add_disc_tooltip = None

    def add_disc_card(self, blank_text_fields=False):

        self.card_counter += 1

        card = MusicDiscCard(
            self.scroll_frame,
            self.card_counter,
            self.remove_disc_card,
            self,
            blank_text_fields=blank_text_fields
        )

        card.pack(
            fill=tk.X,
            expand=True,
            pady=6,
            padx=4
        )

        self.disc_cards.append(
            card
        )

        # Keep the add control after the final disc card.
        self.btn_add_disc.pack_forget()
        for disc_card in self.disc_cards:
            disc_card.pack(
                fill=tk.X,
                expand=True,
                pady=6,
                padx=4
            )
        self.btn_add_disc.pack(pady=(2, 8))

        self.update_idletasks()

        self.canvas.yview_moveto(
            1.0
        )

        self.update_recipe_disc_dropdown()

    # ========================================================
    # Remove disc
    # ========================================================

    def remove_disc_card(self, card):

        if len(self.disc_cards) <= 1:

            messagebox.showwarning(
                "Warning",
                "You must keep at least one music disc entry."
            )

            return

        card.destroy()

        self.disc_cards.remove(
            card
        )

        self.update_recipe_tab_visibility()

    # ========================================================
    # Generate
    # ========================================================

    def _draw_generate_button(self, color):
        self.btn_generate.delete("all")
        self.btn_generate.create_polygon(
            12, 2, 288, 2, 298, 10, 298, 40, 288, 48, 12, 48,
            2, 40, 2, 10,
            smooth=True,
            splinesteps=20,
            fill=color,
            outline="#a5d6a7",
            width=2
        )
        self.btn_generate.create_text(
            150, 25,
            text="✨  GENERATE PACKAGE",
            fill="#ffffff",
            font=("Segoe UI", 12, "bold")
        )
        self.btn_generate.bind("<Button-1>", lambda event: self.generate())
        self.btn_generate.bind(
            "<Enter>", lambda event: self._draw_generate_button("#4caf50")
        )
        self.btn_generate.bind(
            "<Leave>", lambda event: self._draw_generate_button("#43a047")
        )

    def _advance_generation(self, value=0):
        if value >= 100:
            self.generate_progress["value"] = 100
            self.generate_progress.pack_forget()
            self.btn_generate.config(state="normal", cursor="hand2")
            try:
                folder_path, zip_path = self._generate_package()
            except Exception as error:
                messagebox.showerror(
                    "Generation Failed",
                    f"The package could not be generated.\n\n{error}"
                )
                return

            export_directory = filedialog.askdirectory(
                parent=self,
                title="Choose export directory",
                initialdir=os.path.dirname(folder_path)
            )
            if not export_directory:
                return

            destination_folder = os.path.join(
                export_directory,
                os.path.basename(folder_path)
            )
            destination_zip = (
                os.path.join(export_directory, os.path.basename(zip_path))
                if zip_path
                else None
            )
            same_folder = os.path.normcase(os.path.abspath(folder_path)) == (
                os.path.normcase(os.path.abspath(destination_folder))
            )
            same_zip = (
                zip_path is not None
                and destination_zip is not None
                and os.path.normcase(os.path.abspath(zip_path))
                == os.path.normcase(os.path.abspath(destination_zip))
            )
            conflicting_paths = []
            if not same_folder and os.path.exists(destination_folder):
                conflicting_paths.append(destination_folder)
            if (
                zip_path
                and destination_zip
                and not same_zip
                and os.path.exists(destination_zip)
            ):
                conflicting_paths.append(destination_zip)
            if conflicting_paths:
                messagebox.showerror(
                    "Export Failed",
                    "The export directory already contains a generated "
                    "package with the same name:\n\n"
                    + "\n".join(conflicting_paths)
                    + "\n\nThe generated files remain in their original "
                    "location."
                )
                return

            try:
                if not same_folder:
                    folder_path = shutil.move(
                        folder_path,
                        destination_folder
                    )
                if zip_path and destination_zip and not same_zip:
                    zip_path = shutil.move(zip_path, destination_zip)
            except OSError as error:
                output_location = f"Package folder:\n{folder_path}"
                if zip_path:
                    output_location += f"\n\nZIP archive:\n{zip_path}"
                messagebox.showerror(
                    "Export Failed",
                    "The package was generated, but could not be fully "
                    f"moved to the chosen directory.\n\n{error}\n\n"
                    f"Current file locations:\n{output_location}"
                )
                return

            output_text = f"Package folder:\n{folder_path}"
            if zip_path:
                output_text += f"\n\nZIP archive:\n{zip_path}"

            messagebox.showinfo("Package Generated", output_text)
            return

        self.generate_progress["value"] = value
        self.after(35, lambda: self._advance_generation(value + 5))

    def _generate_package(self):
        self._save_visible_recipe()
        pack_name = self.entry_pack_name.get().strip()
        if (
            not pack_name
            or pack_name in {".", ".."}
            or re.search(r'[<>:"/\\|?*\x00-\x1f]', pack_name)
            or pack_name.endswith((" ", "."))
        ):
            raise ValueError(
                "Pack name must be a non-empty file name without path "
                "separators or Windows-invalid characters."
            )

        output_directory = (
            os.path.dirname(os.path.abspath(sys.executable))
            if getattr(sys, "frozen", False)
            else os.path.dirname(os.path.abspath(__file__))
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        package_name = f"music_disc_package_{timestamp}"
        folder_path = os.path.join(output_directory, package_name)
        zip_path = (
            os.path.join(output_directory, f"{package_name}.zip")
            if self.var_gen_zip.get()
            else None
        )

        discs = []
        for card in self.disc_cards:
            namespace = card.entry_namespace.get().strip()
            if not re.fullmatch(r"[a-z0-9_-][a-z0-9_.-]*", namespace):
                raise ValueError(
                    f"Disc #{card.card_id} has an invalid namespace: {namespace!r}"
                )

            sound_path = card.entry_sound.get().strip().strip('"{}\'')
            if not sound_path or not os.path.isfile(sound_path):
                raise ValueError(
                    f"Choose an existing sound file for disc #{card.card_id}."
                )

            sound_extension = os.path.splitext(sound_path)[1].lower()
            if sound_extension not in {".ogg", ".wav", ".mp3", ".flac", ".m4a", ".aac"}:
                raise ValueError(
                    f"Disc #{card.card_id} uses an unsupported audio format: "
                    f"{sound_extension or '(no extension)'}"
                )

            texture_path = card.entry_texture.get().strip().strip('"{}\'')
            if texture_path and (
                not os.path.isfile(texture_path)
                or not texture_path.lower().endswith(".png")
            ):
                raise ValueError(
                    f"Disc #{card.card_id} texture must be an existing PNG file."
                )

            if sound_extension != ".ogg" and not self.var_convert_ffmpeg.get():
                raise ValueError(
                    f"Disc #{card.card_id} must use OGG audio unless automatic "
                    "FFmpeg conversion is enabled."
                )

            description = card.entry_string_desc.get().strip()
            translations = {}
            song_description_key = (
                f"jukebox_song.{namespace}.disc_{card.card_id}"
            )
            if card.combo_desc_type.get() == "lang":
                for entry in card.lang_entries:
                    language = entry["lang"].get().strip()
                    key = entry["key"].get().strip()
                    value = entry["val"].get().strip()
                    if language and key and value:
                        translations.setdefault(language, {})[key] = value
                        translations[language][song_description_key] = value
            else:
                description = description or f"Music Disc {card.card_id}"
                translations.setdefault("en_us", {})[
                    song_description_key
                ] = description

            try:
                sound_range = float(card.entry_range.get().strip())
                comparator_output = int(card.combo_comp.get())
            except ValueError as error:
                raise ValueError(
                    f"Disc #{card.card_id} has an invalid sound range or "
                    "comparator output."
                ) from error
            if (
                not math.isfinite(sound_range)
                or sound_range <= 0
                or not 0 <= comparator_output <= 15
            ):
                raise ValueError(
                    f"Disc #{card.card_id} sound range must be positive and "
                    "comparator output must be between 0 and 15."
                )

            discs.append({
                "id": card.card_id,
                "namespace": namespace,
                "sound_path": sound_path,
                "sound_extension": sound_extension,
                "texture_path": texture_path,
                "translations": translations,
                "description": description,
                "song_description_key": song_description_key,
                "sound_range": sound_range,
                "comparator_output": comparator_output,
                "create_func": card.var_create_func.get(),
                "recipe": card.var_recipe.get(),
                "recipe_config": {
                    "type": card.recipe_config["type"],
                    "inputs": {
                        recipe_type: (
                            [row[:] for row in value]
                            if recipe_type == "Crafting (Shaped)"
                            else value
                        )
                        for recipe_type, value
                        in card.recipe_config["inputs"].items()
                    },
                },
                "creeper_loot": card.var_creeper_loot.get(),
            })

        if not discs:
            raise ValueError("Add at least one music disc before generating.")

        ffmpeg_executable = None
        if self.var_convert_ffmpeg.get() and any(
            disc["sound_extension"] != ".ogg" for disc in discs
        ):
            ffmpeg_executable = self._get_ffmpeg_executable(output_directory)

        with tempfile.TemporaryDirectory(
            dir=output_directory,
            prefix=".music_disc_generation_"
        ) as temporary_directory:
            staged_folder = os.path.join(temporary_directory, package_name)
            os.makedirs(staged_folder)
            self._write_package(
                staged_folder,
                discs,
                pack_name,
                ffmpeg_executable
            )

            staged_zip = None
            if zip_path:
                staged_zip = os.path.join(temporary_directory, f"{package_name}.zip")
                with zipfile.ZipFile(
                    staged_zip,
                    "w",
                    compression=zipfile.ZIP_DEFLATED
                ) as archive:
                    for root, _, filenames in os.walk(staged_folder):
                        for filename in filenames:
                            source_path = os.path.join(root, filename)
                            archive_name = os.path.relpath(
                                source_path,
                                staged_folder
                            )
                            archive.write(source_path, archive_name)

            os.replace(staged_folder, folder_path)
            if zip_path and staged_zip:
                os.replace(staged_zip, zip_path)

        return folder_path, zip_path

    @staticmethod
    def _get_ffmpeg_executable(output_directory):
        installed_ffmpeg = shutil.which("ffmpeg")
        if installed_ffmpeg:
            return installed_ffmpeg

        if sys.platform != "win32":
            raise FileNotFoundError(
                "FFmpeg is not installed. Automatic FFmpeg download is "
                "currently supported on Windows; install FFmpeg or use OGG files."
            )

        cache_directory = os.path.join(output_directory, "ffmpeg")
        executable_path = os.path.join(cache_directory, "ffmpeg.exe")
        if os.path.isfile(executable_path):
            with open(executable_path, "rb") as executable:
                if executable.read(2) == b"MZ":
                    return executable_path
            raise RuntimeError(
                f"The cached FFmpeg executable is invalid: {executable_path}"
            )

        try:
            with tempfile.TemporaryDirectory(
                dir=output_directory,
                prefix=".ffmpeg_install_"
            ) as temporary_directory:
                archive_path = os.path.join(
                    temporary_directory,
                    "ffmpeg.zip"
                )
                digest = hashlib.sha256()
                request = urllib.request.Request(
                    FFMPEG_DOWNLOAD_URL,
                    headers={"User-Agent": "MusicDiscGenerator/1.0"}
                )
                with urllib.request.urlopen(request, timeout=60) as response:
                    with open(archive_path, "wb") as archive_file:
                        while chunk := response.read(1024 * 1024):
                            digest.update(chunk)
                            archive_file.write(chunk)

                if digest.hexdigest() != FFMPEG_DOWNLOAD_SHA256:
                    raise RuntimeError(
                        "The downloaded FFmpeg archive failed its SHA-256 "
                        "integrity check."
                    )

                staged_executable = os.path.join(
                    temporary_directory,
                    "ffmpeg.exe"
                )
                with zipfile.ZipFile(archive_path) as archive:
                    candidates = [
                        info for info in archive.infolist()
                        if info.filename.lower().endswith("/bin/ffmpeg.exe")
                    ]
                    if len(candidates) != 1:
                        raise RuntimeError(
                            "The FFmpeg archive did not contain exactly one "
                            "expected bin/ffmpeg.exe."
                        )
                    executable_info = candidates[0]
                    if not 1024 * 1024 <= executable_info.file_size <= 200 * 1024 * 1024:
                        raise RuntimeError(
                            "The FFmpeg executable in the downloaded archive "
                            "has an unexpected file size."
                        )
                    with archive.open(executable_info) as source:
                        with open(staged_executable, "wb") as destination:
                            shutil.copyfileobj(source, destination)

                with open(staged_executable, "rb") as executable:
                    if executable.read(2) != b"MZ":
                        raise RuntimeError(
                            "The downloaded FFmpeg executable is not a valid "
                            "Windows program."
                        )

                os.makedirs(cache_directory, exist_ok=True)
                os.replace(staged_executable, executable_path)
        except Exception as error:
            raise RuntimeError(
                "Could not download and install portable FFmpeg beside the "
                "script. Check your internet connection and write permissions, "
                "or install FFmpeg manually and retry."
            ) from error

        return executable_path

    def _write_package(
        self,
        package_directory,
        discs,
        pack_name,
        ffmpeg_executable=None
    ):
        game_version = self.combo_format.get()
        resource_format, data_format = {
            "1.21.1": (34, 48),
            "1.21.2": (42, 57),
            "1.21.3": (42, 57),
            "1.21.4": (46, 61),
        }.get(game_version, (None, None))

        resource_pack_name = f"{pack_name}_rp"
        data_pack_name = f"{pack_name}_dp"
        resource_pack = os.path.join(package_directory, resource_pack_name)
        data_pack = os.path.join(package_directory, data_pack_name)
        os.makedirs(resource_pack)
        os.makedirs(data_pack)

        if game_version.startswith("26."):
            resource_metadata = {
                "min_format": 97.1,
                "max_format": 97.1,
                "description": f"Custom music discs for Minecraft {game_version}",
            }
            data_metadata = {
                "min_format": 121.0,
                "max_format": 121.0,
                "description": f"Custom music discs for Minecraft {game_version}",
            }
        else:
            resource_metadata = {
                "pack_format": resource_format,
                "description": f"Custom music discs for Minecraft {game_version}",
            }
            data_metadata = {
                "pack_format": data_format,
                "description": f"Custom music discs for Minecraft {game_version}",
            }
        self._write_json(
            os.path.join(resource_pack, "pack.mcmeta"),
            {"pack": resource_metadata}
        )
        self._write_json(
            os.path.join(data_pack, "pack.mcmeta"),
            {"pack": data_metadata}
        )

        all_translations = {}
        model_overrides = []
        modern_model_entries = []
        modern_model_data = (
            game_version == "1.21.4" or game_version.startswith("26.")
        )
        item_format = "function" if not self.var_legacy_datapack.get() else "functions"
        recipe_format = "recipe" if not self.var_legacy_datapack.get() else "recipes"
        loot_format = "loot_table" if not self.var_legacy_datapack.get() else "loot_tables"
        function_directory = os.path.join(
            data_pack,
            "data",
            discs[0]["namespace"],
            item_format
        )
        os.makedirs(function_directory, exist_ok=True)
        give_commands = []

        for disc in discs:
            namespace = disc["namespace"]
            disc_name = f"disc_{disc['id']}"
            sound_name = f"music_disc/{disc_name}"
            asset_root = os.path.join(resource_pack, "assets", namespace)
            sound_directory = os.path.join(asset_root, "sounds", "music_disc")
            os.makedirs(sound_directory, exist_ok=True)

            output_sound = os.path.join(sound_directory, f"{disc_name}.ogg")
            if disc["sound_extension"] == ".ogg":
                shutil.copy2(disc["sound_path"], output_sound)
            else:
                conversion = subprocess.run(
                    [
                        ffmpeg_executable or "ffmpeg",
                        "-y",
                        "-i",
                        disc["sound_path"],
                        "-vn",
                        "-c:a",
                        "libvorbis",
                        "-q:a",
                        "5",
                        output_sound,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if conversion.returncode:
                    detail = conversion.stderr.strip().splitlines()
                    raise RuntimeError(
                        f"FFmpeg could not convert disc #{disc['id']} audio."
                        + (f"\n{detail[-1]}" if detail else "")
                    )

            if disc["texture_path"]:
                texture_directory = os.path.join(
                    asset_root,
                    "textures",
                    "item"
                )
                model_directory = os.path.join(
                    asset_root,
                    "models",
                    "item"
                )
                os.makedirs(texture_directory, exist_ok=True)
                os.makedirs(model_directory, exist_ok=True)
                shutil.copy2(
                    disc["texture_path"],
                    os.path.join(texture_directory, f"{disc_name}.png")
                )
                self._write_json(
                    os.path.join(model_directory, f"{disc_name}.json"),
                    {
                        "parent": "minecraft:item/generated",
                        "textures": {
                            "layer0": f"{namespace}:item/{disc_name}",
                        },
                    }
                )
                if modern_model_data:
                    modern_model_entries.append({
                        "threshold": float(disc["id"]),
                        "model": {
                            "type": "minecraft:model",
                            "model": f"{namespace}:item/{disc_name}",
                        },
                    })
                else:
                    model_overrides.append({
                        "predicate": {
                            "custom_model_data": disc["id"],
                        },
                        "model": f"{namespace}:item/{disc_name}",
                    })

            for language, translations in disc["translations"].items():
                all_translations.setdefault(language, {}).update(translations)

            song_directory = os.path.join(
                data_pack,
                "data",
                namespace,
                "jukebox_song"
            )
            self._write_json(
                os.path.join(
                    song_directory,
                    f"{disc_name}.json"
                ),
                {
                    "sound_event": f"{namespace}:{sound_name}",
                    "description": {
                        "translate": disc["song_description_key"]
                    },
                    "length_in_seconds": 180,
                    "comparator_output": int(disc["comparator_output"]),
                }
            )

            custom_model_data = (
                f"{{floats:[{disc['id']}.0]}}"
                if modern_model_data
                else str(disc["id"])
            )
            if disc["create_func"]:
                give_commands.append(
                    f"give @s minecraft:music_disc_13"
                    f"[minecraft:custom_model_data={custom_model_data},"
                    f"minecraft:jukebox_playable={{song_event:"
                    f"\"{namespace}:{disc_name}\"}}] 1"
                )

            if disc["recipe"]:
                self._write_disc_recipe(data_pack, disc, recipe_format)

            if disc["creeper_loot"]:
                self._write_creeper_loot(data_pack, disc, loot_format)

        for namespace in {disc["namespace"] for disc in discs}:
            namespace_discs = [
                disc for disc in discs if disc["namespace"] == namespace
            ]
            self._write_json(
                os.path.join(resource_pack, "assets", namespace, "sounds.json"),
                {
                    f"music_disc/disc_{disc['id']}": {
                        "sounds": [{
                            "name": (
                                f"{namespace}:music_disc/disc_{disc['id']}"
                            ),
                            "stream": True,
                            "attenuation_distance": disc["sound_range"],
                        }]
                    }
                    for disc in namespace_discs
                }
            )

        if modern_model_entries:
            self._write_json(
                os.path.join(
                    resource_pack,
                    "assets",
                    "minecraft",
                    "items",
                    "music_disc_13.json"
                ),
                {
                    "model": {
                        "type": "minecraft:range_dispatch",
                        "property": "minecraft:custom_model_data",
                        "entries": modern_model_entries,
                        "fallback": {
                            "type": "minecraft:model",
                            "model": "minecraft:item/music_disc_13",
                        },
                    }
                }
            )
        elif model_overrides:
            model_path = os.path.join(
                resource_pack,
                "assets",
                "minecraft",
                "models",
                "item",
                "music_disc_13.json"
            )
            model = {
                "parent": "minecraft:item/generated",
                "textures": {
                    "layer0": "minecraft:item/music_disc_13",
                },
                "overrides": model_overrides,
            }
            self._write_json(model_path, model)

        for language, translations in all_translations.items():
            self._write_json(
                os.path.join(
                    resource_pack,
                    "assets",
                    "minecraft",
                    "lang",
                    f"{language}.json"
                ),
                translations
            )

        if give_commands:
            self._write_text(
                os.path.join(function_directory, "give_discs.mcfunction"),
                "\n".join(give_commands) + "\n"
            )

        install_text = (
            "Custom music disc package\n"
            f"Minecraft version selected: {game_version}\n\n"
            f"Copy {resource_pack_name} into the world's resourcepacks folder "
            f"and {data_pack_name} into the world's datapacks folder.\n"
            f"Run /function {discs[0]['namespace']}:give_discs to receive the "
            "generated discs when the function option is enabled.\n"
            "Creeper loot output is a separate table template; merge it with "
            "the vanilla creeper loot table if you want to preserve vanilla drops.\n"
        )
        self._write_text(
            os.path.join(package_directory, "README.txt"),
            install_text
        )

    def _write_disc_recipe(self, data_pack, disc, recipe_format):
        recipe_directory = os.path.join(
            data_pack,
            "data",
            disc["namespace"],
            recipe_format
        )
        os.makedirs(recipe_directory, exist_ok=True)

        modern_model_data = (
            self.combo_format.get() == "1.21.4"
            or self.combo_format.get().startswith("26.")
        )
        custom_model_data = (
            {"floats": [float(disc["id"])]}
            if modern_model_data
            else disc["id"]
        )
        result = {
            "id": "minecraft:music_disc_13",
            "count": 1,
            "components": {
                "minecraft:custom_model_data": custom_model_data,
                "minecraft:jukebox_playable": {
                    "song_event": f"{disc['namespace']}:disc_{disc['id']}",
                },
            },
        }
        recipe_config = disc["recipe_config"]
        selected_type = recipe_config["type"]
        if selected_type == "Crafting (Shaped)":
            rows = []
            ingredients = {}
            next_symbol = iter("ABCDEFGHI")
            for row in recipe_config["inputs"].get(selected_type, []):
                pattern_row = ""
                for item in row:
                    item_id = item.strip()
                    if not item_id or item_id == "minecraft:air":
                        pattern_row += " "
                        continue
                    if not re.fullmatch(r"[a-z0-9_.-]+:[a-z0-9_./-]+", item_id):
                        raise ValueError(f"Invalid recipe item ID: {item_id!r}")
                    if item_id not in ingredients.values():
                        symbol = next(next_symbol, None)
                        if symbol is None:
                            raise ValueError("A recipe cannot use more than nine ingredients.")
                        ingredients[symbol] = item_id
                    pattern_row += next(
                        key for key, value in ingredients.items()
                        if value == item_id
                    )
                rows.append(pattern_row)
            while rows and not rows[0].strip():
                rows.pop(0)
            while rows and not rows[-1].strip():
                rows.pop()
            if not rows or not any(row.strip() for row in rows):
                raise ValueError("The shaped recipe needs at least one ingredient.")
            width = max(len(row) for row in rows)
            rows = [row.ljust(width) for row in rows]
            left = min(
                index for row in rows for index, char in enumerate(row)
                if char != " "
            )
            right = max(
                index for row in rows for index, char in enumerate(row)
                if char != " "
            ) + 1
            recipe = {
                "type": "minecraft:crafting_shaped",
                "pattern": [row[left:right] for row in rows],
                "key": {
                    symbol: {"item": item_id}
                    for symbol, item_id in ingredients.items()
                },
                "result": result,
            }
        elif selected_type == "Crafting (Shapeless)":
            ingredient = recipe_config["inputs"].get(selected_type, "").strip()
            if not re.fullmatch(r"[a-z0-9_.-]+:[a-z0-9_./-]+", ingredient):
                raise ValueError(f"Invalid recipe item ID: {ingredient!r}")
            recipe = {
                "type": "minecraft:crafting_shapeless",
                "ingredients": [{"item": ingredient}],
                "result": result,
            }
        else:
            ingredient = recipe_config["inputs"].get(selected_type, "").strip()
            if not re.fullmatch(r"[a-z0-9_.-]+:[a-z0-9_./-]+", ingredient):
                raise ValueError(f"Invalid recipe item ID: {ingredient!r}")
            cooking_type = {
                "Smelting (Furnace)": "smelting",
                "Blast Furnace": "blasting",
                "Smoker": "smoking",
            }.get(selected_type)
            if not cooking_type:
                raise ValueError(f"Unsupported recipe type: {selected_type}")
            recipe = {
                "type": f"minecraft:{cooking_type}",
                "ingredient": {"item": ingredient},
                "result": "minecraft:music_disc_13",
                "experience": 0.1,
                "cookingtime": 200,
            }

        self._write_json(
            os.path.join(recipe_directory, f"disc_{disc['id']}.json"),
            recipe
        )

    def _write_creeper_loot(self, data_pack, disc, loot_format):
        loot_directory = os.path.join(
            data_pack,
            "data",
            disc["namespace"],
            loot_format,
            "creeper"
        )
        os.makedirs(loot_directory, exist_ok=True)
        modern_model_data = (
            self.combo_format.get() == "1.21.4"
            or self.combo_format.get().startswith("26.")
        )
        custom_model_data = (
            {"floats": [float(disc["id"])]}
            if modern_model_data
            else disc["id"]
        )
        self._write_json(
            os.path.join(loot_directory, f"disc_{disc['id']}.json"),
            {
                "type": "minecraft:entity",
                "pools": [
                    {
                        "rolls": 1,
                        "entries": [
                            {
                                "type": "minecraft:item",
                                "name": "minecraft:music_disc_13",
                                "functions": [
                                    {
                                        "function": "minecraft:set_components",
                                        "components": {
                                            "minecraft:custom_model_data": custom_model_data,
                                            "minecraft:jukebox_playable": {
                                                "song_event": (
                                                    f"{disc['namespace']}:disc_{disc['id']}"
                                                ),
                                            },
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        )

    @staticmethod
    def _write_json(path, value):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as output_file:
            json.dump(value, output_file, indent=2, ensure_ascii=False)

    @staticmethod
    def _write_text(path, value):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as output_file:
            output_file.write(value)

    def generate(self):
        if self.btn_generate.cget("state") == "disabled":
            return
        self.generate_progress["value"] = 0
        self.generate_progress.pack(
            before=self.btn_generate,
            fill=tk.X,
            pady=(0, 6)
        )
        self.btn_generate.config(state="disabled", cursor="wait")
        self.after(35, self._advance_generation)


# ============================================================
# Application entry point
# ============================================================

def main():

    try:

        app = MusicDiscMakerApp()

        app.mainloop()

    except Exception as error:

        # If something fails during startup, don't silently
        # leave the user with an apparently blank application.

        error_text = (
            "The application failed to start.\n\n"
            f"{type(error).__name__}: {error}\n\n"
            "A traceback will be printed to the console."
        )

        try:
            messagebox.showerror(
                "Music Disc Maker - Startup Error",
                error_text
            )
        except Exception:
            pass

        traceback.print_exc()


if __name__ == "__main__":
    main()