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
    fm, _ = parse_note((Path(root) / "README.md").read_text(encoding="utf-8"))
    return fm.get("version")


def build_lexicon(root):
    root = Path(root)
    lexemes = []
    for path in sorted((root / "Language" / "Lexicon").glob("*.md")):
        fm, _ = parse_note(path.read_text(encoding="utf-8"))
        lexemes.append({key: _unwrap(fm.get(key)) for key in EXPORTED})
    return {"version": read_version(root), "lexemes": lexemes}


def build_phonology(root):
    root = Path(root)
    path = root / "Language" / "Phonology" / "Transliteration.md"
    rows = parse_table(path.read_text(encoding="utf-8"))
    header = [cell.lower() for cell in rows[0]]
    header[0] = "ipa"
    transliteration = [dict(zip(header, cells)) for cells in rows[1:]]
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
