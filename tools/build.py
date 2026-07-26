"""Сборка машинных представлений языка из заметок.

Заметки — источник правды. Всё, что здесь пишется, — производное,
руками не правится.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.notes import (
    TABLE_COLUMNS,
    TABLE_HEADER,
    expected_phoneme_count,
    parse_inventory,
    parse_note,
    parse_table,
    table_contract_issues,
)

ROOT = Path(__file__).resolve().parent.parent

LINK = re.compile(r"^\[\[([^\]]+)\]\]$")

EXPORTED = ["lemma", "cyrillic", "pos", "meaning", "verb_type", "noun_class", "root", "phon", "etym", "status"]


class BuildError(Exception):
    """Заметка не даёт собрать корректный вывод."""


def _unwrap(value):
    """[[Class 7]] -> Class 7. Список ссылок -> список развёрнутых имён. Остальное как есть."""
    if isinstance(value, str):
        match = LINK.match(value.strip())
        if match:
            return match.group(1)
        return value
    if isinstance(value, list):
        return [_unwrap(item) for item in value]
    return value


def read_version(root):
    path = Path(root) / "README.md"
    fm, _ = parse_note(path.read_text(encoding="utf-8"))
    version = fm.get("version")
    if version is None:
        raise BuildError(
            f"{path}: нет version во frontmatter (там и только там должна жить версия языка)"
        )
    return version


def build_lexicon(root):
    root = Path(root)
    lexemes = []
    for path in sorted((root / "Language" / "Lexicon").glob("*.md")):
        fm, _ = parse_note(path.read_text(encoding="utf-8"))
        if fm.get("type") != "lexeme":
            continue
        lexemes.append({key: _unwrap(fm.get(key)) for key in EXPORTED})
    return {"version": read_version(root), "lexemes": lexemes}


def _read_inventory(root):
    path = Path(root) / "Language" / "Phonology" / "Inventory.md"
    if not path.is_file():
        raise BuildError(f"{path}: файл отсутствует")
    return parse_inventory(path.read_text(encoding="utf-8"))


def build_phonology(root):
    root = Path(root)
    inventory = _read_inventory(root)
    expected_rows = expected_phoneme_count(inventory)

    path = root / "Language" / "Phonology" / "Transliteration.md"
    rows = parse_table(path.read_text(encoding="utf-8"))

    issues = table_contract_issues(rows, expected_rows)
    if issues:
        issue = issues[0]
        kind = issue["kind"]
        if kind == "missing":
            raise BuildError(f"{path}: таблица не найдена")
        if kind == "header_columns":
            raise BuildError(
                f"{path}: заголовок таблицы: ожидалось {TABLE_COLUMNS} колонок, "
                f"получено {issue['got']}: {issue['raw']!r}"
            )
        if kind == "header_mismatch":
            raise BuildError(
                f"{path}: заголовок таблицы не соответствует контракту: "
                f"ожидалось {TABLE_HEADER}, получено {issue['got']}"
            )
        if kind == "row_count":
            raise BuildError(
                f"{path}: ожидалось {issue['expected']} строк данных (плюс заголовок), "
                f"получено {issue['got']}"
            )
        if kind == "row_columns":
            cells = issue["cells"]
            raise BuildError(
                f"{path}: строка {issue['row']}: ожидалось {TABLE_COLUMNS} колонок, "
                f"получено {len(cells)}: {cells!r}"
            )
        if kind == "row_empty":
            cells = issue["cells"]
            raise BuildError(f"{path}: строка {issue['row']}: пустая ячейка: {cells!r}")

    transliteration = [dict(zip(TABLE_HEADER, cells)) for cells in rows[1:]]

    return {
        "version": read_version(root),
        "transliteration": transliteration,
        "inventory": {
            "consonants": inventory["consonants"],
            "vowels": inventory["vowels"],
        },
        "categories": inventory["categories"],
    }


def run(root, out):
    """Собрать оба JSON-файла. Ловит BuildError и печатает его текстом,
    без traceback — автор волта не программист и не должен видеть стек
    вызовов на сломанной таблице. -> код возврата (0/1)."""
    try:
        lexicon = build_lexicon(root)
        phonology = build_phonology(root)
    except BuildError as error:
        print(f"ошибка сборки: {error}")
        return 1

    out = Path(out)
    out.mkdir(exist_ok=True)
    (out / "lexicon.json").write_text(
        json.dumps(lexicon, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out / "phonology.json").write_text(
        json.dumps(phonology, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"build/lexicon.json: {len(lexicon['lexemes'])} лексем\n"
        f"build/phonology.json: {len(phonology['transliteration'])} фонем"
    )
    return 0


def main():
    return run(ROOT, ROOT / "build")


if __name__ == "__main__":
    sys.exit(main())
