"""Keep finite completion claims tied to requirements, dependencies and evidence."""
from collections import Counter
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CompletionBacklogTests(unittest.TestCase):
    def test_requirement_disposition_and_dependency_graph(self):
        data = json.loads((ROOT / "docs/spl/completion-backlog.json").read_text(encoding="utf-8"))
        items = {r["id"]: r for r in data["work_items"]}
        self.assertEqual(len(items), len(data["work_items"]))
        self.assertEqual({f["id"] for f in data["families"]}, {f"C{i:02d}" for i in range(1, 18)})
        self.assertEqual(data["status_counts"], dict(Counter(r["status"] for r in items.values())))
        ledger = (ROOT / "docs/spl/conformance-ledger.md").read_text(encoding="utf-8")
        granular = set(re.findall(r"^\| ([GTOQFDRUA][0-9]{2})\b", ledger, re.MULTILINE))
        dispositions = {r["requirement"] for r in data["ledger_disposition"]}
        self.assertEqual(dispositions, granular)
        known = granular | {f"C{i:02d}" for i in range(1, 18)}
        done, visiting = set(), set()

        def visit(identity):
            self.assertNotIn(identity, visiting, "Dependency cycle")
            if identity in done:
                return
            visiting.add(identity)
            row = items[identity]
            self.assertIn(row["status"], data["status_meanings"])
            self.assertTrue(row["requirements"] and row["acceptance"])
            self.assertLessEqual(set(row["requirements"]), known)
            for dependency in row["depends_on"]:
                self.assertIn(dependency, items)
                if row["status"] == "complete":
                    self.assertEqual(items[dependency]["status"], "complete")
                visit(dependency)
            if row["status"] == "complete":
                self.assertTrue(row.get("evidence"))
                for name in row["evidence"]:
                    # Local checkouts may not have this workstation's external
                    # artifacts; repository evidence must always be portable.
                    if not re.match(r"^[A-Za-z]:[/\\]", name):
                        self.assertTrue((ROOT / name).is_file(), name)
            visiting.remove(identity)
            done.add(identity)

        for identity in items:
            visit(identity)
        for row in data["ledger_disposition"]:
            self.assertLessEqual(set(row["work_items"]), set(items))


if __name__ == "__main__":
    unittest.main()
