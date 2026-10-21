import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.build import BuildError, EXPORTED, build_lexicon, build_phonology, read_version, run

LEXEME = """---
type: lexeme
lemma: gaśi
cyrillic: гащи
pos: nouns
meaning: place
verb_type:
noun_class: "[[Class 7]]"
root: "[[-gaśi-]]"
phon:
etym:
examples:
status: ok
tags: [lexeme]
---
"""

# A fully-populated lexeme fixture: every one of the ten exported fields
# carries a distinct, non-empty value so a test can pin down each of them
# individually.
FULL_LEXEME = """---
type: lexeme
lemma: qeșe
cyrillic: кэщэ
pos: verbs
meaning: to coil
verb_type: "[[Type II]]"
noun_class: "[[Class 3]]"
root: "[[-qeșe-]]"
phon: qeɕe
etym: proto-ophidian *qesse
status: unverified
tags: [lexeme]
---

Body text is not part of the export.
"""

# A compound lexeme whose root is a list of two links, the way real
# compounds (e.g. seșegaśixxi) are recorded.
COMPOUND_LEXEME = """---
type: lexeme
lemma: seșegaśixxi
cyrillic: сэшэгащиххи
pos: verbs
meaning: to have eaten and crawl in a safe place to digest
verb_type: "[[Type II]]"
noun_class:
root: ["[[-seșe-]]", "[[-gaśi-]]"]
phon:
etym:
status: ok
tags: [lexeme]
---
"""

# A stray note that lives under Lexicon/ but is not a lexeme (an index,
# a README-style note, etc).
STRAY_NOTE = """---
title: Lexicon index
tags: [index]
---

This note is not a lexeme and must not be exported as one.
"""

README = """---
version: 0.4
---

# ophidian
"""

README_NO_VERSION = """---
title: ophidian
---

# ophidian has no version field
"""

# The real transliteration table has a fixed contract: 18 data rows, 6
# columns, header "IPA | latin-1 | latin-2 | latin-3 | cyr-1 | cyr-2".
PHONEMES = [
    ["θ", "t", "th", "t", "т", "ф"],
    ["s", "s", "s", "s", "с", "с"],
    ["sʲ", "c", "c", "c", "сь", "сј"],
    ["ʃ", "ș", "sh", "w", "ш", "ш"],
    ["ʂ", "š", "rz", "r", "ж", "ж"],
    ["ɕ", "ś", "ch", "z", "щ", "шј"],
    ["ç", "j", "j", "j", "хь", "ј"],
    ["x", "x", "x", "x", "х", "х"],
    ["χ", "g", "g", "g", "г", "г"],
    ["ħ", "q", "q", "q", "к", "к"],
    ["h", "h", "h", "h", "ь", "кј"],
    ["ɬ", "l", "l", "l", "л", "л"],
    ["𝼆", "ļ", "lh", "y", "ль", "лј"],
    ["i", "i", "i", "i", "и", "и"],
    ["e", "e", "e", "e", "э", "е"],
    ["a", "a", "a", "a", "а", "а"],
    ["u", "u", "u", "u", "у", "у"],
    ["ʔ", "’", "’", "’", "ъ", "’"],
]

TABLE_HEADER_ROW = ["IPA", "latin-1", "latin-2", "latin-3", "cyr-1", "cyr-2"]


def _table_text(header, rows):
    lines = ["# Transliteration", ""]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join("---" for _ in header) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


TABLE = _table_text(TABLE_HEADER_ROW, PHONEMES)

# Mirrors the real Language/Phonology/Inventory.md closely enough that
# expected_phoneme_count() derives 18, matching PHONEMES above: 13 "simple"
# consonants + 4 "short" vowels + the glottal stop.
INVENTORY = """# Phoneme Inventory

## Consonants
**simple**: θ, s, sʲ, ʃ, ʂ, ɕ, ç, x, χ, ħ, h, ɬ, 𝼆
**geminated**: θː, sː, sʲː, ʃː, ʂː, ɕː, çː, xː, χː, ħː, hː, ɬː, 𝼆ː

## Vowels
**short**: i, e, a, u
**long**: iː, eː, aː, uː
**double**: iʔi, eʔe, aʔa, uʔu

## Категории

**Согласные**
- soft: θ, sʲ, ɕ, ç, h, 𝼆
- hard: s, ʃ, ʂ, x, χ, ħ, ɬ

**Гласные**
- front: i, e, a
- back: u
"""


