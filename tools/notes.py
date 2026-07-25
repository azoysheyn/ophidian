"""Чтение и запись frontmatter заметок Obsidian.

Намеренно поддерживает только то подмножество YAML, которое реально
встречается в этом волте: плоские пары ключ-значение, блочные списки
и инлайновые списки. Без зависимостей.
"""

import re
from pathlib import Path

DELIM = "---"
# Значение приходится закавычивать, если оно начинается с символа,
# который YAML прочтёт как структуру, либо содержит ссылку [[...]].
_NEEDS_QUOTES_PREFIX = "[{&*!|>%@`#"
_TABLE_ROW = re.compile(r"^\|(.+)\|\s*$")


def _unquote(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _split_inline(value):
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [_unquote(item.strip()) for item in inner.split(",")]


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


def _format_value(value):
    if value is None:
        return ""
    if isinstance(value, list):
        return "[" + ", ".join(value) + "]"
    text = str(value)
    if not text:
        return '""'
    if text[0] in _NEEDS_QUOTES_PREFIX or text != text.strip():
        return '"' + text + '"'
    return text


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
