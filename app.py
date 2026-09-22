# -*- coding: utf-8 -*-
"""Офлайн-переводчик (CustomTkinter UI, креативные темы).

Движок: Argos Translate (нейросетевой перевод, модели лежат локально).
Режим разбиения на предложения — MiniSBD (лёгкий, без stanza/torch).

Возможности:
  * Выбор пары и направления (сегментный переключатель), автоопределение языка.
  * Горячие клавиши: Ctrl+Alt+T — буфер обмена, Ctrl+Alt+S — выделенный текст.
  * Трей, всплывашка у курсора, перевод в буфер.
  * Темы: простые + «Космос»/«Закат» с обоями, «Терминал», «Неон», «Ретро-95», «Своя».
  * «Языки…» — установка дополнительных пар (нужен интернет).

Самопроверка exe: app.py --test (пишет selftest_result.txt)
"""

import configparser
import ctypes
import os
import queue
import random
import re
import sys
import threading
from ctypes import wintypes

# Лёгкий режим разбиения на предложения — задать ДО импорта argostranslate
os.environ.setdefault("ARGOS_CHUNK_TYPE", "MINISBD")

import customtkinter as ctk
import tkinter as tk
from tkinter import colorchooser

import argostranslate.package as apackage
import argostranslate.translate as atranslate

APP_TITLE = "Офлайн-переводчик"

MAX_POPUP_SOURCE = 5000   # ограничение текста для перевода из буфера
SELECTION_WAIT_MS = 1500  # сколько ждём, пока приложение скопирует выделение

APP_DIR = (
    os.path.dirname(sys.executable)
    if getattr(sys, "frozen", False)
    else os.path.dirname(os.path.abspath(__file__))
)
INI_PATH = os.path.join(APP_DIR, "settings.ini")

# ---------------- Темы оформления ----------------
# radius — скругление углов; wallpaper — фон-обои ("stars" | ("gradient", c1, c2) | None)

THEMES = {
    "Светлая": {
        "bg": "#f0f2f5", "text_bg": "#ffffff", "dst_bg": "#f7f9fb", "text_fg": "#1a1a1a",
        "caret": "#1a1a1a", "accent": "#2f6fdb", "accent_fg": "#ffffff",
        "btn_bg": "#e4e7ec", "btn_fg": "#1a1a1a", "btn_active": "#ccd3dd",
        "btn_fg_disabled": "#9aa3b0", "status_fg": "#4a5568", "border": "#c9ced6",
        "font_family": "Segoe UI", "font_size": 13, "radius": 12, "wallpaper": None,
    },
    "Тёмная": {
        "bg": "#1e1f24", "text_bg": "#26272e", "dst_bg": "#2b2c34", "text_fg": "#e8e8e8",
        "caret": "#e8e8e8", "accent": "#4f8cff", "accent_fg": "#ffffff",
        "btn_bg": "#33353d", "btn_fg": "#e8e8e8", "btn_active": "#454752",
        "btn_fg_disabled": "#6f727d", "status_fg": "#9aa3b2", "border": "#3a3c45",
        "font_family": "Segoe UI", "font_size": 13, "radius": 12, "wallpaper": None,
    },
    "Бумага": {
        "bg": "#f3ecdd", "text_bg": "#faf6ec", "dst_bg": "#f4eede", "text_fg": "#3b3128",
        "caret": "#3b3128", "accent": "#8c6d3f", "accent_fg": "#fdf9ef",
        "btn_bg": "#e7dcc4", "btn_fg": "#3b3128", "btn_active": "#d9cbb0",
        "btn_fg_disabled": "#b3a68d", "status_fg": "#6b5d4a", "border": "#d8cbb0",
        "font_family": "Georgia", "font_size": 13, "radius": 10, "wallpaper": None,
    },
    "Контраст": {
        "bg": "#000000", "text_bg": "#000000", "dst_bg": "#0d0d0d", "text_fg": "#ffffff",
        "caret": "#ffff00", "accent": "#ffff00", "accent_fg": "#000000",
        "btn_bg": "#1c1c1c", "btn_fg": "#ffffff", "btn_active": "#333333",
        "btn_fg_disabled": "#666666", "status_fg": "#ffff00", "border": "#777777",
        "font_family": "Segoe UI", "font_size": 14, "radius": 6, "wallpaper": None,
    },
    "Океан": {
        "bg": "#eaf4fb", "text_bg": "#ffffff", "dst_bg": "#f2f9fd", "text_fg": "#12324a",
        "caret": "#12324a", "accent": "#0e7bb8", "accent_fg": "#ffffff",
        "btn_bg": "#d3e8f5", "btn_fg": "#12324a", "btn_active": "#b8d9ec",
        "btn_fg_disabled": "#8fb4c9", "status_fg": "#33627f", "border": "#bcdcec",
        "font_family": "Segoe UI", "font_size": 13, "radius": 14, "wallpaper": None,
    },
    # --- креативные ---
    "Неон": {
        "bg": "#0d0119", "text_bg": "#170a2e", "dst_bg": "#130825", "text_fg": "#efe6ff",
        "caret": "#ff2bd6", "accent": "#ff2bd6", "accent_fg": "#ffffff",
        "btn_bg": "#241338", "btn_fg": "#e6d9ff", "btn_active": "#3d2066",
        "btn_fg_disabled": "#6b5a8a", "status_fg": "#b28dff", "border": "#4b2a86",
        "font_family": "Segoe UI", "font_size": 13, "radius": 18, "wallpaper": None,
    },
    "Терминал": {
        "bg": "#050805", "text_bg": "#0a120a", "dst_bg": "#081008", "text_fg": "#39ff5e",
        "caret": "#39ff5e", "accent": "#1d9e3a", "accent_fg": "#d9ffe3",
        "btn_bg": "#0d1a0d", "btn_fg": "#39ff5e", "btn_active": "#1a331a",
        "btn_fg_disabled": "#2f6b3f", "status_fg": "#7dffa1", "border": "#1f3d1f",
        "font_family": "Consolas", "font_size": 13, "radius": 2, "wallpaper": None,
    },
    "Ретро-95": {
        "bg": "#c0c0c0", "text_bg": "#ffffff", "dst_bg": "#f4f4f0", "text_fg": "#000000",
        "caret": "#000000", "accent": "#000080", "accent_fg": "#ffffff",
        "btn_bg": "#d4d0c8", "btn_fg": "#000000", "btn_active": "#b5b0a8",
        "btn_fg_disabled": "#808080", "status_fg": "#222222", "border": "#808080",
        "font_family": "Tahoma", "font_size": 12, "radius": 3, "wallpaper": None,
    },
    "Космос": {
        "bg": "#0b1026", "text_bg": "#141b38", "dst_bg": "#101731", "text_fg": "#e8ecff",
        "caret": "#e8ecff", "accent": "#7c5cff", "accent_fg": "#ffffff",
        "btn_bg": "#1d2547", "btn_fg": "#dfe5ff", "btn_active": "#2a3564",
        "btn_fg_disabled": "#5b648f", "status_fg": "#9aa8e8", "border": "#2c3768",
        "font_family": "Segoe UI", "font_size": 13, "radius": 16, "wallpaper": "stars",
    },
    "Янтарь": {
        "bg": "#000000", "text_bg": "#1c1c1e", "dst_bg": "#161618", "text_fg": "#ffffff",
        "caret": "#f2a03c", "accent": "#f2a03c", "accent_fg": "#000000",
        "btn_bg": "#2c2c2e", "btn_fg": "#ffffff", "btn_active": "#3a3a3c",
        "btn_fg_disabled": "#8e8e93", "status_fg": "#8e8e93", "border": "#2c2c2e",
        "font_family": "Segoe UI", "font_size": 13, "radius": 14, "wallpaper": None,
    },
    "Закат": {
        "bg": "#1b1b3a", "text_bg": "#241f3d", "dst_bg": "#201b36", "text_fg": "#ffe9d6",
        "caret": "#ffe9d6", "accent": "#ff7e5f", "accent_fg": "#2b1330",
        "btn_bg": "#3a2f55", "btn_fg": "#ffd9c2", "btn_active": "#4d3f6e",
        "btn_fg_disabled": "#8a7698", "status_fg": "#ffb59e", "border": "#584a80",
        "font_family": "Segoe UI", "font_size": 13, "radius": 16,
        "wallpaper": ("gradient", "#1b1b3a", "#6a2c70", "#f38b4a"),
    },
}
CUSTOM_THEME_NAME = "Своя"
THEMES[CUSTOM_THEME_NAME] = dict(THEMES["Светлая"])
DEFAULT_THEME = "Светлая"
THEME_SLUGS = {"Светлая": "light", "Тёмная": "dark", "Бумага": "paper", "Контраст": "contrast",
               "Океан": "ocean", "Неон": "neon", "Терминал": "terminal", "Ретро-95": "retro95",
               "Космос": "space", "Закат": "sunset", "Янтарь": "amber", CUSTOM_THEME_NAME: "custom"}
