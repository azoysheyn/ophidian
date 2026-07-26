import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.check import check_vault

GOOD_LEXEME = """---
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

GOOD_ROOT = """---
type: root
meaning: movement
tags: [root]
---
"""

GOOD_CLASS = """---
type: noun_class
class: 7
prefix:
semantics: inanimate
tags: [noun_class]
---
"""

TABLE = """# Transliteration

| IPA | latin-1 | latin-2 | latin-3 | cyr-1 | cyr-2 |
| --- | --- | --- | --- | --- | --- |
"""


def build_vault(directory, lexemes=None, table_rows=18):
    root = Path(directory)
    (root / "Language" / "Lexicon").mkdir(parents=True)
    (root / "Language" / "Roots").mkdir(parents=True)
    (root / "Language" / "Noun Classes").mkdir(parents=True)
    (root / "Language" / "Phonology").mkdir(parents=True)

    for name, text in (lexemes or {"gaśi": GOOD_LEXEME}).items():
        (root / "Language" / "Lexicon" / f"{name}.md").write_text(text, encoding="utf-8")
    (root / "Language" / "Roots" / "-gaśi-.md").write_text(GOOD_ROOT, encoding="utf-8")
    (root / "Language" / "Noun Classes" / "Class 7.md").write_text(GOOD_CLASS, encoding="utf-8")

    table = TABLE + "".join(f"| p{i} | a | b | c | d | e |\n" for i in range(table_rows))
    (root / "Language" / "Phonology" / "Transliteration.md").write_text(table, encoding="utf-8")
    return root


class CheckVault(unittest.TestCase):
    def test_clean_vault_has_no_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            errors, _ = check_vault(build_vault(directory))
            self.assertEqual(errors, [])

    def test_filename_must_match_lemma(self):
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {"wrong": GOOD_LEXEME})
            errors, _ = check_vault(root)
            self.assertTrue(any("lemma" in error for error in errors))

    def test_broken_link_is_an_error(self):
        broken = GOOD_LEXEME.replace("[[Class 7]]", "[[Class 99]]")
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {"gaśi": broken})
            errors, _ = check_vault(root)
            self.assertTrue(any("Class 99" in error for error in errors))

    def test_cedilla_is_an_error(self):
        cedilla = GOOD_LEXEME.replace("meaning: place", "meaning: şagassa")
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {"gaśi": cedilla})
            errors, _ = check_vault(root)
            self.assertTrue(any("U+015F" in error for error in errors))

    def test_empty_string_value_is_an_error(self):
        quoted = GOOD_LEXEME.replace("etym:", 'etym: ""')
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {"gaśi": quoted})
            errors, _ = check_vault(root)
            self.assertTrue(any("etym" in error for error in errors))

    def test_duplicate_lemma_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {"gaśi": GOOD_LEXEME})
            (root / "Language" / "Lexicon" / "gaśi copy.md").write_text(
                GOOD_LEXEME, encoding="utf-8"
            )
            errors, _ = check_vault(root)
            self.assertTrue(any("дубль" in error for error in errors))

    def test_wrong_table_row_count_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, table_rows=17)
            errors, _ = check_vault(root)
            self.assertTrue(any("18" in error for error in errors))

    def test_noun_without_class_is_a_warning_not_error(self):
        classless = GOOD_LEXEME.replace('noun_class: "[[Class 7]]"', "noun_class:")
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {"gaśi": classless})
            errors, warnings = check_vault(root)
            self.assertEqual(errors, [])
            self.assertTrue(any("noun_class" in warning for warning in warnings))

    def test_unreferenced_root_is_a_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory)
            (root / "Language" / "Roots" / "-orphan-.md").write_text(GOOD_ROOT, encoding="utf-8")
            errors, warnings = check_vault(root)
            self.assertEqual(errors, [])
            self.assertTrue(any("-orphan-" in warning for warning in warnings))

    def test_nfd_filename_with_nfc_lemma_is_clean(self):
        # macOS filesystems hand back NFD names; the frontmatter lemma is
        # typically typed in as NFC. They must compare equal.
        nfd_name = unicodedata.normalize("NFD", "gaśi")
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {nfd_name: GOOD_LEXEME})
            errors, _ = check_vault(root)
            self.assertEqual(errors, [])

    def test_nfc_filename_with_nfd_lemma_is_clean(self):
        nfd_lemma = unicodedata.normalize("NFD", "gaśi")
        lexeme = GOOD_LEXEME.replace("lemma: gaśi", f"lemma: {nfd_lemma}")
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {"gaśi": lexeme})
            errors, _ = check_vault(root)
            self.assertEqual(errors, [])

    def test_root_pointing_at_lexeme_is_an_error(self):
        # A root field pointing at the lexeme's own (undashed) name — the
        # exact heeje.md bug: the link resolves, but to the wrong kind.
        bad = GOOD_LEXEME.replace('root: "[[-gaśi-]]"', 'root: "[[gaśi]]"')
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {"gaśi": bad})
            errors, _ = check_vault(root)
            self.assertTrue(
                any("root" in error and "Lexicon" in error for error in errors)
            )

    def test_noun_class_pointing_at_root_is_an_error(self):
        bad = GOOD_LEXEME.replace('noun_class: "[[Class 7]]"', 'noun_class: "[[-gaśi-]]"')
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {"gaśi": bad})
            errors, _ = check_vault(root)
            self.assertTrue(
                any("noun_class" in error and "Roots" in error for error in errors)
            )

    def test_two_root_compound_is_clean(self):
        compound = GOOD_LEXEME.replace(
            'root: "[[-gaśi-]]"', 'root: ["[[-gaśi-]]", "[[-lasa-]]"]'
        )
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {"gaśi": compound})
            (root / "Language" / "Roots" / "-lasa-.md").write_text(GOOD_ROOT, encoding="utf-8")
            errors, _ = check_vault(root)
            self.assertEqual(errors, [])

    def test_field_not_in_schema_is_an_error(self):
        extra = GOOD_LEXEME.replace("tags: [lexeme]", "tags: [lexeme]\nbogus_field: 1")
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {"gaśi": extra})
            errors, _ = check_vault(root)
            self.assertTrue(
                any("bogus_field" in error and "не из схемы" in error for error in errors)
            )

    def test_schema_field_missing_from_note_is_an_error(self):
        missing = GOOD_LEXEME.replace("phon:\n", "")
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {"gaśi": missing})
            errors, _ = check_vault(root)
            self.assertTrue(
                any("phon" in error and "отсутствует" in error for error in errors)
            )

    def test_illegal_filename_char_is_an_error(self):
        lexeme = GOOD_LEXEME.replace("lemma: gaśi", "lemma: gaśi?")
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {"gaśi?": lexeme})
            errors, _ = check_vault(root)
            self.assertTrue(
                any("запрещённые символы" in error and "?" in error for error in errors)
            )

    def test_transliteration_wrong_column_count_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory)
            rows = "".join(
                "| p0 | a | b | c | d |\n" if i == 0 else f"| p{i} | a | b | c | d | e |\n"
                for i in range(18)
            )
            (root / "Language" / "Phonology" / "Transliteration.md").write_text(
                TABLE + rows, encoding="utf-8"
            )
            errors, _ = check_vault(root)
            self.assertTrue(
                any("колонок" in error and "p0" in error for error in errors)
            )

    def test_transliteration_empty_cell_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory)
            rows = "".join(
                "| p0 | | b | c | d | e |\n" if i == 0 else f"| p{i} | a | b | c | d | e |\n"
                for i in range(18)
            )
            (root / "Language" / "Phonology" / "Transliteration.md").write_text(
                TABLE + rows, encoding="utf-8"
            )
            errors, _ = check_vault(root)
            self.assertTrue(
                any("пустая клетка" in error and "p0" in error for error in errors)
            )

    def test_verb_without_verb_type_is_a_warning(self):
        verb = GOOD_LEXEME.replace("pos: nouns", "pos: verbs")
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {"gaśi": verb})
            errors, warnings = check_vault(root)
            self.assertEqual(errors, [])
            self.assertTrue(any("verb_type" in warning for warning in warnings))

    def test_lexeme_without_root_is_a_warning(self):
        rootless = GOOD_LEXEME.replace('root: "[[-gaśi-]]"', "root:")
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {"gaśi": rootless})
            errors, warnings = check_vault(root)
            self.assertEqual(errors, [])
            self.assertTrue(any("нет root" in warning for warning in warnings))

    def test_status_unverified_is_a_warning(self):
        unverified = GOOD_LEXEME.replace("status: ok", "status: unverified")
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {"gaśi": unverified})
            errors, warnings = check_vault(root)
            self.assertEqual(errors, [])
            self.assertTrue(any("unverified" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
