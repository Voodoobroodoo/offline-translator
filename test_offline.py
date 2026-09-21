# -*- coding: utf-8 -*-
"""Быстрая проверка офлайн-перевода (в обе стороны)."""

import os
import time

os.environ.setdefault("ARGOS_CHUNK_TYPE", "MINISBD")

import argostranslate.translate as t

start = time.time()
langs = {l.code: l for l in t.get_installed_languages()}
en, ru = langs["en"], langs["ru"]
e2r = en.get_translation(ru)
r2e = ru.get_translation(en)

print("EN->RU:", e2r.translate("Hello! This offline translator works without internet. How are you?"))
print("RU->EN:", r2e.translate("Привет! Проверяю перевод без интернета. Сегодня отличная погода."))
print(f"OK за {time.time() - start:.1f} c")
