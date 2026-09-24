import re
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit


SKILL_DIR = Path(__file__).resolve().parents[1]
SKILL_PATH = SKILL_DIR / "SKILL.md"


def markdown_files():
    return sorted(SKILL_DIR.rglob("*.md"))


def frontmatter(text):
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise AssertionError("SKILL.md must start with YAML frontmatter")
    fields = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if separator:
            fields[key.strip()] = value.strip()
    return fields


class SkillContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_PATH.read_text(encoding="utf-8")
        cls.fields = frontmatter(cls.text)

    def test_frontmatter_name_and_description(self):
        self.assertEqual("orch-burn-down", self.fields.get("name"))
        description = self.fields.get("description", "")
        for phrase in (
            "HELIX ticket",
            "burn down",
            "running or resuming the orchestrator",
            "READY-FOR-MERGE",
            "human review and merge",
        ):
            self.assertIn(phrase, description)

    def test_all_local_markdown_links_resolve(self):
        links = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
        for document in markdown_files():
            for target in links.findall(document.read_text(encoding="utf-8")):
                parsed = urlsplit(target.strip().split(maxsplit=1)[0])
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                resolved = (document.parent / unquote(parsed.path)).resolve()
                self.assertTrue(resolved.exists(), f"{document}: missing link target {target}")

    def test_structural_sources_are_linked(self):
        for path in (
            "../../../../ops/orchestrator/README.md",
            "../../../../ops/orchestrator/policy.example.json",
            "../../../../ops/orchestrator/orch.py",
        ):
            self.assertIn(f"]({path})", self.text)
            self.assertTrue((SKILL_DIR / path).resolve().is_file())

    def test_run_command_and_dispositions_are_required(self):
        self.assertIn(
            "ops/orchestrator/orch run --repo OWNER/REPO --policy PATH/TO/POLICY.json [--state PATH/TO/STATE.json]",
            self.text,
        )
        for disposition in ("planned", "ready_for_merge", "complete", "blocked", "failed"):
            self.assertRegex(self.text, rf"`{disposition}`")

    def test_never_merge_rule(self):
        self.assertIn("Never merge.", self.text)
        self.assertIn("Show the reported pull request to the human for review and stop.", self.text)
        self.assertIn("After the human confirms the merge, rerun the same command.", self.text)

    def test_stale_manual_workflow_is_absent(self):
        corpus = "\n".join(path.read_text(encoding="utf-8") for path in markdown_files())
        stale_patterns = (
            r"\borch\s+(?:reconcile|next|execute|complete|ready-check)\b",
            r"\bwebhooks?\b",
            r"\bleases?\b",
            r"\btimers?\b",
            r"\bwaiting_for_ci\b",
            r"\bharness(?:-contract)?\b",
        )
        for pattern in stale_patterns:
            self.assertIsNone(re.search(pattern, corpus, re.IGNORECASE), pattern)
        for obsolete in (
            "references/harness-contract.md",
            "scripts/verify_webhook.py",
            "scripts/test_verify_webhook.py",
        ):
            self.assertFalse((SKILL_DIR / obsolete).exists(), obsolete)


if __name__ == "__main__":
    unittest.main()
