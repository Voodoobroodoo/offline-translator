# -*- coding: utf-8 -*-
"""Скриншоты окна во всех темах -> preview_<slug>.png (для быстрого просмотра)."""

import time
import tkinter as tk

import customtkinter as ctk
from PIL import ImageGrab

import app as appmod

SRC = "The weather is nice today. Select any text, copy it, press Ctrl+Alt+T!"
DST = "Погода сегодня хорошая. Выделите текст, скопируйте и нажмите Ctrl+Alt+T!"

root = ctk.CTk()
a = appmod.TranslatorApp(root, use_tray=False)

# Сразу подставим примеры текстов, чтобы превью выглядели живыми
def fill() -> None:
    a.src_text.insert("1.0", SRC)
    a.dst_text.configure(state=tk.NORMAL)
    a.dst_text.insert("1.0", DST)
    a.dst_text.configure(state=tk.DISABLED)
    a.status_var.set("Готово к работе • Ctrl+Alt+T — перевод из буфера обмена")

# Подождать, пока модели загрузятся и тема применится
root.after(2500, fill)

def shoot() -> None:
    root.update_idletasks()
    root.update()
    for name in appmod.THEMES:
        a.theme_var.set(name)
        a.apply_theme(name, save=False)
        root.update_idletasks()
        root.update()
        time.sleep(0.3)
        x, y = root.winfo_rootx(), root.winfo_rooty()
        w, h = root.winfo_width(), root.winfo_height()
        slug = appmod.THEME_SLUGS.get(name, name)
        img = ImageGrab.grab(bbox=(x - 2, y - 32, x + w + 2, y + h + 2))
        path = f"preview_{slug}.png"
        img.save(path)
        print("saved", path)
    a.apply_theme(appmod.DEFAULT_THEME, save=False)
    root.destroy()

root.after(3500, shoot)
root.mainloop()
