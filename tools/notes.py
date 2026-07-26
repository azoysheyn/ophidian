"""Чтение и запись frontmatter заметок Obsidian.

Намеренно поддерживает только то подмножество YAML, которое реально
встречается в этом волте: плоские пары ключ-значение, блочные списки
и инлайновые списки. Без зависимостей.
"""

import re
from pathlib import Path

DELIM = "---"
# Значение приходится закавычивать, если оно начинается с символа,
# который YAML прочтёт как структуру, либо содержит ссылку [[...]], либо
# содержит запятую (иначе инлайновый список растащит его на части).
_NEEDS_QUOTES_PREFIX = "[{&*!|>%@`#"
_TABLE_ROW = re.compile(r"^\|(.+)\|\s*$")


def _unquote(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _split_inline(value):
    """Разбить содержимое инлайнового списка [a, "b, c"] по запятым верхнего
    уровня — запятые внутри кавычек не считаются разделителями."""
    inner = value[1:-1].strip()
    if not inner:
        return []
    items = []
    current = []
    quote = None
    for char in inner:
        if quote:
            current.append(char)
            if char == quote:
                quote = None
            continue
        if char in "\"'":
            quote = char
            current.append(char)
            continue
        if char == ",":
            items.append(_unquote("".join(current).strip()))
            current = []
            continue
        current.append(char)
    items.append(_unquote("".join(current).strip()))
    return items


def parse_note(text):
    """-> (frontmatter, body). Пустое значение — None, список — list[str]."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != DELIM:
        return {}, text

    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == DELIM:
            end = index
            break
    if end is None:
        return {}, text

    fm = {}
    key = None
    index = 1
    while index < end:
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue

        if line.startswith((" ", "\t")) and stripped.startswith("- "):
            if key is not None:
                if not isinstance(fm[key], list):
                    fm[key] = []
                fm[key].append(_unquote(stripped[2:].strip()))
            index += 1
            continue

        if ":" not in stripped:
            index += 1
            continue

        key, _, raw = stripped.partition(":")
        key = key.strip()
        raw = raw.strip()
        if not raw:
            fm[key] = None
        elif raw.startswith("[") and raw.endswith("]"):
            fm[key] = _split_inline(raw)
        else:
            fm[key] = _unquote(raw)
        index += 1

    body = "\n".join(lines[end + 1 :])
    return fm, body


def _quote_if_needed(text):
    if not text:
        return '""'
    if text[0] in _NEEDS_QUOTES_PREFIX or text != text.strip() or "," in text:
        return '"' + text + '"'
    return text


def _format_value(value):
    if value is None:
        return ""
    if isinstance(value, list):
        return "[" + ", ".join(_quote_if_needed(str(item)) for item in value) + "]"
    return _quote_if_needed(str(value))


def format_note(fm, body):
    lines = [DELIM]
    for key, value in fm.items():
        rendered = _format_value(value)
        lines.append(f"{key}: {rendered}" if rendered else f"{key}:")
    lines.append(DELIM)
    return "\n".join(lines) + "\n" + body


def parse_table(text):
    """Строки markdown-таблицы. Первая — заголовок, разделитель отброшен."""
    rows = []
    for line in text.split("\n"):
        match = _TABLE_ROW.match(line)
        if not match:
            continue
        cells = [cell.strip() for cell in match.group(1).split("|")]
        if all(set(cell) <= set("- ") for cell in cells):
            continue
        rows.append(cells)
    return rows


def read_note(path):
    return parse_note(Path(path).read_text(encoding="utf-8"))


def write_note(path, fm, body):
    Path(path).write_text(format_note(fm, body), encoding="utf-8")


# --- Таблица транслитерации: общий контракт для check.py и build.py ------
#
# Оба модуля проверяют одну и ту же таблицу (Transliteration.md) по одним и
# тем же правилам — заголовок, число колонок, число строк данных, пустые
# ячейки. Раньше эта логика и её константы были продублированы в обоих
# файлах и успели разойтись в формулировках. Здесь она определена один раз;
# check.py копит найденные проблемы в список ошибок, build.py останавливается
# на первой и поднимает BuildError — форматирование сообщения остаётся у
# каждого вызывающего модуля.

TABLE_HEADER = ["ipa", "latin-1", "latin-2", "latin-3", "cyr-1", "cyr-2"]
TABLE_COLUMNS = len(TABLE_HEADER)


def table_contract_issues(rows, expected_row_count):
    """Проверить разобранную таблицу фонем на соответствие контракту.

    -> список словарей-проблем (пустой, если таблица в порядке). Каждый
    словарь содержит "kind" и данные, нужные для конкретного сообщения:
    "missing", "header_columns", "header_mismatch", "row_count",
    "row_columns", "row_empty".
    """
    issues = []
    if not rows:
        issues.append({"kind": "missing"})
        return issues

    header = [cell.lower() for cell in rows[0]]
    if len(header) != TABLE_COLUMNS:
        issues.append({"kind": "header_columns", "got": len(header), "raw": rows[0]})
    elif header != TABLE_HEADER:
        issues.append({"kind": "header_mismatch", "got": header})

    data = rows[1:]
    if len(data) != expected_row_count:
        issues.append({"kind": "row_count", "got": len(data), "expected": expected_row_count})

    for row_number, cells in enumerate(data, start=2):
        if len(cells) != TABLE_COLUMNS:
            issues.append({"kind": "row_columns", "row": row_number, "cells": cells})
        elif any(not cell for cell in cells):
            issues.append({"kind": "row_empty", "row": row_number, "cells": cells})

    return issues


# --- Language/Phonology/Inventory.md --------------------------------------

_BOLD_LABEL = re.compile(r"^\*\*(.+?)\*\*:\s*(.*)$")
_BOLD_HEADING = re.compile(r"^\*\*(.+?)\*\*\s*$")
_BULLET_LABEL = re.compile(r"^-\s*(\w+):\s*(.*)$")


def _split_items(raw):
    return [item.strip() for item in raw.split(",") if item.strip()]


def parse_inventory(text):
    """Разобрать Language/Phonology/Inventory.md в списки фонем и категорий.

    -> {
        "consonants": {"simple": [...], "geminated": [...]},
        "vowels": {"short": [...], "long": [...], "double": [...]},
        "categories": {
            "consonants": {"soft": [...], "hard": [...]},
            "vowels": {"front": [...], "back": [...]},
        },
    }
    """
    result = {
        "consonants": {},
        "vowels": {},
        "categories": {"consonants": {}, "vowels": {}},
    }
    section = None
    subsection = None
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## "):
            section = stripped[3:].strip()
            subsection = None
            continue

        if section == "Категории":
            heading = _BOLD_HEADING.match(stripped)
            if heading:
                subsection = heading.group(1)
                continue
            bullet = _BULLET_LABEL.match(stripped)
            if bullet and subsection in ("Согласные", "Гласные"):
                label, raw = bullet.groups()
                key = "consonants" if subsection == "Согласные" else "vowels"
                result["categories"][key][label] = _split_items(raw)
            continue

        if section in ("Consonants", "Vowels"):
            bold = _BOLD_LABEL.match(stripped)
            if bold:
                label, raw = bold.groups()
                key = "consonants" if section == "Consonants" else "vowels"
                result[key][label] = _split_items(raw)

    return result


def expected_phoneme_count(inventory):
    """Ожидаемое число строк в Transliteration.md: согласные ("simple" —
    геминаты пишутся удвоением, отдельной строки не получают) + краткие
    гласные + гортанная смычка (в Inventory.md не перечислена явно)."""
    consonants = len(inventory.get("consonants", {}).get("simple", []))
    vowels = len(inventory.get("vowels", {}).get("short", []))
    return consonants + vowels + 1
