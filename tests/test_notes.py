import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.notes import parse_note, format_note


class ParseNote(unittest.TestCase):
    def test_scalar_and_empty_and_link(self):
        text = (
            "---\n"
            "type: lexeme\n"
            "lemma: gaśi\n"
            "noun_class: \"[[Class 7]]\"\n"
            "etym:\n"
            "---\n"
            "\n"
        )
        fm, body = parse_note(text)
        self.assertEqual(fm["type"], "lexeme")
        self.assertEqual(fm["lemma"], "gaśi")
        self.assertEqual(fm["noun_class"], "[[Class 7]]")
        self.assertIsNone(fm["etym"])
        self.assertEqual(body, "\n")

    def test_block_sequence(self):
        text = "---\nscript:\n  - gaśi\n  - гащи\ntags:\n  - lexeme\n---\n"
        fm, _ = parse_note(text)
        self.assertEqual(fm["script"], ["gaśi", "гащи"])
        self.assertEqual(fm["tags"], ["lexeme"])

    def test_inline_sequence(self):
        fm, _ = parse_note("---\ntags: [lexeme]\n---\n")
        self.assertEqual(fm["tags"], ["lexeme"])

    def test_empty_inline_sequence_is_a_list(self):
        fm, _ = parse_note("---\nexamples: []\n---\n")
        self.assertEqual(fm["examples"], [])

    def test_meaning_with_comma_stays_one_string(self):
        fm, _ = parse_note("---\nmeaning: to open, to disembowel\n---\n")
        self.assertEqual(fm["meaning"], "to open, to disembowel")

    def test_no_frontmatter(self):
        fm, body = parse_note("# Just prose\n")
        self.assertEqual(fm, {})
        self.assertEqual(body, "# Just prose\n")

    def test_body_preserved_after_frontmatter(self):
        fm, body = parse_note("---\ntype: root\n---\nSome prose.\n")
        self.assertEqual(body, "Some prose.\n")


class ParseTable(unittest.TestCase):
    def test_separator_row_is_dropped(self):
        from tools.notes import parse_table

        text = (
            "# Title\n\n"
            "| IPA | latin-1 |\n"
            "| --- | ------- |\n"
            "| θ | t |\n"
            "| ʃ | ș |\n"
        )
        rows = parse_table(text)
        self.assertEqual(rows[0], ["IPA", "latin-1"])
        self.assertEqual(rows[1:], [["θ", "t"], ["ʃ", "ș"]])

    def test_no_table_returns_empty(self):
        from tools.notes import parse_table

        self.assertEqual(parse_table("Just prose.\n"), [])


class FormatNote(unittest.TestCase):
    def test_roundtrip_flat(self):
        fm = {"type": "lexeme", "lemma": "gaśi", "etym": None, "tags": ["lexeme"]}
        text = format_note(fm, "")
        self.assertEqual(
            text,
            "---\ntype: lexeme\nlemma: gaśi\netym:\ntags: [lexeme]\n---\n",
        )

    def test_link_value_is_quoted(self):
        text = format_note({"noun_class": "[[Class 7]]"}, "")
        self.assertEqual(text, '---\nnoun_class: "[[Class 7]]"\n---\n')

    def test_parse_of_formatted_matches_original(self):
        fm = {
            "type": "lexeme",
            "lemma": "gaśi",
            "cyrillic": "гащи",
            "meaning": "to open, to disembowel",
            "noun_class": "[[Class 7]]",
            "etym": None,
            "tags": ["lexeme"],
        }
        again, _ = parse_note(format_note(fm, ""))
        self.assertEqual(again, fm)

    def test_list_of_link_values_is_quoted(self):
        text = format_note({"root": ["[[-a-]]", "[[-b-]]"]}, "")
        self.assertEqual(text, '---\nroot: ["[[-a-]]", "[[-b-]]"]\n---\n')

    def test_list_of_links_roundtrips(self):
        fm = {"root": ["[[-a-]]", "[[-b-]]"]}
        again, body = parse_note(format_note(fm, ""))
        self.assertEqual(again, fm)
        self.assertEqual(body, "")

    def test_single_word_list_item_stays_unquoted(self):
        text = format_note({"tags": ["lexeme"]}, "")
        self.assertEqual(text, "---\ntags: [lexeme]\n---\n")


if __name__ == "__main__":
    unittest.main()
