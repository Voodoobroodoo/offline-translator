# -*- coding: utf-8 -*-
"""Тест перевода в режиме MiniSBD (без stanza/torch) + кэширование MiniSBD-моделей."""

import os
import pathlib
import time

os.environ["ARGOS_CHUNK_TYPE"] = "MINISBD"

import argostranslate.settings as settings
import argostranslate.translate as t

start = time.time()
langs = {l.code: l for l in t.get_installed_languages()}
en, ru = langs["en"], langs["ru"]
e2r = en.get_translation(ru)
r2e = ru.get_translation(en)

print("EN->RU:", e2r.translate("Hello! This offline translator works without internet. How are you?"))
print("RU->EN:", r2e.translate("Привет! Проверяю перевод без интернета. Сегодня отличная погода."))
print(f"OK за {time.time() - start:.1f} c")

minisbd_dir = pathlib.Path(settings.data_dir) / "minisbd"
if minisbd_dir.exists():
    for f in sorted(minisbd_dir.iterdir()):
        print("cached:", f.name, f.stat().st_size // 1024, "KB")
else:
    print("minisbd cache NOT created")
