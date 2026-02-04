#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Объединяет profiles.json и файл категории с продавцами:
каждому профилю (id + name) назначается 5 продавцов из категории.
Запуск: python merge_profiles_sellers.py
"""

import json
from pathlib import Path

# Пути к файлам (от корня проекта)
PROJECT_ROOT = Path(__file__).parent
PROFILES_PATH = PROJECT_ROOT / "profiles" / "data" / "profiles.json"
CATEGORY_PATH = PROJECT_ROOT / "server" / "category_tarelki_02.02.2026_21-35-51.json"
OUTPUT_PATH = PROJECT_ROOT / "server" / "profiles_with_sellers.json"

SELLERS_PER_PROFILE = 5


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    profiles = load_json(PROFILES_PATH)
    category_data = load_json(CATEGORY_PATH)
    sellers = category_data.get("sellers", [])

    if not sellers:
        print("В файле категории нет продавцов (sellers).")
        return

    n = len(sellers)
    result = []

    for i, profile in enumerate(profiles):
        # Берём 5 продавцов по кругу (индексы i*5, i*5+1, ... i*5+4 по модулю n)
        start = (i * SELLERS_PER_PROFILE) % n
        selected = []
        for j in range(SELLERS_PER_PROFILE):
            idx = (start + j) % n
            selected.append(sellers[idx])

        result.append({
            "id": profile["id"],
            "name": profile["name"],
            "sellers": selected,
        })

    save_json(OUTPUT_PATH, result)
    print(f"Готово: {len(result)} профилей, каждому по {SELLERS_PER_PROFILE} продавцов.")
    print(f"Результат: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
