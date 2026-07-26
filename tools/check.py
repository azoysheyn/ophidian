"""Валидатор волта.

Ошибки — структурная поломка, ронять сборку. Предупреждения — неполнота
языка, это нормальное рабочее состояние.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.notes import parse_note, parse_table

ROOT = Path(__file__).resolve().parent.parent

CEDILLA = "ş"  # ş — запрещён, правильный символ ș U+0219
ILLEGAL_NAME_CHARS = set('?*:/\\|"<>')
LINK = re.compile(r"\[\[([^\]]+)\]\]")
PHONEME_COUNT = 18  # 13 согласных + 4 гласных + гортанная смычка
TABLE_COLUMNS = 6  # IPA + пять вариантов записи

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


def _typed_notes(root):
    """-> список (path, expected_type, frontmatter)."""
    found = []
    for folder, expected in TYPED_DIRS.items():
        directory = root / "Language" / folder
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            if path.stem == "template":
                continue
            fm, _ = parse_note(path.read_text(encoding="utf-8"))
            found.append((path, expected, fm))
    return found


def _note_names(root):
    return {path.stem for path in (root / "Language").rglob("*.md")}


def _check_transliteration(root, errors):
    path = root / "Language" / "Phonology" / "Transliteration.md"
    if not path.is_file():
        errors.append("Transliteration.md отсутствует")
        return
    rows = parse_table(path.read_text(encoding="utf-8"))
    if not rows:
        errors.append("Transliteration.md: таблица не найдена")
        return
    data = rows[1:]
    if len(data) != PHONEME_COUNT:
        errors.append(
            f"Transliteration.md: строк данных {len(data)}, ожидается {PHONEME_COUNT} "
            "(13 согласных + 4 гласных + гортанная смычка)"
        )
    for cells in data:
        if len(cells) != TABLE_COLUMNS:
            errors.append(
                f"Transliteration.md: в строке {cells[0]!r} колонок {len(cells)}, "
                f"ожидается {TABLE_COLUMNS}"
            )
        elif any(not cell for cell in cells):
            errors.append(f"Transliteration.md: пустая клетка в строке {cells[0]!r}")


def check_vault(root):
    root = Path(root)
    errors = []
    warnings = []

    names = _note_names(root)
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
        if CEDILLA in text:
            errors.append(f"{where}: символ ş U+015F, ожидается ș U+0219")
        for target in LINK.findall(text):
            if target not in names:
                errors.append(f"{where}: битая ссылка [[{target}]]")

        if expected == "lexeme":
            lemma = fm.get("lemma")
            if lemma != path.stem:
                errors.append(f"{where}: lemma {lemma!r} не совпадает с именем файла {path.stem!r}")
            if lemma in seen_lemmas:
                errors.append(f"{where}: дубль lemma {lemma!r}, уже есть в {seen_lemmas[lemma]}")
            else:
                seen_lemmas[lemma] = where

            if fm.get("root"):
                referenced_roots.update(LINK.findall(str(fm["root"])))
            else:
                warnings.append(f"{where}: нет root")
            if fm.get("pos") == "nouns" and not fm.get("noun_class"):
                warnings.append(f"{where}: pos=nouns, но нет noun_class")
            if fm.get("pos") == "verbs" and not fm.get("verb_type"):
                warnings.append(f"{where}: pos=verbs, но нет verb_type")
            if fm.get("status") == "unverified":
                warnings.append(f"{where}: status=unverified")

    for path, expected, _ in notes:
        if expected == "root" and path.stem not in referenced_roots:
            warnings.append(f"{path.relative_to(root)}: на корень не ссылается ни одна лексема")

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