FONT_FAMILIES = ["Segoe UI", "Georgia", "Verdana", "Calibri", "Consolas", "Arial", "Tahoma"]

# ---------------- Глобальные горячие клавиши (Win32) ----------------

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
VK_SPACE = 0x20

HOTKEY_VARIANTS = {
    "Ctrl+Alt+T": (MOD_CONTROL | MOD_ALT, ord("T")),
    "Ctrl+Alt+R": (MOD_CONTROL | MOD_ALT, ord("R")),
    "Ctrl+Alt+S": (MOD_CONTROL | MOD_ALT, ord("S")),
    "Ctrl+Alt+Пробел": (MOD_CONTROL | MOD_ALT, VK_SPACE),
    "Ctrl+Shift+T": (MOD_CONTROL | MOD_SHIFT, ord("T")),
}
DEFAULT_HOTKEY_CLIPBOARD = "Ctrl+Alt+T"
DEFAULT_HOTKEY_SELECTION = "Ctrl+Alt+S"


class HotkeyManager:
    """Регистрирует глобальную горячую клавишу через RegisterHotKey.

    on_hotkey и on_result вызываются из потока-хука: в GUI их обработчик
    должен только класть сообщение в очередь, а не трогать tkinter.
    """

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None

    def start(self, mods: int, vk: int, on_hotkey, on_result) -> None:
        self.stop()
        self._thread = threading.Thread(
            target=self._loop, args=(mods, vk, on_hotkey, on_result), daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        thread = self._thread
        if thread is not None and thread.is_alive():
            user32 = ctypes.windll.user32
            user32.PostThreadMessageW(thread.ident, WM_QUIT, 0, 0)
            thread.join(timeout=2)
        self._thread = None

    @staticmethod
    def _loop(mods: int, vk: int, on_hotkey, on_result) -> None:
        user32 = ctypes.windll.user32
        if not user32.RegisterHotKey(None, 1, mods, vk):
            on_result(False, "клавиша занята другой программой")
            return
        on_result(True, "")
        msg = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY and msg.wParam == 1:
                    on_hotkey()
        finally:
            user32.UnregisterHotKey(None, 1)


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUT_UNION)]


def send_copy_shortcut() -> None:
    """Имитирует Ctrl+C в активном окне (для перевода выделенного текста)."""
    VK_CONTROL, VK_C, KEYEVENTF_KEYUP = 0x11, 0x43, 0x0002
    seq = [(VK_CONTROL, 0), (VK_C, 0), (VK_C, KEYEVENTF_KEYUP), (VK_CONTROL, KEYEVENTF_KEYUP)]
    inputs = (INPUT * len(seq))()
    for i, (vk, flags) in enumerate(seq):
        inputs[i].type = 1  # INPUT_KEYBOARD
        inputs[i].ki = KEYBDINPUT(vk, 0, flags, 0, None)
    ctypes.windll.user32.SendInput(len(seq), inputs, ctypes.sizeof(INPUT))


# ---------------- Определение языка ----------------

_SCRIPT_CHECKS = (
    ("uk", lambda t: any(ch in "іїєґ" for ch in t)),
    ("ru", lambda t: any("\u0400" <= ch <= "\u04FF" for ch in t)),
    ("zh", lambda t: any("\u4e00" <= ch <= "\u9fff" for ch in t)),
    ("ja", lambda t: any("\u3040" <= ch <= "\u30ff" for ch in t)),
    ("ko", lambda t: any("\uac00" <= ch <= "\ud7af" for ch in t)),
    ("el", lambda t: any("\u0370" <= ch <= "\u03ff" for ch in t)),
    ("ar", lambda t: any("\u0600" <= ch <= "\u06ff" for ch in t)),
    ("he", lambda t: any("\u0590" <= ch <= "\u05ff" for ch in t)),
)
_STOPWORDS = {
    "en": "the and is are was were in on of to it this that with for have has be you i not they he she we do does did my your his her its our their what which who will would can could should",
    "de": "der die das und ist sind war waren in an auf mit für nicht ein eine ich du er sie es wir ihr haben hat sein werden wurde",
    "fr": "le la les et est sont était dans sur pour pas une des du je tu il elle nous vous ils elles avec qui que ce cette avoir être faire plus",
    "es": "el la los las y es son estaba en para con por que una del al lo su sus esta este eso como más pero muy todo está son fue",
    "it": "il lo la i gli le e è sono era in per con non una del della dei che cosa come più stato nella questo quella",
    "pt": "o a os as e é são estava em para com por que uma do da dos das no na não mais como este esta isso foi",
    "nl": "de het een en is zijn was in op met voor niet van dat dit ik jij hij zij we jullie hebben heeft wordt worden",
    "pl": "nie jest są było w na z do dla się to ten ta te że oraz jak ale co kto on ona oni my wy",
    "tr": "bir ve için ile bu şu o değil çok ama var yok olarak gibi her en daha",
}
_STOPWORD_SETS = {k: frozenset(v.split()) for k, v in _STOPWORDS.items()}


