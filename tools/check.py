"""Валидатор волта.

Ошибки — структурная поломка, ронять сборку. Предупреждения — неполнота
языка, это нормальное рабочее состояние.
"""

import re
import sys
import unicodedata
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

CEDILLA = "ş"  # ş — запрещён, правильный символ ș U+0219
ILLEGAL_NAME_CHARS = set('?*:/\\|"<>')
LINK = re.compile(r"\[\[([^\]]+)\]\]")

# Заметки, среди которых ищем символ ş — это источник правды и рабочие
# материалы, а не служебные Meta/ и не сгенерированный build/.
CEDILLA_SCAN_DIRS = ["Language", "Corpus", "Lore", "Drafts"]

# Папки, в которых ищем цель ссылки [[...]] — весь волт, кроме служебного
# build/ (сгенерирован, не источник правды).
LINKABLE_DIRS = ["Language", "Corpus", "Lore", "Drafts", "Meta"]

SCHEMA = {
    "lexeme": [
        "type", "lemma", "cyrillic", "pos", "meaning", "verb_type",
        "noun_class", "root", "phon", "etym", "examples", "status", "tags",
    ],
    "root": ["type", "meaning", "tags"],
    "affix": ["type", "cyrillic", "meaning", "etym", "examples", "tags"],
    "noun_class": ["type", "class", "prefix", "semantics", "tags"],
    "verb_class": ["type", "affix", "semantics", "tags"],
}

TYPED_DIRS = {
    "Lexicon": "lexeme",
    "Roots": "root",
    "Affixes": "affix",
    "Noun Classes": "noun_class",
    "Verb Classes": "verb_class",
}

# Типизированные поля-ссылки лексем: поле -> папка, в которой обязана
# лежать целевая заметка.
TYPED_LINK_FIELDS = {
    "root": "Roots",
    "noun_class": "Noun Classes",
}


def _nfc(text):
    """Юникод-нормализация к NFC. Волт хранится преимущественно в NFD
    (так отдаёт файловую систему macOS), но сравнивать текст нужно
    независимо от формы нормализации."""
    if not isinstance(text, str):
        return text
    return unicodedata.normalize("NFC", text)


def _typed_notes(root):
    """-> список (path, expected_type, frontmatter)."""
    found = []
    for folder, expected in TYPED_DIRS.items():
        directory = root / "Language" / folder
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            fm, _ = parse_note(path.read_text(encoding="utf-8"))
            found.append((path, expected, fm))
    return found


def _linkable_notes(root):
    for dirname in LINKABLE_DIRS:
        directory = root / dirname
        if not directory.is_dir():
            continue
        yield from directory.rglob("*.md")


def _note_names(root):
    return {_nfc(path.stem) for path in _linkable_notes(root)}


def _note_locations(root):
    """-> dict NFC(имя заметки) -> список папок (относительно root), где
    заметка с таким именем существует. Используется для проверки, что
    типизированная ссылка (root, noun_class) ведёт в правильную папку."""
    locations = {}
    for path in _linkable_notes(root):
        locations.setdefault(_nfc(path.stem), []).append(path.parent.relative_to(root))
    return locations


def _check_cedilla(root, errors):
    for dirname in CEDILLA_SCAN_DIRS:
        directory = root / dirname
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            if CEDILLA in text:
                errors.append(f"{path.relative_to(root)}: символ ş U+015F, ожидается ș U+0219")