def build_vault(directory, lexeme_files=None, readme=README, table=TABLE, inventory=INVENTORY):
    root = Path(directory)
    (root / "Language" / "Lexicon").mkdir(parents=True)
    (root / "Language" / "Phonology").mkdir(parents=True)
    if lexeme_files is None:
        lexeme_files = {"gaśi.md": LEXEME}
    for name, content in lexeme_files.items():
        (root / "Language" / "Lexicon" / name).write_text(content, encoding="utf-8")
    (root / "Language" / "Phonology" / "Transliteration.md").write_text(table, encoding="utf-8")
    (root / "Language" / "Phonology" / "Inventory.md").write_text(inventory, encoding="utf-8")
    (root / "README.md").write_text(readme, encoding="utf-8")
    return root


class BuildLexicon(unittest.TestCase):
    def test_version_read_from_readme(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(read_version(build_vault(directory)), "0.4")

    def test_version_missing_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, readme=README_NO_VERSION)
            with self.assertRaises(BuildError):
                read_version(root)

    def test_lexeme_is_flat_and_links_are_unwrapped(self):
        with tempfile.TemporaryDirectory() as directory:
            data = build_lexicon(build_vault(directory))
            self.assertEqual(data["version"], "0.4")
            self.assertEqual(len(data["lexemes"]), 1)
            entry = data["lexemes"][0]
            self.assertEqual(entry["lemma"], "gaśi")
            self.assertEqual(entry["cyrillic"], "гащи")
            self.assertEqual(entry["noun_class"], "Class 7")
            self.assertEqual(entry["root"], "-gaśi-")
            self.assertIsNone(entry["etym"])

    def test_type_and_tags_are_not_exported(self):
        with tempfile.TemporaryDirectory() as directory:
            entry = build_lexicon(build_vault(directory))["lexemes"][0]
            self.assertNotIn("type", entry)
            self.assertNotIn("tags", entry)
            self.assertNotIn("examples", entry)

    def test_exported_keys_are_exactly_ten_in_order(self):
        with tempfile.TemporaryDirectory() as directory:
            entry = build_lexicon(
                build_vault(directory, lexeme_files={"qeșe.md": FULL_LEXEME})
            )["lexemes"][0]
            self.assertEqual(
                list(entry.keys()),
                ["lemma", "cyrillic", "pos", "meaning", "verb_type",
                 "noun_class", "root", "phon", "etym", "status"],
            )

    def test_every_exported_field_carries_its_value(self):
        with tempfile.TemporaryDirectory() as directory:
            entry = build_lexicon(
                build_vault(directory, lexeme_files={"qeșe.md": FULL_LEXEME})
            )["lexemes"][0]
            self.assertEqual(entry["lemma"], "qeșe")
            self.assertEqual(entry["cyrillic"], "кэщэ")
            self.assertEqual(entry["pos"], "verbs")
            self.assertEqual(entry["meaning"], "to coil")
            self.assertEqual(entry["verb_type"], "Type II")
            self.assertEqual(entry["noun_class"], "Class 3")
            self.assertEqual(entry["root"], "-qeșe-")
            self.assertEqual(entry["phon"], "qeɕe")
            self.assertEqual(entry["etym"], "proto-ophidian *qesse")
            self.assertEqual(entry["status"], "unverified")

    def test_compound_root_exports_as_plain_list_of_unwrapped_names(self):
        with tempfile.TemporaryDirectory() as directory:
            entry = build_lexicon(
                build_vault(directory, lexeme_files={"seșegaśixxi.md": COMPOUND_LEXEME})
            )["lexemes"][0]
            self.assertEqual(entry["root"], ["-seșe-", "-gaśi-"])
            self.assertIsInstance(entry["root"], list)
            self.assertEqual(len(entry["root"]), 2)
            for name in entry["root"]:
                self.assertNotIn("[", name)
                self.assertNotIn("]", name)

    def test_stray_note_without_lexeme_type_is_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            data = build_lexicon(
                build_vault(
                    directory,
                    lexeme_files={"gaśi.md": LEXEME, "_index.md": STRAY_NOTE},
                )
            )
            lemmas = [entry["lemma"] for entry in data["lexemes"]]
            self.assertEqual(lemmas, ["gaśi"])


