"""Сборка машинных представлений языка из заметок.

Заметки — источник правды. Всё, что здесь пишется, — производное,
руками не правится.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.notes import parse_note, parse_table

ROOT = Path(__file__).resolve().parent.parent

LINK = re.compile(r"^\[\[([^\]]+)\]\]$")

EXPORTED = ["lemma", "cyrillic", "pos", "meaning", "verb_type", "noun_class", "root", "phon", "etym", "status"]

TABLE_HEADER = ["ipa", "latin-1", "latin-2", "latin-3", "cyr-1", "cyr-2"]
TABLE_COLUMNS = len(TABLE_HEADER)
TABLE_ROWS = 18


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


def build_phonology(root):
    root = Path(root)
    path = root / "Language" / "Phonology" / "Transliteration.md"
    rows = parse_table(path.read_text(encoding="utf-8"))

    if len(rows) != TABLE_ROWS + 1:
        raise BuildError(
            f"{path}: ожидалось {TABLE_ROWS} строк данных (плюс заголовок), "
            f"получено {len(rows) - 1}"
        )

    header = [cell.lower() for cell in rows[0]]
    if len(header) != TABLE_COLUMNS:
        raise BuildError(
            f"{path}: заголовок таблицы: ожидалось {TABLE_COLUMNS} колонок, "
            f"получено {len(header)}: {rows[0]!r}"
        )
    if header != TABLE_HEADER:
        raise BuildError(
            f"{path}: заголовок таблицы не соответствует контракту: "
            f"ожидалось {TABLE_HEADER}, получено {header}"
        )

    transliteration = []
    for row_number, cells in enumerate(rows[1:], start=2):
        if len(cells) != TABLE_COLUMNS:
            raise BuildError(
                f"{path}: строка {row_number}: ожидалось {TABLE_COLUMNS} колонок, "
                f"получено {len(cells)}: {cells!r}"
            )
        if any(not cell for cell in cells):
            raise BuildError(f"{path}: строка {row_number}: пустая ячейка: {cells!r}")
        transliteration.append(dict(zip(TABLE_HEADER, cells)))

    return {"version": read_version(root), "transliteration": transliteration}


def main():
    out = ROOT / "build"
    out.mkdir(exist_ok=True)
    lexicon = build_lexicon(ROOT)
    phonology = build_phonology(ROOT)
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


if __name__ == "__main__":
    sys.exit(main())
