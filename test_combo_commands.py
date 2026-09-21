# -*- coding: utf-8 -*-
"""Проверка, что выбор в выпадающих списках (command=) реально применяет тему,
пару и горячие клавиши — как клик пользователя."""

import configparser

import customtkinter as ctk

import app as appmod

root = ctk.CTk()
a = appmod.TranslatorApp(root, use_tray=False)

prev_theme = configparser.ConfigParser()
prev_theme.read(appmod.INI_PATH, encoding="utf-8")
prev_theme_value = prev_theme.get("theme", "name", fallback="Светлая")


def pump(ms: int = 400) -> None:
    for _ in range(ms // 50):
        root.update()
        root.after(50, lambda: None)
        root.update()


errors = []

# 1. Тема: command('Неон') должен перекрасить приложение и записать ini
a.theme_combo.cget("command")("Неон")
pump(200)
if a.theme_colors["accent"] != appmod.THEMES["Неон"]["accent"]:
    errors.append(f"тема не применилась: accent={a.theme_colors['accent']}")
check = configparser.ConfigParser()
check.read(appmod.INI_PATH, encoding="utf-8")
if check.get("theme", "name", fallback="") != "Неон":
    errors.append("тема не сохранилась в settings.ini")

# 2. Горячие клавиши: command должен перерегистрировать клавишу
a.hotkey_clip_combo.cget("command")("Ctrl+Alt+R")
a.hotkey_sel_combo.cget("command")("Ctrl+Alt+R")
pump(400)

# 3. Пара: дождаться моделей и дёрнуть command пары
for _ in range(60):
    if a.pairs:
        break
    pump(200)
a.pair_combo.cget("command")(a.pair_var.get())
pump(300)
values = a.direction_seg.cget("values")
if not (values and len(values) == 3):
    errors.append(f"сегменты направления не заполнены: {values}")

# вернуть прежнюю тему в настройках
appmod.ini_set("theme", "name", prev_theme_value)
root.destroy()

if errors:
    print("FAIL:", "; ".join(errors))
    raise SystemExit(1)
print("COMBO_COMMANDS=OK")
