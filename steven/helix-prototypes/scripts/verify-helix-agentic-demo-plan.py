#!/usr/bin/env python3

import argparse
import csv
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "docs/specifications/helix-agentic-e2e-demo.md"
MATRIX_PATH = ROOT / "docs/specifications/helix-agentic-e2e-demo-coverage.tsv"
REPOSITORY = "Steven-Espaillat/Helix"
REQUIREMENT_PATTERN = re.compile(r"\b(?:DEMO|AUTH|TRACE|EVAL|UX|AZURE|PROOF)-\d{3}\b")
RANGE_PATTERN = re.compile(
    r"`(DEMO|AUTH|TRACE|EVAL|UX|AZURE|PROOF)-(\d{3})`\s+through\s+"
    r"`(DEMO|AUTH|TRACE|EVAL|UX|AZURE|PROOF)-(\d{3})`"
)
ISSUE_PATTERN = re.compile(r"#(\d+)")
DEPENDENCY_PATTERN = re.compile(r"#(\d+) -> #(\d+)")
TICKET_HEADINGS = [
    "## Goal",
    "## Locked",
    "## Acceptance",
    "## Out of scope",
    "## Refs",
    "## Process",
]
EXPECTED_TITLES = {
    28: "SPEC: HELIX agentic end-to-end Azure demo",
    29: "DEMO SLICE 0: Run the governed Codex path from production containers",
    30: "DEMO SLICE 1: Persist and render one authoritative Workflow Trace",
    31: "DEMO SLICE 2: Bind and display qualification and study-output evaluations",
    32: "DEMO SLICE 3: Export one qualified Codex-authored body-weight section",
    33: "DEMO SLICE 4: Deploy the authenticated HELIX stack to Azure",
    34: "DEMO SLICE 5: Publish the deployed golden-path proof",
}


@dataclass(frozen=True)
class CoverageRow:
    source: str
    kind: str
    issues: tuple[int, ...]
    proof: str


@dataclass(frozen=True)
class PublishedIssue:
    number: int
    title: str
    body: str
    state: str
    labels: frozenset[str]
    url: str


def requirement_references(text: str) -> set[str]:
    references = set(REQUIREMENT_PATTERN.findall(text))
    for start_prefix, start_value, end_prefix, end_value in RANGE_PATTERN.findall(text):
        if start_prefix != end_prefix:
            continue
        start = int(start_value)
        end = int(end_value)
        references.update(f"{start_prefix}-{value:03d}" for value in range(start, end + 1))
    return references


def load_coverage() -> list[CoverageRow]:
    with MATRIX_PATH.open(newline="") as handle:
        reader = csv.DictReader(handle, dialect="excel-tab")
        if reader.fieldnames != ["source", "kind", "issues", "proof"]:
            raise ValueError("coverage matrix header is invalid")
        rows = []
        for raw in reader:
            issues = tuple(int(value) for value in ISSUE_PATTERN.findall(raw["issues"]))
            rows.append(
                CoverageRow(
                    source=raw["source"],
                    kind=raw["kind"],
                    issues=issues,
                    proof=raw["proof"],
                )
            )
    return rows


def fetch_issue(number: int) -> PublishedIssue:
    completed = subprocess.run(
        [
            "gh",
            "issue",
            "view",
            str(number),
            "--repo",
            REPOSITORY,
            "--json",
            "number,title,body,state,labels,url",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    raw = json.loads(completed.stdout)
    return PublishedIssue(
        number=raw["number"],
        title=raw["title"],
        body=raw["body"],
        state=raw["state"],
        labels=frozenset(label["name"] for label in raw["labels"]),
        url=raw["url"],
    )


def validate_local(rows: list[CoverageRow]) -> list[str]:
    errors = []
    spec_requirements = requirement_references(SPEC_PATH.read_text())
    covered_requirements = {row.source for row in rows if row.kind == "requirement"}
    missing = sorted(spec_requirements - covered_requirements)
    extra = sorted(covered_requirements - spec_requirements)
    if missing:
        errors.append(f"requirements missing from coverage: {', '.join(missing)}")
    if extra:
        errors.append(f"coverage has unknown requirements: {', '.join(extra)}")
    sources = [row.source for row in rows]
    duplicates = sorted({source for source in sources if sources.count(source) > 1})
    if duplicates:
        errors.append(f"duplicate coverage sources: {', '.join(duplicates)}")
    for row in rows:
        if row.kind not in {"requirement", "adr", "dependency"}:
            errors.append(f"{row.source} has invalid kind {row.kind}")
        if not row.issues:
            errors.append(f"{row.source} has no covering issue")
        if not row.proof.strip():
            errors.append(f"{row.source} has no proof")
        unknown_issues = sorted(set(row.issues) - set(EXPECTED_TITLES))
        if unknown_issues:
            errors.append(f"{row.source} references unmanaged issues {unknown_issues}")
    return errors


def validate_published(rows: list[CoverageRow]) -> tuple[list[str], dict[int, PublishedIssue]]:
    issues = {number: fetch_issue(number) for number in EXPECTED_TITLES}
    errors = []
    for number, expected_title in EXPECTED_TITLES.items():
        issue = issues[number]
        if issue.title != expected_title:
            errors.append(f"#{number} title does not match the plan")
        if issue.state != "OPEN":
            errors.append(f"#{number} is not open")
        if "ready-for-agent" not in issue.labels:
            errors.append(f"#{number} lacks ready-for-agent")
        if number != 28:
            positions = [issue.body.find(heading) for heading in TICKET_HEADINGS]
            if any(position < 0 for position in positions) or positions != sorted(positions):
                errors.append(f"#{number} does not use the six ticket sections in order")
    for row in rows:
        if row.kind == "requirement":
            for number in row.issues:
                if row.source not in requirement_references(issues[number].body):
                    errors.append(f"#{number} does not cite mapped requirement {row.source}")
        elif row.kind == "adr":
            for number in row.issues:
                if row.source not in issues[number].body:
                    errors.append(f"#{number} does not cite mapped decision {row.source}")
        elif row.kind == "dependency":
            match = DEPENDENCY_PATTERN.fullmatch(row.source)
            if match is None:
                errors.append(f"invalid dependency source {row.source}")
                continue
            blocker = int(match.group(1))
            blocked = int(match.group(2))
            if row.issues != (blocked,):
                errors.append(f"{row.source} must map only to #{blocked}")
            process = issues[blocked].body.split("## Process", 1)[-1]
            if f"#{blocker}" not in process:
                errors.append(f"#{blocked} does not name blocker #{blocker} in Process")
    return errors, issues


def digest(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--github", action="store_true")
    args = parser.parse_args()

    rows = load_coverage()
    errors = validate_local(rows)
    issues = {}
    if args.github:
        published_errors, issues = validate_published(rows)
        errors.extend(published_errors)
    if errors:
        for error in errors:
            print(error)
        return 1
    result = {
        "verified": True,
        "requirements": sum(row.kind == "requirement" for row in rows),
        "coverage_rows": len(rows),
        "spec_hash": digest(SPEC_PATH.read_bytes()),
        "coverage_hash": digest(MATRIX_PATH.read_bytes()),
        "published_issues": [
            {
                "number": number,
                "url": issues[number].url,
                "body_hash": digest(issues[number].body.encode()),
            }
            for number in sorted(issues)
        ],
    }
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
