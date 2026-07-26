import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.build import build_lexicon, build_phonology, read_version

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

README = """---
version: 0.4
---

# ophidian
"""

TABLE = """# Transliteration

| IPA | latin-1 | latin-2 | latin-3 | cyr-1 | cyr-2 |
| --- | --- | --- | --- | --- | --- |
| θ | t | th | t | т | ф |
| ʃ | ș | sh | w | ш | ш |
"""


def build_vault(directory):
    root = Path(directory)
    (root / "Language" / "Lexicon").mkdir(parents=True)
    (root / "Language" / "Phonology").mkdir(parents=True)
    (root / "Language" / "Lexicon" / "gaśi.md").write_text(LEXEME, encoding="utf-8")
    (root / "Language" / "Phonology" / "Transliteration.md").write_text(TABLE, encoding="utf-8")
    (root / "README.md").write_text(README, encoding="utf-8")
    return root


class BuildLexicon(unittest.TestCase):
    def test_version_read_from_readme(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(read_version(build_vault(directory)), "0.4")

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


class BuildPhonology(unittest.TestCase):
    def test_table_rows_keep_alignment(self):
        with tempfile.TemporaryDirectory() as directory:
            data = build_phonology(build_vault(directory))
            rows = data["transliteration"]
            self.assertEqual(len(rows), 2)
            self.assertEqual(
                rows[1],
                {"ipa": "ʃ", "latin-1": "ș", "latin-2": "sh", "latin-3": "w",
                 "cyr-1": "ш", "cyr-2": "ш"},
            )


if __name__ == "__main__":
    unittest.main()
