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

# Matches the real Language/Phonology/Inventory.md shape closely enough
# that expected_phoneme_count() derives 18: 13 "simple" consonants + 4
# "short" vowels + the glottal stop.
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


def build_vault(directory, lexemes=None, table_rows=18, inventory=INVENTORY):
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
    (root / "Language" / "Phonology" / "Inventory.md").write_text(inventory, encoding="utf-8")
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

    def test_bare_verb_type_is_an_error(self):
        verb = GOOD_LEXEME.replace("pos: nouns", "pos: verbs").replace(
            "verb_type:", "verb_type: 1"
        )
        with tempfile.TemporaryDirectory() as directory:
            errors, _ = check_vault(build_vault(directory, {"gaśi": verb}))
            self.assertTrue(
                any("verb_type" in error and "не ссылка" in error for error in errors)
            )

    def test_verb_type_pointing_at_noun_class_is_an_error(self):
        verb = GOOD_LEXEME.replace("pos: nouns", "pos: verbs").replace(
            "verb_type:", 'verb_type: "[[Class 7]]"'
        )
        with tempfile.TemporaryDirectory() as directory:
            errors, _ = check_vault(build_vault(directory, {"gaśi": verb}))
            self.assertTrue(
                any("verb_type" in error and "Verb Classes" in error for error in errors)
            )

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

    def test_cedilla_outside_typed_dirs_is_an_error(self):
        # Corpus/, Lore/, Drafts/ and Language/Grammar/, Language/Phonology/
        # are not among the five typed directories but are still source of
        # truth (or, for Drafts/, still worth catching). The scan must not
        # be limited to the typed dirs.
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory)
            (root / "Corpus").mkdir(parents=True)
            (root / "Corpus" / "Story.md").write_text("secişi old taagataxxa.\n", encoding="utf-8")
            errors, _ = check_vault(root)
            self.assertTrue(
                any("Corpus/Story.md" in error and "U+015F" in error for error in errors)
            )

    def test_transliteration_wrong_header_is_an_error(self):
        # check.py must be at least as strict as build.py: renaming a
        # column in the table header must fail check.py too, not just
        # build.py.
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory)
            bad_table = (
                "# Transliteration\n\n"
                "| IPA | latin-1 | latin-2 | latin-3 | cyr-1 | cyr-3 |\n"
                "| --- | --- | --- | --- | --- | --- |\n"
            ) + "".join(f"| p{i} | a | b | c | d | e |\n" for i in range(18))
            (root / "Language" / "Phonology" / "Transliteration.md").write_text(
                bad_table, encoding="utf-8"
            )
            errors, _ = check_vault(root)
            self.assertTrue(
                any("заголовок" in error and "контракту" in error for error in errors)
            )

    def test_phoneme_count_follows_inventory(self):
        # Adding a 19th phoneme should be possible by editing notes alone:
        # add a row to the table AND a phoneme to Inventory.md, and the
        # expected count must follow, with no code change.
        extra_inventory = INVENTORY.replace(
            "**simple**: θ, s, sʲ, ʃ, ʂ, ɕ, ç, x, χ, ħ, h, ɬ, 𝼆",
            "**simple**: θ, s, sʲ, ʃ, ʂ, ɕ, ç, x, χ, ħ, h, ɬ, 𝼆, k",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, table_rows=19, inventory=extra_inventory)
            errors, _ = check_vault(root)
            self.assertEqual(errors, [])

        # Without the matching Inventory.md entry, 19 rows is now wrong
        # (expected stays 18).
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, table_rows=19)
            errors, _ = check_vault(root)
            self.assertTrue(any("18" in error for error in errors))

    def test_link_to_corpus_note_resolves(self):
        # A lexeme linking [[Fable]] where Fable.md lives in Corpus/, not
        # Language/, must not be a broken link.
        with_link = GOOD_LEXEME.replace("meaning: place", "meaning: place, see [[Fable]]")
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {"gaśi": with_link})
            (root / "Corpus").mkdir(parents=True)
            (root / "Corpus" / "Fable.md").write_text("# Fable\n", encoding="utf-8")
            errors, _ = check_vault(root)
            self.assertTrue(not any("Fable" in error for error in errors))

    def test_root_link_into_corpus_note_is_still_wrong_kind(self):
        # Widening link resolution to the whole vault must not weaken the
        # kind-aware check: a root field pointing at a note that only
        # exists in Corpus/ (not Language/Roots/) is still an error.
        bad = GOOD_LEXEME.replace('root: "[[-gaśi-]]"', 'root: "[[Fable]]"')
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {"gaśi": bad})
            (root / "Corpus").mkdir(parents=True)
            (root / "Corpus" / "Fable.md").write_text("# Fable\n", encoding="utf-8")
            errors, _ = check_vault(root)
            self.assertTrue(
                any("root" in error and "ожидается заметка" in error for error in errors)
            )


if __name__ == "__main__":
    unittest.main()
