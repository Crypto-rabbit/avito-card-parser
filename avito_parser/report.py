from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .parser import AvitoCard


REPORT_HEADERS = [
    "Позиция",
    "Категория",
    "Комплектующие -> Ножки",
    "Заголовок",
    "Пр.Всего",
    "Пр.Сегод.",
    "Цена",
    "Продвижения",
    "Время поднятия",
    "Описание",
    "Кол-во знак.",
    "Доставка",
    "№ объяв.",
    "Позвонить",
    "Написать ✉️",
    "Реквизиты проверены",
    "Характеристики",
    "Состояние",
    "Доступность",
    "Ширина",
    "Высота",
    "Длина",
    "Длина в разложенном виде",
    "Длина в сложенном виде",
    "Количество кресел",
    "Количество стульев",
    "Материал основания",
    "Материал столешницы",
    "Основной цвет",
    "Основной цвет столешницы",
    "Раскладной механизм",
    "Раскладной механизм у стола",
    "Состав комплекта",
    "Тип стола",
    "Тип товара",
    "Форма",
    "Форма стола",
    "Что есть у товара",
    "Продавец",
    "Широта",
    "Долгота",
    "Город",
    "Ссылка",
    "Фото шт.",
    "фото1",
    "фото2",
    "фото3",
]


def card_to_report_row(card: AvitoCard, position: int) -> dict[str, str]:
    chars = card.characteristics
    return {
        "Позиция": str(position),
        "Категория": card.category,
        "Комплектующие -> Ножки": card.breadcrumbs,
        "Заголовок": card.title,
        "Пр.Всего": card.total_views,
        "Пр.Сегод.": card.today_views,
        "Цена": card.price,
        "Продвижения": card.promotion,
        "Время поднятия": card.boost_time,
        "Описание": card.description,
        "Кол-во знак.": card.description_chars,
        "Доставка": card.delivery,
        "№ объяв.": card.item_id,
        "Позвонить": card.can_call,
        "Написать ✉️": card.can_message,
        "Реквизиты проверены": card.verified_requisites,
        "Характеристики": card.characteristics_text,
        "Состояние": chars.get("Состояние", ""),
        "Доступность": chars.get("Доступность", ""),
        "Ширина": chars.get("Ширина", ""),
        "Высота": chars.get("Высота", ""),
        "Длина": chars.get("Длина", ""),
        "Длина в разложенном виде": chars.get("Длина в разложенном виде", ""),
        "Длина в сложенном виде": chars.get("Длина в сложенном виде", ""),
        "Количество кресел": chars.get("Количество кресел", ""),
        "Количество стульев": chars.get("Количество стульев", ""),
        "Материал основания": chars.get("Материал основания", ""),
        "Материал столешницы": chars.get("Материал столешницы", ""),
        "Основной цвет": chars.get("Основной цвет", ""),
        "Основной цвет столешницы": chars.get("Основной цвет столешницы", ""),
        "Раскладной механизм": chars.get("Раскладной механизм", ""),
        "Раскладной механизм у стола": chars.get("Раскладной механизм у стола", ""),
        "Состав комплекта": chars.get("Состав комплекта", ""),
        "Тип стола": chars.get("Тип стола", ""),
        "Тип товара": chars.get("Тип товара", ""),
        "Форма": chars.get("Форма", ""),
        "Форма стола": chars.get("Форма стола", ""),
        "Что есть у товара": chars.get("Что есть у товара", ""),
        "Продавец": card.seller,
        "Широта": card.latitude,
        "Долгота": card.longitude,
        "Город": card.location,
        "Ссылка": card.url,
        "Фото шт.": card.images_count,
        "фото1": card.photo1,
        "фото2": card.photo2,
        "фото3": card.photo3,
    }


def write_report_csv(path: Path, cards: list[AvitoCard]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=REPORT_HEADERS)
        writer.writeheader()
        for index, card in enumerate(cards, start=1):
            writer.writerow(card_to_report_row(card, index))


def write_raw_json(path: Path, cards: list[AvitoCard]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([card.to_dict() for card in cards], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def report_rows_for_sheets(cards: list[AvitoCard], start_position: int = 1) -> list[list[Any]]:
    rows = []
    for offset, card in enumerate(cards):
        row = card_to_report_row(card, start_position + offset)
        rows.append([row.get(header, "") for header in REPORT_HEADERS])
    return rows

