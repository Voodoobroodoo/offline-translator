# -*- coding: utf-8 -*-
"""Тест сценария горячей клавиши: буфер -> перевод -> всплывашка -> буфер."""

import tkinter as tk

import customtkinter as ctk

import app as appmod

PHRASE = "How do I get to the train station?"

root = ctk.CTk()
a = appmod.TranslatorApp(root)
result = {}


def check(counter: int = 0) -> None:
    clip = ""
    try:
        clip = root.clipboard_get()
    except tk.TclError:
        pass
    popup_ready = a._popup is not None
    if (clip and clip != PHRASE and popup_ready) or counter > 80:
        result["clip"] = clip
        result["popup"] = popup_ready
        result["status"] = a.status_var.get()
        root.destroy()
    else:
        root.after(250, lambda: check(counter + 1))


def fire() -> None:
    root.clipboard_clear()
    root.clipboard_append(PHRASE)
    a.worker_queue.put(("hotkey", ""))  # как будто нажали глобальную клавишу
    root.after(200, lambda: check())


def wait_models() -> None:
    if a.pairs:
        fire()
    else:
        root.after(500, wait_models)


root.after(500, wait_models)
root.after(90000, root.destroy)  # предохранитель

try:
    root.mainloop()
except tk.TclError:
    pass

print("CLIP:", result.get("clip", "<пусто>"))
print("POPUP:", "да" if result.get("popup") else "нет")
print("STATUS:", result.get("status", "<нет>"))