def detect_lang_code(text: str, codes) -> str:
    """Какой из codes больше похож на язык text."""
    codes = list(codes)
    lower = text.lower()
    for code, check in _SCRIPT_CHECKS:
        if code in codes and check(lower):
            return code
    words = re.findall(r"[^\W\d_]+", lower, re.UNICODE)
    best_code, best_score = codes[0], -1
    for code in codes:
        sw = _STOPWORD_SETS.get(code)
        score = sum(1 for w in words if sw and w in sw) if sw else 0
        if score > best_score:
            best_code, best_score = code, score
    return best_code


# ---------------- Настройки (settings.ini) ----------------

_ini_lock = threading.Lock()


def _ini_read() -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    try:
        parser.read(INI_PATH, encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    return parser


def ini_get(section: str, key: str, fallback: str = "") -> str:
    return _ini_read().get(section, key, fallback=fallback)


def ini_set(section: str, key: str, value: str) -> None:
    with _ini_lock:
        parser = _ini_read()
        if section not in parser:
            parser[section] = {}
        parser[section][key] = value
        try:
            with open(INI_PATH, "w", encoding="utf-8") as fh:
                parser.write(fh)
        except OSError:
            pass


def load_custom_theme() -> None:
    parser = _ini_read()
    theme = THEMES[CUSTOM_THEME_NAME]
    for key in list(theme):
        value = parser.get("custom", key, fallback=None)
        if value is None:
            continue
        if key == "font_size":
            try:
                theme[key] = max(9, min(18, int(value)))
            except ValueError:
                pass
        elif key == "font_family":
            if value in FONT_FAMILIES:
                theme[key] = value
        elif key == "radius":
            try:
                theme[key] = max(0, min(24, int(value)))
            except ValueError:
                pass
        elif isinstance(value, str) and value.startswith("#"):
            theme[key] = value


def save_custom_theme() -> None:
    for key, value in THEMES[CUSTOM_THEME_NAME].items():
        if key == "wallpaper":
            continue
        ini_set("custom", key, str(value))


# ---------------- Приложение ----------------


class TranslatorApp:
    def __init__(self, root: ctk.CTk, use_tray: bool = True) -> None:
        self.root = root
        root.title(APP_TITLE)
        root.geometry("1000x640")
        root.minsize(780, 500)

        self.theme_colors = THEMES[DEFAULT_THEME]
        self.base_font = ctk.CTkFont(family="Segoe UI", size=13)

        self.pairs: list[tuple[str, str]] = []
        self.translators: dict[tuple[str, str], object] = {}
        self.worker_queue: queue.Queue = queue.Queue()
        self.translating = False
        self._popup: tk.Toplevel | None = None
        self._popup_job: str | None = None
        self._tray: object | None = None
        self._tray_hint_shown = False
        self._sel_saved_clip: str | None = None
        self._sel_polls_left = 0
        self._closing = False

        # обои/логотип
        self._wallpaper: ctk.CTkLabel | None = None
        self._wall_spec = None
        self._wall_size = (0, 0)
        self._wall_job: str | None = None
        self._logo_label: ctk.CTkLabel | None = None

        # направление: canonical "auto"/"forward"/"reverse" + подписи сегментов
        self.direction_var = tk.StringVar(value="auto")
        self._dir_labels = {"auto": "Авто"}

        # реестры виджетов для перекраски тем
        self._frames: list[ctk.CTkFrame] = []
        self._labels: list[ctk.CTkLabel] = []
        self._status_labels: list[ctk.CTkLabel] = []
        self._normal_buttons: list[ctk.CTkButton] = []
        self._accent_buttons: list[ctk.CTkButton] = []
        self._combos: list[ctk.CTkComboBox] = []
        self._segmented: list[ctk.CTkSegmentedButton] = []
        self._textboxes: list[tuple[ctk.CTkTextbox, str]] = []
        self._pane_titles: list[ctk.CTkLabel] = []

        self.hotkey_clip = HotkeyManager()
        self.hotkey_sel = HotkeyManager()

        self._build_ui()
        load_custom_theme()
        self.apply_theme(ini_get("theme", "name", DEFAULT_THEME), save=False)
        self._apply_hotkey_clip(ini_get("hotkey", "combo", DEFAULT_HOTKEY_CLIPBOARD), save=True)
        self._apply_hotkey_sel(
            ini_get("hotkey", "combo_selection", DEFAULT_HOTKEY_SELECTION), save=True
        )
        self._load_models()
        self.root.after(100, self._poll_worker)
        if use_tray:
            self.root.after(500, self._setup_tray)
        root.protocol("WM_DELETE_WINDOW", self._on_close_window)
        root.bind("<Destroy>", self._on_root_destroy)
        root.bind("<Configure>", self._on_configure)

    # ---------- фабрики виджетов ----------

    def _mk_frame(self, parent, **kwargs) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, fg_color="transparent", **kwargs)
        self._frames.append(frame)
        return frame

    def _mk_label(self, parent, text: str = "", status: bool = False, **kwargs) -> ctk.CTkLabel:
        label = ctk.CTkLabel(parent, text=text, font=self.base_font, **kwargs)
        (self._status_labels if status else self._labels).append(label)
        return label

    def _mk_button(self, parent, text: str, command, accent: bool = False, **kwargs) -> ctk.CTkButton:
        button = ctk.CTkButton(parent, text=text, command=command, font=self.base_font, **kwargs)
        (self._accent_buttons if accent else self._normal_buttons).append(button)
        return button

    def _mk_combo(self, parent, variable, values, width: int, command=None) -> ctk.CTkComboBox:
        combo = ctk.CTkComboBox(
            parent,
            variable=variable,
            values=values,
            width=width,
            state="readonly",
            font=self.base_font,
            dropdown_font=self.base_font,
            command=command,
        )
        self._combos.append(combo)
        return combo

    # ---------------- UI ----------------

    def _build_ui(self) -> None:
        top = self._mk_frame(self.root)
        top.pack(fill=tk.X, padx=10, pady=(10, 4))

        # Правая часть (пакуется первой, чтобы не вытеснялась при узком окне).
        # ВАЖНО: у CTkComboBox выбор пункта прилетает только через command=,
        # событие <<ComboboxSelected>> не генерируется.
        self.theme_var = tk.StringVar(value=ini_get("theme", "name", DEFAULT_THEME))
        self.theme_combo = self._mk_combo(
            top, self.theme_var, list(THEMES), 116,
            command=lambda value: self.apply_theme(value),
        )
        self.theme_combo.pack(side=tk.RIGHT, padx=(4, 8))
        self._mk_label(top, "Тема:").pack(side=tk.RIGHT)

        self._logo_label = ctk.CTkLabel(top, text="")
        self._logo_label.pack(side=tk.LEFT, padx=(0, 8))

        self._mk_label(top, "Пара:").pack(side=tk.LEFT)
        self.pair_var = tk.StringVar()
        self.pair_combo = self._mk_combo(
            top, self.pair_var, [], 110,
            command=lambda value: self._on_pair_change(),
        )
        self.pair_combo.pack(side=tk.LEFT, padx=(6, 10))

        self._mk_label(top, "Направление:").pack(side=tk.LEFT)
        self.direction_seg = ctk.CTkSegmentedButton(
            top, values=["Авто"], command=self._on_direction_seg, font=self.base_font
        )
        self._segmented.append(self.direction_seg)
        self.direction_seg.pack(side=tk.LEFT, padx=(6, 10))

        self.translate_btn = self._mk_button(
            top, "Перевести  (Ctrl+Enter)", self.translate, accent=True
        )
        self.translate_btn.pack(side=tk.LEFT, padx=4)

        self._mk_button(top, "⇄", self.swap_texts, width=36).pack(side=tk.LEFT, padx=2)
        self._mk_button(top, "Очистить", self.clear_all).pack(side=tk.LEFT, padx=2)

        # Нижняя панель пакуется ДО текстовых полей: Text запрашивает много
        # высоты, и без этого pack обрезает нижнюю панель.
        bottom = self._mk_frame(self.root)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(4, 10))

        self._mk_button(bottom, "Копировать", self.copy_result).pack(side=tk.LEFT, padx=(0, 8))

        self._mk_label(bottom, "Клавиши:").pack(side=tk.LEFT)
        self.hotkey_clip_var = tk.StringVar(
            value=ini_get("hotkey", "combo", DEFAULT_HOTKEY_CLIPBOARD)
        )
        hk1 = self._mk_combo(
            bottom, self.hotkey_clip_var, list(HOTKEY_VARIANTS), 128,
            command=lambda value: self._apply_hotkey_clip(value),
        )
        hk1.pack(side=tk.LEFT, padx=(4, 2))
        self.hotkey_sel_var = tk.StringVar(
            value=ini_get("hotkey", "combo_selection", DEFAULT_HOTKEY_SELECTION)
        )
        hk2 = self._mk_combo(
            bottom, self.hotkey_sel_var, list(HOTKEY_VARIANTS), 128,
            command=lambda value: self._apply_hotkey_sel(value),
        )
        hk2.pack(side=tk.LEFT, padx=(2, 8))
        self.hotkey_clip_combo, self.hotkey_sel_combo = hk1, hk2

        self._mk_button(bottom, "Языки…", self.open_languages_dialog).pack(
            side=tk.LEFT, padx=(0, 8)
        )

        self.status_var = tk.StringVar(value="Загрузка моделей…")
        self._mk_label(bottom, textvariable=self.status_var, status=True, anchor="w").pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )

        body = self._mk_frame(self.root)
        body.pack(fill=tk.BOTH, expand=True, padx=10)

        src_title = self._mk_label(body, "Исходный текст")
        src_title.pack(anchor="w", pady=(2, 2))
        self._pane_titles.append(src_title)
        self.src_text = self._mk_textbox(body, "text_bg")
        self.src_text.pack(fill=tk.BOTH, expand=True)

        dst_title = self._mk_label(body, "Перевод")
        dst_title.pack(anchor="w", pady=(8, 2))
        self._pane_titles.append(dst_title)
        self.dst_text = self._mk_textbox(body, "dst_bg")
        self.dst_text.pack(fill=tk.BOTH, expand=True)
        self.dst_text.configure(state="disabled")

        self.src_text.bind("<Control-Return>", lambda e: self.translate())

    def _mk_textbox(self, parent, bg_key: str) -> ctk.CTkTextbox:
        textbox = ctk.CTkTextbox(
            parent,
            wrap="word",
            font=self.base_font,
            activate_scrollbars=True,
        )
        self._textboxes.append((textbox, bg_key))
        return textbox

    # ---------------- Тема ----------------

    def apply_theme(self, name: str, save: bool = True) -> None:
        t = THEMES.get(name, THEMES[DEFAULT_THEME])
        self.theme_colors = t
        self.base_font = ctk.CTkFont(family=t["font_family"], size=t["font_size"])
        radius = t.get("radius", 12)
        ctk.set_appearance_mode("light" if self._is_light(t["bg"]) else "dark")

        self._apply_wallpaper(t)

        self.root.configure(fg_color=t["bg"])
        frame_bg = "transparent" if t.get("wallpaper") else t["bg"]
        for frame in self._frames:
            frame.configure(fg_color=frame_bg)
        for label in self._labels:
            label.configure(font=self.base_font, text_color=t["text_fg"])
        for label in self._status_labels:
            label.configure(font=self.base_font, text_color=t["status_fg"])
        for button in self._normal_buttons:
            button.configure(
                font=self.base_font,
                fg_color=t["btn_bg"],
                hover_color=t["btn_active"],
                text_color=t["btn_fg"],
                border_color=t["border"],
                corner_radius=radius,
            )
        for button in self._accent_buttons:
            button.configure(
                font=self.base_font,
                fg_color=t["accent"],
                hover_color=t["accent"],
                text_color=t["accent_fg"],
                corner_radius=radius,
            )
        for combo in self._combos:
            combo.configure(
                font=self.base_font,
                dropdown_font=self.base_font,
                fg_color=t["text_bg"],
                button_color=t["btn_bg"],
                button_hover_color=t["btn_active"],
                text_color=t["text_fg"],
                border_color=t["border"],
                dropdown_fg_color=t["text_bg"],
                dropdown_text_color=t["text_fg"],
                dropdown_hover_color=t["accent"],
                corner_radius=radius,
            )
        for seg in self._segmented:
            seg.configure(
                font=self.base_font,
                fg_color=t["btn_bg"],
                unselected_color=t["btn_bg"],
                unselected_hover_color=t["btn_active"],
                selected_color=t["accent"],
                selected_hover_color=t["accent"],
                text_color=t["text_fg"],
                text_color_disabled=t["btn_fg_disabled"],
                corner_radius=radius,
            )
        for textbox, bg_key in self._textboxes:
            textbox.configure(
                font=self.base_font,
                fg_color=t[bg_key],
                text_color=t["text_fg"],
                scrollbar_button_color=t["btn_bg"],
                scrollbar_button_hover_color=t["accent"],
                corner_radius=radius,
                border_width=1,
                border_color=t["border"],
            )

        self._update_logo()

        if save:
            ini_set("theme", "name", name)
            if name == CUSTOM_THEME_NAME:
                save_custom_theme()

    @staticmethod
    def _is_light(hex_color: str) -> bool:
        value = hex_color.lstrip("#")
        r, g, b = (int(value[i : i + 2], 16) for i in (0, 2, 4))
        return (r * 299 + g * 587 + b * 114) / 1000 > 127

    # ---------- обои и логотип ----------

    @staticmethod
    def _render_wallpaper_image(spec, width: int, height: int):
        from PIL import Image, ImageDraw

        width = max(width, 200)
        height = max(height, 200)
        if spec == "stars":
            top, bottom = (11, 16, 38), (27, 42, 74)
            img = Image.new("RGB", (width, height))
            px = img.load()
            for y in range(height):
                k = y / max(height - 1, 1)
                color = tuple(int(top[i] + (bottom[i] - top[i]) * k) for i in range(3))
                for x in range(width):
                    px[x, y] = color
            draw = ImageDraw.Draw(img)
            rng = random.Random(42)
            for _ in range(width * height // 2200):
                x, y = rng.randrange(width), rng.randrange(height)
                size = rng.choice((1, 1, 1, 2, 2, 3))
                shade = rng.choice(((255, 255, 255), (200, 210, 255), (255, 230, 180)))
                if size == 1:
                    draw.point((x, y), fill=shade)
                else:
                    draw.ellipse((x, y, x + size - 1, y + size - 1), fill=shade)
            return img
        if isinstance(spec, tuple) and spec[0] == "gradient":
            colors = [tuple(int(c.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)) for c in spec[1:]]
            img = Image.new("RGB", (width, height))
            px = img.load()
            stops = len(colors) - 1
            for y in range(height):
                k = y / max(height - 1, 1)
                seg = min(int(k * stops), stops - 1)
                local = k * stops - seg
                c1, c2 = colors[seg], colors[seg + 1]
                color = tuple(int(c1[i] + (c2[i] - c1[i]) * local) for i in range(3))
                for x in range(width):
                    px[x, y] = color
            return img
        return None

    def _apply_wallpaper(self, theme: dict) -> None:
        spec = theme.get("wallpaper")
        if spec is None:
            if self._wallpaper is not None:
                self._wallpaper.destroy()
                self._wallpaper = None
            self._wall_spec = None
            return
        self._wall_spec = spec
        width = max(self.root.winfo_width(), 200)
        height = max(self.root.winfo_height(), 200)
        img = self._render_wallpaper_image(spec, width, height)
        if img is None:
            return
        self._wall_size = (width, height)
        from PIL import Image as PILImage

        ctk_image = ctk.CTkImage(light_image=img, dark_image=img, size=(width, height))
        if self._wallpaper is None:
            self._wallpaper = ctk.CTkLabel(self.root, text="")
            self._wallpaper.place(x=0, y=0, relwidth=1, relheight=1)
            self._wallpaper.lower()
        else:
            self._wallpaper.configure(image=ctk_image)

    def _on_configure(self, event) -> None:
        if event.widget is not self.root or self._wall_spec is None:
            return
        width, height = self.root.winfo_width(), self.root.winfo_height()
        if (width, height) == self._wall_size:
            return
        if self._wall_job is not None:
            try:
                self.root.after_cancel(self._wall_job)
            except tk.TclError:
                pass
        self._wall_job = self.root.after(
            300, lambda: self._apply_wallpaper(self.theme_colors)
        )

    def _update_logo(self) -> None:
        if self._logo_label is None:
            return
        try:
            from PIL import Image, ImageDraw

            accent = self.theme_colors["accent"]
            img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.rounded_rectangle([2, 2, 61, 61], radius=16, fill=self._hex_to_rgb(accent))
            white = (255, 255, 255, 255)
            draw.line([(14, 26), (38, 26)], fill=white, width=6)
            draw.line([(48, 26), (44, 20), (44, 32)], fill=white, width=6)
            draw.line([(50, 40), (26, 40)], fill=white, width=6)
            draw.line([(16, 40), (20, 34), (20, 46)], fill=white, width=6)
            self._logo_label.configure(
                image=ctk.CTkImage(light_image=img, dark_image=img, size=(26, 26))
            )
        except Exception:  # noqa: BLE001
            pass

    # ---------------- Направление ----------------

    def _set_direction_values(self, forward: str, reverse: str, saved: str = "auto") -> None:
        self._dir_labels = {"auto": "Авто", "forward": forward, "reverse": reverse}
        self.direction_seg.configure(values=["Авто", forward, reverse])
        self.direction_seg.set(self._dir_labels.get(saved, "Авто"))
        self.direction_var.set(saved)

    def _on_direction_seg(self, value: str) -> None:
        for code, label in self._dir_labels.items():
            if label == value:
                self.direction_var.set(code)
                break
        self._save_pair_choice()

    # ---------------- Языковые пары ----------------

    @staticmethod
    def _collect_pairs():
        pairs = set()
        try:
            for lang in atranslate.get_installed_languages():
                for tr in lang.translations_from:
                    underlying = getattr(tr, "underlying", tr)
                    pkg = getattr(underlying, "pkg", None)
                    if pkg is not None and pkg.from_code != pkg.to_code:
                        pairs.add((pkg.from_code, pkg.to_code))
        except Exception:  # noqa: BLE001
            pass
        return sorted(pairs)

    @staticmethod
    def _pair_label(pair: tuple[str, str]) -> str:
        return f"{pair[0].upper()} ⇄ {pair[1].upper()}"

    def _reload_pairs(self) -> None:
        self.pairs = self._collect_pairs()
        self.pair_combo.configure(values=[self._pair_label(p) for p in self.pairs])
        if not self.pairs:
            self.status_var.set(
                "Модели не найдены. Запустите install_models.py (нужен интернет)."
            )
            return
        saved = ini_get("ui", "pair", "en-ru")
        chosen = None
        for p in self.pairs:
            if "-".join(p) == saved:
                chosen = p
                break
        if chosen is None:
            for p in self.pairs:
                if set(p) == {"en", "ru"}:
                    chosen = p
                    break
        if chosen is None:
            chosen = self.pairs[0]
        self.pair_var.set(self._pair_label(chosen))
        self._on_pair_change(restore_direction=True)

    def _current_pair(self):
        label = self.pair_var.get()
        for p in self.pairs:
            if self._pair_label(p) == label:
                return p
        return self.pairs[0] if self.pairs else None

    def _on_pair_change(self, restore_direction: bool = False) -> None:
        pair = self._current_pair()
        if pair is None:
            return
        a, b = pair
        saved = ini_get("ui", "direction", "auto") if restore_direction else "auto"
        if saved not in ("auto", "forward", "reverse"):
            saved = "auto"
        self._set_direction_values(
            f"{a.upper()} → {b.upper()}", f"{b.upper()} → {a.upper()}", saved
        )
        self._set_pane_titles(
            f"Исходный текст ({a.upper()} / {b.upper()})", "Перевод"
        )
        self._save_pair_choice()

    def _set_pane_titles(self, src: str, dst: str) -> None:
        if len(self._pane_titles) >= 2:
            self._pane_titles[0].configure(text=src)
            self._pane_titles[1].configure(text=dst)

    def _save_pair_choice(self) -> None:
        pair = self._current_pair()
        if pair:
            ini_set("ui", "pair", "-".join(pair))
        ini_set("ui", "direction", self.direction_var.get())

    def _get_translator(self, from_code: str, to_code: str):
        key = (from_code, to_code)
        if key not in self.translators:
            langs = {l.code: l for l in atranslate.get_installed_languages()}
            src, dst = langs.get(from_code), langs.get(to_code)
            if src is None or dst is None:
                return None
            self.translators[key] = src.get_translation(dst)
        return self.translators[key]

    def _pick_translator(self, text: str):
        pair = self._current_pair()
        if pair is None:
            return None, ""
        a, b = pair
        direction = self.direction_var.get()
        if direction == "auto":
            code = detect_lang_code(text, (a, b))
            src, dst = code, b if code == a else a
            label = f"{src.upper()} → {dst.upper()} (авто)"
        elif direction == "reverse":
            src, dst = b, a
            label = f"{b.upper()} → {a.upper()}"
        else:
            src, dst = a, b
            label = f"{a.upper()} → {b.upper()}"
        return self._get_translator(src, dst), label

    # ---------------- Модели ----------------

    def _load_models(self) -> None:
        def work() -> None:
            try:
                pairs = self._collect_pairs()
                self.worker_queue.put(("models_ready", pairs))
            except Exception as exc:  # noqa: BLE001
                self.worker_queue.put(("error", f"Не удалось загрузить модели: {exc}"))

        self.translate_btn.configure(state=tk.DISABLED)
        threading.Thread(target=work, daemon=True).start()

    # ---------------- Перевод ----------------

    def translate(self) -> None:
        if self.translating or not self.pairs:
            return
        text = self.src_text.get("1.0", "end-1c").strip()
        if not text:
            self.status_var.set("Введите текст для перевода.")
            return
        translator, label = self._pick_translator(text)
        if translator is None:
            self.status_var.set("Нет переводчика для выбранной пары.")
            return
        self._start_translation(translator, text, label, ("done", None))

    def _start_translation(self, translator, text: str, label: str, done_kind: tuple) -> None:
        self.translating = True
        self.translate_btn.configure(state=tk.DISABLED)
        self.status_var.set(f"Перевод ({label})…")

        def work() -> None:
            try:
                result = translator.translate(text)
                self.worker_queue.put((done_kind[0], (result, label)))
            except Exception as exc:  # noqa: BLE001
                self.worker_queue.put(("error", f"Ошибка перевода: {exc}"))

        threading.Thread(target=work, daemon=True).start()

    def _poll_worker(self) -> None:
        try:
            while True:
                kind, payload = self.worker_queue.get_nowait()
                if kind == "models_ready":
                    self.pairs = payload
                    self._reload_pairs()
                    if self.pairs:
                        self.translate_btn.configure(state=tk.NORMAL)
                        self.status_var.set(
                            "Модели загружены • офлайн • Ctrl+Enter, "
                            f"{self.hotkey_clip_var.get()} (буфер) или "
                            f"{self.hotkey_sel_var.get()} (выделение)"
                        )
                elif kind == "done":
                    result, label = payload
                    self._show_result_in_window(result)
                    self.status_var.set(f"Готово • {label} • офлайн")
                elif kind == "hotkey":
                    self._translate_clipboard()
                elif kind == "hotkey2":
                    self._translate_selection()
                elif kind == "hk_clip_result":
                    ok, error = payload
                    self._hotkey_status(ok, error, self.hotkey_clip_var.get(), "из буфера")
                elif kind == "hk_sel_result":
                    ok, error = payload
                    self._hotkey_status(ok, error, self.hotkey_sel_var.get(), "выделения")
                elif kind == "hotkey_done":
                    result, label = payload
                    self._show_result_in_window(result)
                    self._set_clipboard(result)
                    self._show_popup(result, label)
                    self.status_var.set(f"Перевод • {label} • в буфере обмена")
                elif kind == "sel_text":
                    text, label = payload
                    translator, _ = self._pick_translator(text)
                    if translator is None:
                        self._finish_selection_failed("нет переводчика")
                    else:
                        self._start_translation(
                            translator, text, label + " • выделение", ("hotkey_done", None)
                        )
                elif kind == "sel_fail":
                    self._finish_selection_failed(payload)
                elif kind == "tray_show":
                    self._show_main_window()
                elif kind == "tray_exit":
                    self._really_exit()
                elif kind == "avail_list":
                    self._render_available(getattr(self, "_avail_inner", None), payload)
                    self.status_var.set(
                        f"Доступно пакетов: {len(payload)}. Отметьте нужные и нажмите «Скачать отмеченные»."
                    )
                elif kind == "install_done":
                    ok, message = payload
                    self.status_var.set(message if ok else f"Установка: {message}")
                elif kind == "error":
                    self.status_var.set(str(payload))
                    self.translate_btn.configure(state=tk.NORMAL)
                self.translating = False
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._poll_worker)

    def _hotkey_status(self, ok: bool, error: str, name: str, what: str) -> None:
        if not ok:
            self.status_var.set(f"Горячая клавиша {name} ({what}) недоступна: {error}")

    def _show_result_in_window(self, result: str) -> None:
        if result:
            self.dst_text.configure(state=tk.NORMAL)
            self.dst_text.delete("1.0", tk.END)
            self.dst_text.insert("1.0", result)
            self.dst_text.configure(state="disabled")
        self.translate_btn.configure(state=tk.NORMAL)

    # ---------------- Из буфера обмена ----------------

    def _translate_clipboard(self) -> None:
        if not self.pairs:
            return
        if self.translating:
            self.status_var.set("Идёт предыдущий перевод — попробуйте через секунду.")
            return
        try:
            text = self.root.clipboard_get().strip()
        except tk.TclError:
            self.status_var.set("В буфере обмена нет текста.")
            return
        if not text:
            self.status_var.set("В буфере обмена нет текста.")
            return
        self._translate_quick(text)

    def _translate_quick(self, text: str) -> None:
        truncated = ""
        if len(text) > MAX_POPUP_SOURCE:
            text = text[:MAX_POPUP_SOURCE]
            truncated = " …"
        translator, label = self._pick_translator(text)
        if translator is None:
            self.status_var.set("Нет переводчика для этого языка.")
            return
        self._start_translation(translator, text, label + truncated, ("hotkey_done", None))

    # ---------------- Выделенный текст ----------------

    def _translate_selection(self) -> None:
        if not self.pairs:
            return
        if self.translating:
            self.status_var.set("Идёт предыдущий перевод — попробуйте через секунду.")
            return
        try:
            self._sel_saved_clip = self.root.clipboard_get()
        except tk.TclError:
            self._sel_saved_clip = None
        self.root.clipboard_clear()
        send_copy_shortcut()
        self._sel_polls_left = SELECTION_WAIT_MS // 100
        self.status_var.set("Беру выделенный текст…")
        self._poll_selection()

    def _poll_selection(self) -> None:
        try:
            text = self.root.clipboard_get().strip()
        except tk.TclError:
            text = ""
        if text:
            self._sel_saved_clip = None
            self._translate_quick(text)
            return
        if self._sel_polls_left > 0:
            self._sel_polls_left -= 1
            self.root.after(100, self._poll_selection)
        else:
            self._finish_selection_failed(
                "не удалось скопировать выделение (в активной программе нет выделенного текста)"
            )

    def _finish_selection_failed(self, reason: str) -> None:
        if self._sel_saved_clip is not None:
            self._set_clipboard(self._sel_saved_clip)
            self._sel_saved_clip = None
        self.status_var.set(f"Выделение: {reason}")

    # ---------------- Всплывашка и буфер ----------------

    def _set_clipboard(self, text: str) -> None:
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
        except tk.TclError:
            pass

    def _show_popup(self, text: str, label: str) -> None:
        self._close_popup()
        t = self.theme_colors
        pop = tk.Toplevel(self.root)
        pop.overrideredirect(True)
        pop.attributes("-topmost", True)

        frame = tk.Frame(
            pop, bg=t["text_bg"], highlightthickness=1, highlightbackground=t["border"]
        )
        frame.pack(fill=tk.BOTH, expand=True)
        header = tk.Label(
            frame,
            text=f"{label}  •  перевод в буфере обмена",
            bg=t["accent"],
            fg=t["accent_fg"],
            font=(t["font_family"], 9, "bold"),
            anchor="w",
            padx=10,
            pady=4,
        )
        header.pack(fill=tk.X)
        body = tk.Label(
            frame,
            text=text,
            bg=t["text_bg"],
            fg=t["text_fg"],
            font=(t["font_family"], t["font_size"]),
            wraplength=460,
            justify=tk.LEFT,
            anchor="nw",
            padx=10,
            pady=8,
        )
        body.pack(fill=tk.BOTH, expand=True)

        self._popup = pop
        close = lambda event=None: self._close_popup()  # noqa: E731
        for widget in (pop, frame, header, body):
            widget.bind("<Button-1>", close)

        x = self.root.winfo_pointerx() + 16
        y = self.root.winfo_pointery() + 20
        x = min(x, self.root.winfo_screenwidth() - 520)
        y = min(y, self.root.winfo_screenheight() - 300)
        pop.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        self._popup_job = self.root.after(12000, self._close_popup)

    def _close_popup(self) -> None:
        if self._popup_job is not None:
            try:
                self.root.after_cancel(self._popup_job)
            except tk.TclError:
                pass
            self._popup_job = None
        if self._popup is not None:
            try:
                self._popup.destroy()
            except tk.TclError:
                pass
            self._popup = None

    # ---------------- Горячие клавиши ----------------

    def _apply_hotkey_clip(self, choice: str, save: bool = False) -> None:
        def on_hotkey() -> None:
            self.worker_queue.put(("hotkey", ""))

        def on_result(ok: bool, error: str) -> None:
            self.worker_queue.put(("hk_clip_result", (ok, error)))

        mods, vk = HOTKEY_VARIANTS.get(choice, HOTKEY_VARIANTS[DEFAULT_HOTKEY_CLIPBOARD])
        self.hotkey_clip.start(mods, vk, on_hotkey, on_result)
        if save:
            ini_set("hotkey", "combo", choice)

    def _apply_hotkey_sel(self, choice: str, save: bool = False) -> None:
        def on_hotkey() -> None:
            self.worker_queue.put(("hotkey2", ""))

        def on_result(ok: bool, error: str) -> None:
            self.worker_queue.put(("hk_sel_result", (ok, error)))

        mods, vk = HOTKEY_VARIANTS.get(choice, HOTKEY_VARIANTS[DEFAULT_HOTKEY_SELECTION])
        self.hotkey_sel.start(mods, vk, on_hotkey, on_result)
        if save:
            ini_set("hotkey", "combo_selection", choice)

    # ---------------- Трей ----------------

    def _setup_tray(self) -> None:
        try:
            import pystray
            from PIL import Image, ImageDraw

            def make_image():
                accent = self._hex_to_rgb(self.theme_colors["accent"])
                img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                draw.rounded_rectangle([2, 2, 61, 61], radius=14, fill=accent)
                white = (255, 255, 255, 255)
                draw.line([(16, 26), (38, 26)], fill=white, width=6)
                draw.line([(48, 26), (44, 20), (44, 32)], fill=white, width=6)
                draw.line([(48, 40), (26, 40)], fill=white, width=6)
                draw.line([(16, 40), (20, 34), (20, 46)], fill=white, width=6)
                return img

            def show():
                self.worker_queue.put(("tray_show", ""))

            def clip():
                self.worker_queue.put(("hotkey", ""))

            def sel():
                self.worker_queue.put(("hotkey2", ""))

            def exit_app():
                self.worker_queue.put(("tray_exit", ""))

            menu = pystray.Menu(
                pystray.MenuItem("Показать", show, default=True),
                pystray.MenuItem("Перевести выделенное", sel),
                pystray.MenuItem("Перевести из буфера", clip),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Выход", exit_app),
            )
            self._tray = pystray.Icon("translator", make_image(), APP_TITLE, menu=menu)
            # ВАЖНО: свой daemon-поток вместо run_detached — иначе не-daemon
            # поток pystray не даёт процессу завершиться после закрытия окна.
            threading.Thread(target=self._tray.run, daemon=True, name="tray").start()
        except Exception as exc:  # noqa: BLE001
            self._tray = None
            self.status_var.set(f"(трей недоступен: {exc})")

    @staticmethod
    def _hex_to_rgb(value: str):
        value = value.lstrip("#")
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4)) + (255,)

    def _on_close_window(self) -> None:
        self._close_popup()
        self.root.withdraw()
        if not self._tray_hint_shown:
            self._tray_hint_shown = True
            self.status_var.set(
                "Свернуто в трей • "
                f"{self.hotkey_clip_var.get()} — буфер, "
                f"{self.hotkey_sel_var.get()} — выделение • Выход — через значок в трее"
            )

    def _show_main_window(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _on_root_destroy(self, event) -> None:
        if event.widget is self.root and not self._closing:
            self._really_exit()

    def _really_exit(self) -> None:
        self._closing = True
        self.hotkey_clip.stop()
        self.hotkey_sel.stop()
        if self._tray is not None:
            try:
                self._tray.stop()
            except Exception:  # noqa: BLE001
                pass
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    # ---------------- Диалог языков ----------------

    def open_languages_dialog(self) -> None:
        t = self.theme_colors
        win = ctk.CTkToplevel(self.root)
        win.title("Языковые пакеты")
        win.transient(self.root)
        win.geometry("520x460")
        win.configure(fg_color=t["bg"])

        frame = ctk.CTkFrame(win, fg_color="transparent")
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        installed_text = ", ".join(self._pair_label(p) for p in self.pairs) or "нет"
        ctk.CTkLabel(
            frame,
            text="Установленные пары:\n" + installed_text,
            font=self.base_font,
            text_color=t["text_fg"],
            justify=tk.LEFT,
        ).pack(anchor="w", pady=(0, 8))

        scroll = ctk.CTkScrollableFrame(
            frame,
            fg_color=t["text_bg"],
            label_text="Доступные для скачивания",
            label_font=self.base_font,
        )
        scroll.pack(fill=tk.BOTH, expand=True)
        scroll.configure(label_text_color=t["text_fg"])
        self._avail_inner = scroll

        self._mk_button(
            frame,
            "Показать доступные для скачивания (нужен интернет)",
            lambda: self._fetch_available_packages(),
        ).pack(anchor="w", pady=(8, 0))
        self._mk_button(frame, "Скачать отмеченные", self._install_selected, accent=True).pack(
            anchor="w", pady=(8, 0)
        )
        win.grab_set()

    def _fetch_available_packages(self) -> None:
        self.status_var.set("Получаю список пакетов (интернет)…")

        def work() -> None:
            try:
                available = [
                    p for p in apackage.get_available_packages() if p.type == "translate"
                ]
                self.worker_queue.put(("avail_list", available))
            except Exception as exc:  # noqa: BLE001
                self.worker_queue.put(("error", f"Не удалось получить список: {exc}"))

        threading.Thread(target=work, daemon=True).start()

    def _render_available(self, inner, available) -> None:
        if inner is None:
            return
        for child in inner.winfo_children():
            child.destroy()
        self._avail_vars = []
        self._avail_pkgs = []
        t = self.theme_colors
        installed = {f"{a}-{b}" for a, b in self.pairs}
        for pkg in sorted(available, key=lambda p: (p.from_code, p.to_code))[:300]:
            code = f"{pkg.from_code}-{pkg.to_code}"
            var = tk.BooleanVar(value=False)
            state = "disabled" if code in installed else "normal"
            note = "  (уже есть)" if code in installed else ""
            cb = ctk.CTkCheckBox(
                inner,
                text=f"{pkg.from_name} → {pkg.to_name}{note}",
                variable=var,
                state=state,
                font=self.base_font,
                fg_color=t["accent"],
                hover_color=t["btn_active"],
                text_color=t["text_fg"],
                text_color_disabled=t["btn_fg_disabled"],
                border_color=t["border"],
                checkmark_color=t["accent_fg"],
            )
            cb.pack(anchor="w", pady=2)
            self._avail_vars.append(var)
            self._avail_pkgs.append(pkg)

    def _install_selected(self) -> None:
        pkgs = getattr(self, "_avail_pkgs", [])
        vars_list = getattr(self, "_avail_vars", [])
        selected = [pkg for pkg, var in zip(pkgs, vars_list) if var.get()]
        if not selected:
            self.status_var.set("Сначала получите список и отметьте нужные пары.")
            return

        def work() -> None:
            done = 0
            for pkg in selected:
                try:
                    self.worker_queue.put(("install_done", (True, f"Скачиваю {pkg}…")))
                    path = pkg.download()
                    apackage.install_from_path(path)
                    done += 1
                except Exception as exc:  # noqa: BLE001
                    self.worker_queue.put(
                        ("install_done", (False, f"не удалось {pkg}: {exc}"))
                    )
            if done:
                atranslate.get_installed_languages.cache_clear()
                pairs = self._collect_pairs()
                self.worker_queue.put(("models_ready", pairs))
                self.worker_queue.put(
                    ("install_done", (True, f"Готово! Добавлено пар: {done}."))
                )

        threading.Thread(target=work, daemon=True).start()

    # ---------------- Действия ----------------

    def swap_texts(self) -> None:
        src = self.src_text.get("1.0", "end-1c")
        dst = self.dst_text.get("1.0", "end-1c")
        self.src_text.delete("1.0", tk.END)
        self.src_text.insert("1.0", dst)
        self.dst_text.configure(state=tk.NORMAL)
        self.dst_text.delete("1.0", tk.END)
        self.dst_text.configure(state="disabled")
        if self.direction_var.get() == "forward":
            self.direction_var.set("reverse")
        elif self.direction_var.get() == "reverse":
            self.direction_var.set("forward")
        self.direction_seg.set(self._dir_labels.get(self.direction_var.get(), "Авто"))
        self._save_pair_choice()

    def clear_all(self) -> None:
        self.src_text.delete("1.0", tk.END)
        self.dst_text.configure(state=tk.NORMAL)
        self.dst_text.delete("1.0", tk.END)
        self.dst_text.configure(state="disabled")
        self.src_text.focus_set()

    def copy_result(self) -> None:
        text = self.dst_text.get("1.0", "end-1c")
        if text:
            self._set_clipboard(text)
            self.status_var.set("Перевод скопирован в буфер обмена.")


# ---------------- Самопроверка (для собранного .exe) ----------------


def run_self_test() -> int:
    """Без GUI: модели, перевод, обе горячие клавиши, библиотеки."""
    lines: list[str] = []

    def check_hotkey(name: str) -> None:
        result: list[tuple[bool, str]] = []
        manager = HotkeyManager()
        mods, vk = HOTKEY_VARIANTS[name]
        manager.start(mods, vk, lambda: None, lambda ok, err: result.append((ok, err)))
        deadline = 5.0
        while not result and deadline > 0:
            deadline -= 0.1
            threading.Event().wait(0.1)
        if result:
            ok, err = result[0]
            lines.append(f"hotkey {name}={'OK' if ok else 'FAIL: ' + err}")
        else:
            lines.append(f"hotkey {name}=TIMEOUT")
        manager.stop()

    check_hotkey(DEFAULT_HOTKEY_CLIPBOARD)
    check_hotkey(DEFAULT_HOTKEY_SELECTION)

    try:
        import customtkinter  # noqa: F401
        import pystray  # noqa: F401
        from PIL import Image  # noqa: F401

        lines.append("ui_libs=OK")
    except Exception as exc:  # noqa: BLE001
        lines.append(f"ui_libs=FAIL: {exc!r}")

    try:
        code = detect_lang_code("Привет, как дела?", ("en", "ru"))
        code2 = detect_lang_code("Guten Morgen, wie geht es dir?", ("en", "de"))
        lines.append(f"detect={code},{code2}")
    except Exception as exc:  # noqa: BLE001
        lines.append(f"detect=FAIL: {exc!r}")

    try:
        # обои должны рендериться без GUI
        img1 = TranslatorApp._render_wallpaper_image("stars", 320, 200)
        img2 = TranslatorApp._render_wallpaper_image(
            ("gradient", "#111111", "#ff0000"), 320, 200
        )
        lines.append(f"wallpaper={'OK' if img1 and img2 else 'FAIL'}")
    except Exception as exc:  # noqa: BLE001
        lines.append(f"wallpaper=FAIL: {exc!r}")

    try:
        langs = {l.code: l for l in atranslate.get_installed_languages()}
        en, ru = langs["en"], langs["ru"]
        out1 = en.get_translation(ru).translate("The weather is nice today.")
        out2 = ru.get_translation(en).translate("Погода сегодня хорошая.")
        lines.append(f"en_ru={out1}")
        lines.append(f"ru_en={out2}")
        lines.append("APP=OK")
    except Exception as exc:  # noqa: BLE001
        lines.append(f"APP=FAIL: {exc!r}")

    result_path = os.path.join(os.getcwd(), "selftest_result.txt")
    with open(result_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


def main() -> None:
    if "--test" in sys.argv:
        sys.exit(run_self_test())
    ctk.set_appearance_mode("light")
    root = ctk.CTk()
    TranslatorApp(root, use_tray=True)
    root.mainloop()


if __name__ == "__main__":
    main()
