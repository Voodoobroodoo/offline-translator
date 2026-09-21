# -*- coding: utf-8 -*-
"""Одноразовая загрузка офлайн-моделей EN<->RU (интернет нужен только здесь)."""

import os

# Лёгкий режим разбиения на предложения — задать ДО импорта argostranslate
os.environ.setdefault("ARGOS_CHUNK_TYPE", "MINISBD")

import argostranslate.package as package


def main() -> None:
    print("Получаю список доступных пакетов...")
    available = package.get_available_packages()
    wanted = [("en", "ru"), ("ru", "en")]

    for from_code, to_code in wanted:
        candidates = [
            p for p in available if p.from_code == from_code and p.to_code == to_code
        ]
        if not candidates:
            print(f"!! Пакет {from_code}->{to_code} не найден в репозитории")
            continue
        pkg = candidates[0]
        print(f"Загрузка: {pkg} ...")
        path = pkg.download()
        package.install_from_path(path)
        print(f"Установлено: {from_code} -> {to_code}")

    import argostranslate.translate as translate

    langs = {l.code: l for l in translate.get_installed_languages()}
    ok = True
    for from_code, to_code in wanted:
        try:
            if not langs[from_code].get_translation(langs[to_code]):
                ok = False
        except KeyError:
            ok = False

    if ok:
        print("Прогреваю кэш MiniSBD (короткий тестовый перевод)...")
        try:
            langs["en"].get_translation(langs["ru"]).translate("Hello.")
            langs["ru"].get_translation(langs["en"]).translate("Привет.")
            print("Кэш MiniSBD готов, дальше всё работает офлайн.")
        except Exception as exc:  # noqa: BLE001
            print(f"Прогрев не удался (не критично): {exc}")
        print("Готово! Все модели установлены, переводчик работает офлайн.")
    else:
        print("Внимание: не все модели установлены, перезапустите скрипт.")


if __name__ == "__main__":
    main()
