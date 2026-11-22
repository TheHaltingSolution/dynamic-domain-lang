"""Observable syntax acceptance and rejection for the bounded SPL surface."""
from pathlib import Path
import re
import unittest

from spl_compiler.parser import ParseError, lex, parse


ROOT = Path(__file__).resolve().parents[1]
HEADER = 'schedule Test language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" '


def schedule(body: str) -> str:
    return HEADER + "{ " + body + " }"


class ParserTests(unittest.TestCase):
    def assert_error(self, body: str, code: str = "SYNTAX_ERROR") -> ParseError:
        with self.assertRaises(ParseError) as error:
            parse(schedule(body), "negative.spl")
        self.assertEqual(code, error.exception.code)
        self.assertEqual("negative.spl", error.exception.span["source"])
        return error.exception

    def test_published_schedules_are_exact_extracted_fixtures(self):
        reference = (ROOT / "docs/spl/language-reference.md").read_text(encoding="utf-8")
        blocks = re.findall(r"```spl\n(.*?)\n```", reference, re.S)
        for text, relative in zip(blocks, ["cases/sv/sv01.spl", "cases/lg/lg01.spl"], strict=True):
            fixture = ROOT / relative
            self.assertEqual(text + "\n", fixture.read_text(encoding="utf-8"))
            tree = parse(text, relative)
            self.assertEqual("spl/0.1-draft", tree["language"])
            self.assertTrue(tree["declarations"])
            self.assertEqual(1, tree["span"]["line"])

    def test_rq07_profile_preserves_missing_incurred_date(self):
        path = ROOT / "cases/sv/rq07.spl"
        text = path.read_text(encoding="utf-8")
        tree = parse(text, str(path))
        costs = next(d for d in tree["declarations"] if d.get("name") == "eligible_costs")
        self.assertEqual("SVPostingCost", costs["type"]["args"][0]["name"])
        self.assertIn("c.recognition_date", text)
        self.assertNotIn("c.incurred_date", text)

    def test_exact_number_spelling_and_precedence(self):
        expression = parse(schedule("define x = USD 0.0500 + USD 0.01 * 0.10;"))["declarations"][0]["expr"]
        self.assertEqual("+", expression["op"])
        self.assertEqual("0.0500", expression["left"]["value"])
        self.assertEqual("*", expression["right"]["op"])
        self.assertEqual("0.10", expression["right"]["right"]["value"])

    def test_comments_and_json_escaping_are_distinct(self):
        body = '// ignored "string"\n emit "message" = "slash // quote \\\" and \\u03b1";'
        tree = parse(schedule(body))
        value = tree["declarations"][0]["expr"]["value"]
        self.assertEqual('slash // quote " and α', value)
        self.assertEqual(2, tree["declarations"][0]["span"]["line"])

    def test_comprehension_has_explicit_local_declarations(self):
        tree = parse(schedule('define values = for each x in [1, 2] { define y = x + 1; require y > 0 else "POSITIVE"; yield y; };'))
        expression = tree["declarations"][0]["expr"]
        self.assertEqual("for", expression["kind"])
        self.assertEqual(["define", "require"], [d["kind"] for d in expression["declarations"]])
        self.assertEqual("y", expression["yield"]["name"])

    def test_conditional_operand_requires_parentheses(self):
        self.assert_error("define x = 2 * if true then 1 else 0;")
        expression = parse(schedule("define x = 2 * (if true then 1 else 0);"))["declarations"][0]["expr"]
        self.assertEqual("if", expression["right"]["kind"])

    def test_duplicate_record_fields_rejected(self):
        self.assert_error("emit \"r\" = {value: 1, value: 2};", "DUPLICATE_FIELD")

    def test_unknown_declaration_rejected(self):
        self.assert_error("while true { };", "UNSUPPORTED_DECLARATION")

    def test_lambda_cannot_escape_argument(self):
        self.assert_error("define f = x => x + 1;")

    def test_calls_cannot_target_arbitrary_expressions(self):
        self.assert_error("define x = record.function(1);", "UNSUPPORTED_CALL")

    def test_closed_numeric_lexicon(self):
        for literal in ("1e6", "1,000", "1.", ".5", "+1"):
            with self.subTest(literal=literal):
                self.assert_error("define x = " + literal + ";")

    def test_invalid_strings_rejected(self):
        for literal in ('"bad\\x20"', '"unclosed', '"line\nbreak"', '"\\uD800"'):
            with self.subTest(literal=literal):
                self.assert_error("emit \"test\" = " + literal + ";", "INVALID_STRING")

    def test_choose_requires_arm_and_unambiguous_syntax(self):
        self.assert_error("define x = choose unique { otherwise => 1; };")
        self.assert_error("define x = choose priority { when true => 1; };")
        tree = parse(schedule("define x = choose unique { when false => 1; otherwise => 2; };"))
        expression = tree["declarations"][0]["expr"]
        self.assertEqual(1, len(expression["arms"]))
        self.assertEqual("2", expression["otherwise"]["value"])

    def test_comparisons_are_not_chained(self):
        self.assert_error("define x = 0 < 1 < 2;")
        self.assert_error("define x = 0 == 1 == 2;")

    def test_missing_semicolon_or_braces_rejected(self):
        self.assert_error("define x = 1")
        with self.assertRaises(ParseError):
            parse(HEADER + "{ define x = 1;")

    def test_trailing_source_rejected(self):
        with self.assertRaises(ParseError) as error:
            parse(schedule("define x = 1;") + " injected")
        self.assertEqual("TRAILING_CONTENT", error.exception.code)

    def test_lexical_positions_after_multiline_comments(self):
        tokens = lex("// comment\n\n  USD 1", "positions.spl")
        self.assertEqual({"source": "positions.spl", "line": 3, "column": 3, "start": 14, "end": 17}, tokens[0].span)


if __name__ == "__main__":
    unittest.main()