def _check_transliteration(root, errors):
    inventory_path = root / "Language" / "Phonology" / "Inventory.md"
    if not inventory_path.is_file():
        errors.append("Inventory.md отсутствует")
        return
    inventory = parse_inventory(inventory_path.read_text(encoding="utf-8"))
    expected_rows = expected_phoneme_count(inventory)

    path = root / "Language" / "Phonology" / "Transliteration.md"
    if not path.is_file():
        errors.append("Transliteration.md отсутствует")
        return
    rows = parse_table(path.read_text(encoding="utf-8"))

    for issue in table_contract_issues(rows, expected_rows):
        kind = issue["kind"]
        if kind == "missing":
            errors.append("Transliteration.md: таблица не найдена")
        elif kind == "header_columns":
            errors.append(
                f"Transliteration.md: заголовок таблицы: ожидалось {TABLE_COLUMNS} колонок, "
                f"получено {issue['got']}: {issue['raw']!r}"
            )
        elif kind == "header_mismatch":
            errors.append(
                "Transliteration.md: заголовок таблицы не соответствует контракту: "
                f"ожидалось {TABLE_HEADER}, получено {issue['got']}"
            )
        elif kind == "row_count":
            errors.append(
                f"Transliteration.md: строк данных {issue['got']}, ожидается {issue['expected']} "
                "(по Inventory.md: согласные + краткие гласные + гортанная смычка)"
            )
        elif kind == "row_columns":
            cells = issue["cells"]
            label = cells[0] if cells else issue["row"]
            errors.append(
                f"Transliteration.md: в строке {label!r} колонок {len(cells)}, "
                f"ожидается {TABLE_COLUMNS}"
            )
        elif kind == "row_empty":
            cells = issue["cells"]
            errors.append(f"Transliteration.md: пустая клетка в строке {cells[0]!r}")


def check_vault(root):
    root = Path(root)
    errors = []
    warnings = []

    names = _note_names(root)
    locations = _note_locations(root)
    notes = _typed_notes(root)
    seen_lemmas = {}
    referenced_roots = set()

    for path, expected, fm in notes:
        where = path.relative_to(root)

        illegal = ILLEGAL_NAME_CHARS & set(path.name)
        if illegal:
            errors.append(f"{where}: запрещённые символы в имени: {''.join(sorted(illegal))}")

        allowed = SCHEMA[expected]
        for key in fm:
            if key not in allowed:
                errors.append(f"{where}: поле {key!r} не из схемы {expected}")
        for key in allowed:
            if key not in fm:
                errors.append(f"{where}: отсутствует поле {key!r}")

        for key, value in fm.items():
            if value == "" or value == []:
                errors.append(f"{where}: поле {key!r} — пустая строка или пустой список, должно быть пустым")

        text = path.read_text(encoding="utf-8")
        for target in LINK.findall(text):
            if _nfc(target) not in names:
                errors.append(f"{where}: битая ссылка [[{target}]]")

        if expected == "lexeme":
            lemma = fm.get("lemma")
            if _nfc(lemma) != _nfc(path.stem):
                errors.append(f"{where}: lemma {lemma!r} не совпадает с именем файла {path.stem!r}")
            lemma_key = _nfc(lemma)
            if lemma_key in seen_lemmas:
                errors.append(f"{where}: дубль lemma {lemma!r}, уже есть в {seen_lemmas[lemma_key]}")
            else:
                seen_lemmas[lemma_key] = where

            for field, expected_dir in TYPED_LINK_FIELDS.items():
                value = fm.get(field)
                if not value:
                    continue
                items = value if isinstance(value, list) else [value]
                expected_rel = Path("Language") / expected_dir
                for item in items:
                    for target in LINK.findall(str(item)):
                        dirs = locations.get(_nfc(target))
                        if not dirs:
                            continue  # уже отмечено как битая ссылка выше
                        if expected_rel not in dirs:
                            actual = ", ".join(str(d) for d in dirs)
                            errors.append(
                                f"{where}: поле {field!r} ссылается на [[{target}]], "
                                f"ожидается заметка в {expected_rel}, "
                                f"а найдена в {actual}"
                            )

            if fm.get("root"):
                referenced_roots.update(_nfc(t) for t in LINK.findall(str(fm["root"])))
            else:
                warnings.append(f"{where}: нет root")
            if fm.get("pos") == "nouns" and not fm.get("noun_class"):
                warnings.append(f"{where}: pos=nouns, но нет noun_class")
            if fm.get("pos") == "verbs" and not fm.get("verb_type"):
                warnings.append(f"{where}: pos=verbs, но нет verb_type")
            if fm.get("status") == "unverified":
                warnings.append(f"{where}: status=unverified")

    for path, expected, _ in notes:
        if expected == "root" and _nfc(path.stem) not in referenced_roots:
            warnings.append(f"{path.relative_to(root)}: на корень не ссылается ни одна лексема")

    _check_cedilla(root, errors)
    _check_transliteration(root, errors)
    return errors, warnings


def main():
    errors, warnings = check_vault(ROOT)
    for warning in warnings:
        print(f"warn:  {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    print(f"\n{len(errors)} ошибок, {len(warnings)} предупреждений")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