class BuildPhonology(unittest.TestCase):
    def test_table_rows_keep_alignment(self):
        with tempfile.TemporaryDirectory() as directory:
            data = build_phonology(build_vault(directory))
            rows = data["transliteration"]
            self.assertEqual(len(rows), 18)
            self.assertEqual(
                rows[3],
                {"ipa": "ʃ", "latin-1": "ș", "latin-2": "sh", "latin-3": "w",
                 "cyr-1": "ш", "cyr-2": "ш"},
            )

    def test_short_row_raises(self):
        broken_rows = [list(row) for row in PHONEMES]
        broken_rows[5] = broken_rows[5][:-1]  # drop the last cell of row 7
        table = _table_text(TABLE_HEADER_ROW, broken_rows)
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, table=table)
            with self.assertRaises(BuildError):
                build_phonology(root)

    def test_wrong_header_raises(self):
        bad_header = ["IPA", "latin-1", "latin-2", "latin-3", "cyr-1", "cyr-3"]
        table = _table_text(bad_header, PHONEMES)
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, table=table)
            with self.assertRaises(BuildError):
                build_phonology(root)

    def test_wrong_row_count_raises(self):
        table = _table_text(TABLE_HEADER_ROW, PHONEMES[:-1])
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, table=table)
            with self.assertRaises(BuildError):
                build_phonology(root)

    def test_empty_cell_raises(self):
        broken_rows = [list(row) for row in PHONEMES]
        broken_rows[2][3] = ""
        table = _table_text(TABLE_HEADER_ROW, broken_rows)
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, table=table)
            with self.assertRaises(BuildError):
                build_phonology(root)

    def test_phonology_includes_inventory_and_categories_from_inventory_md(self):
        with tempfile.TemporaryDirectory() as directory:
            data = build_phonology(build_vault(directory))
            self.assertEqual(data["inventory"]["consonants"]["simple"][0], "θ")
            self.assertEqual(len(data["inventory"]["consonants"]["simple"]), 13)
            self.assertEqual(data["inventory"]["vowels"]["short"], ["i", "e", "a", "u"])
            self.assertIn("iʔi", data["inventory"]["vowels"]["double"])
            self.assertEqual(data["categories"]["consonants"]["soft"][0], "θ")
            self.assertEqual(data["categories"]["vowels"]["front"], ["i", "e", "a"])

    def test_phoneme_count_follows_inventory_not_a_hardcoded_constant(self):
        # A 19th phoneme, added purely by editing notes (a table row and a
        # matching Inventory.md entry), must be accepted without touching
        # any Python file.
        extra_row = PHONEMES + [["k", "k", "k", "k", "к", "к"]]
        table = _table_text(TABLE_HEADER_ROW, extra_row)
        extra_inventory = INVENTORY.replace(
            "**simple**: θ, s, sʲ, ʃ, ʂ, ɕ, ç, x, χ, ħ, h, ɬ, 𝼆",
            "**simple**: θ, s, sʲ, ʃ, ʂ, ɕ, ç, x, χ, ħ, h, ɬ, 𝼆, k",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, table=table, inventory=extra_inventory)
            data = build_phonology(root)
            self.assertEqual(len(data["transliteration"]), 19)

        # Same 19-row table but Inventory.md unchanged: now a mismatch.
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, table=table)
            with self.assertRaises(BuildError):
                build_phonology(root)


class BuildRun(unittest.TestCase):
    def test_broken_table_is_reported_without_a_traceback(self):
        # main() must not let BuildError escape as a stack trace — the
        # author isn't a programmer. run() is main()'s testable core: it
        # takes root/out explicitly instead of reading the module-level
        # ROOT constant.
        broken_table = _table_text(TABLE_HEADER_ROW, PHONEMES[:-1])
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, table=broken_table)
            out = Path(directory) / "build"
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = run(root, out)
            self.assertEqual(code, 1)
            self.assertNotIn("Traceback", buffer.getvalue())
            self.assertFalse((out / "phonology.json").exists())

    def test_clean_vault_builds_and_returns_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory)
            out = Path(directory) / "build"
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = run(root, out)
            self.assertEqual(code, 0)
            self.assertTrue((out / "lexicon.json").exists())
            self.assertTrue((out / "phonology.json").exists())


if __name__ == "__main__":
    unittest.main()
