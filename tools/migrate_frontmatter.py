"""Одноразовый перевод заметок в новую схему.

script: [латиница, кириллица] -> cyrillic: кириллица (латиница уже есть в lemma)
пустые "" и [] -> None
добавляется status
порядок ключей приводится к каноническому
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.notes import read_note, write_note

ROOT = Path(__file__).resolve().parent.parent

LEXEME_ORDER = [
    "type", "lemma", "cyrillic", "pos", "meaning", "verb_type",
    "noun_class", "root", "phon", "etym", "examples", "status", "tags",
]
AFFIX_ORDER = ["type", "cyrillic", "meaning", "etym", "examples", "tags"]


def blank(value):
    """Пустая строка, пустой список и '' — всё это отсутствие значения."""
    if value is None:
        return True
    if isinstance(value, list):
        return len(value) == 0
    return value.strip() == ""


def collapse_singleton(value):
    """Список из одного элемента — на деле скалярное значение (напр. root)."""
    if isinstance(value, list) and len(value) == 1:
        return value[0]
    return value


def normalize(fm, order):
    out = {}
    for key in order:
        value = fm.get(key)
        out[key] = None if blank(value) else collapse_singleton(value)
    return out


def script_to_cyrillic(fm):
    """script: [латиница, кириллица] -> cyrillic. Латиница уже есть в lemma.

    Заметка может быть уже мигрирована (поля script больше нет, cyrillic
    уже выставлен) — в этом случае существующее значение cyrillic нельзя
    затирать None, иначе повторный запуск скрипта уничтожает данные.
    """
    script = fm.pop("script", None)
    if isinstance(script, list) and len(script) >= 2:
        fm["cyrillic"] = script[1]
    elif "cyrillic" not in fm:
        fm["cyrillic"] = None


def migrate_lexeme(path):
    fm, body = read_note(path)
    script_to_cyrillic(fm)

    # Имя файла — канон: переименования уже сделаны на предыдущем шаге.
    fm["lemma"] = path.stem
    # По умолчанию — "ok", но существующий статус (напр. "unverified",
    # выставленный вручную) нельзя затирать при повторном запуске.
    if blank(fm.get("status")):
        fm["status"] = "ok"

    fm = normalize(fm, LEXEME_ORDER)
    fm["type"] = "lexeme"
    fm["tags"] = ["lexeme"]
    write_note(path, fm, body)


def migrate_affix(path):
    fm, body = read_note(path)
    script_to_cyrillic(fm)
    fm = normalize(fm, AFFIX_ORDER)
    fm["type"] = "affix"
    fm["tags"] = ["affix"]
    write_note(path, fm, body)


def main():
    lexemes = sorted((ROOT / "Language" / "Lexicon").glob("*.md"))
    for path in lexemes:
        migrate_lexeme(path)
    affixes = [
        path
        for path in sorted((ROOT / "Language" / "Affixes").glob("*.md"))
        if path.stem != "template"
    ]
    for path in affixes:
        migrate_affix(path)
    print(f"lexemes: {len(lexemes)}, affixes: {len(affixes)}")


if __name__ == "__main__":
    main()
