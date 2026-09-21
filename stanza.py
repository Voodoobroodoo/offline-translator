# -*- coding: utf-8 -*-
"""Заглушка stanza для сборки одного .exe.

PyInstaller при анализе находит этот файл раньше библиотеки из site-packages
и упаковывает его вместо тяжёлой stanza (которая тянет torch).
Приложение работает в режиме ARGOS_CHUNK_TYPE=MINISBD и stanza не вызывает.
"""

__version__ = "0.0.0-stub"


def Pipeline(*args, **kwargs):  # noqa: ANN002, ANN003
    raise RuntimeError("stanza заглушен: приложение должно работать в режиме MINISBD")
