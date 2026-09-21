# -*- coding: utf-8 -*-
"""Смоук-тест GUI: открывает окно, ждёт загрузку моделей, делает автоперевод."""

import tkinter as tk

import customtkinter as ctk

import app as appmod

root = ctk.CTk()
a = appmod.TranslatorApp(root)
result = {}


def check(counter: int = 0) -> None:
    out = a.dst_text.get("1.0", "end-1c").strip()
    if out or counter > 60:
        result["out"] = out
        result["status"] = a.status_var.get()
        root.destroy()
    else:
        root.after(250, lambda: check(counter + 1))


def start_translate() -> None:
    a.src_text.insert("1.0", "The weather is nice today.")
    a.translate()
    root.after(200, lambda: check())


def wait_models() -> None:
    if a.pairs:
        start_translate()
    elif not root.winfo_exists():
        return
    else:
        root.after(500, wait_models)


root.after(500, wait_models)
root.after(60000, root.destroy)  # предохранитель

try:
    root.mainloop()
except tk.TclError:
    pass

print("OUT:", result.get("out", "<пусто>"))
print("STATUS:", result.get("status", "<нет>"))
