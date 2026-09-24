"""
user_review.py

Drafts a report section using:
  - approved_report_1.docx  (few-shot example)
  - calculated figures from study_data CSVs
  - blank_template.md       (output structure)

Presents the draft to the human for review / feedback.
The loop continues until the reviewer approves or skips.

Requires:
  pip install openai python-docx

Set these env vars before running:
  APIM_API_KEY   — your APIM / Azure OpenAI key
  APIM_BASE_URL  — your APIM gateway base URL
                   e.g. https://your-org.openai.azure.com/openai
  APIM_MODEL     — model deployment name (default: gpt-4o)
"""

from __future__ import annotations

import csv
import os
import statistics
from pathlib import Path

from docx import Document
from openai import OpenAI

# ── paths ──────────────────────────────────────────────────────────────────
BASE        = Path(__file__).parent / "synthetic-e2e" / "data"
APPROVED    = BASE / "approved_report_1.docx"
TEMPLATE_MD = BASE / "misc" / "blank_template.md"
STUDY_DATA  = BASE / "study_data"

# ── LLM client ─────────────────────────────────────────────────────────────
API_KEY  = os.environ.get("APIM_API_KEY", "")
BASE_URL = os.environ.get("APIM_BASE_URL", "")
MODEL    = os.environ.get("APIM_MODEL", "gpt-4o")

if not API_KEY:
    raise SystemExit(
        "\n[ERROR] Set your APIM key first:\n"
        "  Windows PowerShell:  $env:APIM_API_KEY = 'your-key-here'\n"
        "  Windows CMD:         set APIM_API_KEY=your-key-here\n"
        "  Optional:            $env:APIM_BASE_URL = 'https://your-gateway/...'\n"
        "                       $env:APIM_MODEL    = 'gpt-4o'\n"
    )

def _build_client() -> OpenAI:
    if BASE_URL and "azure-api.net" in BASE_URL:
        # APIM gateway: key goes as ?subscription-key= query param,
        # and the chat endpoint needs /deployments/{model} appended.
        return OpenAI(
            api_key=API_KEY,
            base_url=f"{BASE_URL.rstrip('/')}/deployments/{MODEL}",
            default_query={"subscription-key": API_KEY},
        )
    if BASE_URL:
        return OpenAI(api_key=API_KEY, base_url=BASE_URL)
    return OpenAI(api_key=API_KEY)

llm = _build_client()


# ── 1. load approved report as few-shot example ────────────────────────────

def load_approved_report(path: Path) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


# ── 2. calculate figures from raw CSVs ─────────────────────────────────────

def _read_csv(path: Path) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _group_means(rows: list[dict], group_col: str, sex_col: str,
                 key_col: str, val_col: str) -> dict:
    buckets: dict[tuple, list[float]] = {}
    for r in rows:
        k = (r[group_col], r[sex_col], r[key_col])
        try:
            buckets.setdefault(k, []).append(float(r[val_col]))
        except (ValueError, KeyError):
            pass
    return {k: round(statistics.mean(v), 2) for k, v in buckets.items()}


def calc_figures() -> str:
    # Body weights
    bw_rows = _read_csv(STUDY_DATA / "body_weights.csv")
    bw = _group_means(bw_rows, "group_number", "sex", "study_day", "body_weight_g")

    def bw_mean(g, sex, day):
        return bw.get((str(g), sex, str(day)), "N/A")

    lines = ["=== CALCULATED FIGURES ===", "", "BODY WEIGHTS (group mean g):"]
    for sex_label, sex_key in [("Males", "Male"), ("Females", "Female")]:
        lines.append(f"  {sex_label}:")
        header = "    {:>4}  ".format("Day") + "  ".join(f"G{g}" for g in range(1, 5))
        lines.append(header)
        for day in [1, 7, 14, 21, 28]:
            row = f"    {day:>4}  " + "  ".join(
                f"{bw_mean(g, sex_key, day):>6}" for g in range(1, 5)
            )
            lines.append(row)

    # Organ weights
    try:
        ow_rows = _read_csv(STUDY_DATA / "organ_weights.csv")
        # detect weight column name
        weight_col = next(
            (c for c in ow_rows[0] if "weight" in c.lower() and c != "relative_weight_g"),
            "weight_g",
        )
        organ_col = next(c for c in ow_rows[0] if "organ" in c.lower())
        ow = _group_means(ow_rows, "group_number", "sex", organ_col, weight_col)

        lines += ["", "ORGAN WEIGHTS (group mean g):"]
        organs = sorted({k[2] for k in ow})
        for sex_label, sex_key in [("Males", "Male"), ("Females", "Female")]:
            lines.append(f"  {sex_label}:")
            for organ in organs:
                row = f"    {organ:<24}" + "  ".join(
                    str(ow.get((str(g), sex_key, organ), "N/A")) for g in range(1, 5)
                )
                lines.append(row)
    except Exception as e:
        lines.append(f"\n[Organ weights unavailable: {e}]")

    return "\n".join(lines)


# ── 3. draft one section via LLM ───────────────────────────────────────────

SECTIONS = [
    "Body Weight",
    "Clinical Observations",
    "Organ Weights",
    "Histopathology Findings",
]


def draft_section(
    section: str,
    few_shot: str,
    figures: str,
    template: str,
    prior_feedback: list[str],
) -> str:
    feedback_block = ""
    if prior_feedback:
        feedback_block = (
            "\n\nPREVIOUS REVIEWER FEEDBACK — incorporate all of these:\n"
            + "\n".join(f"  • {fb}" for fb in prior_feedback)
        )

    prompt = (
        "You are a GLP nonclinical report writer.\n\n"
        "APPROVED EXAMPLE REPORT (few-shot — match this style, precision, and structure exactly):\n"
        f"{few_shot}\n\n"
        "REPORT TEMPLATE:\n"
        f"{template}\n\n"
        f"{figures}"
        f"{feedback_block}\n\n"
        f'Draft ONLY the "{section}" section.\n'
        "Rules:\n"
        "  - Use only the numbers from CALCULATED FIGURES — never invent values.\n"
        "  - Match the table format and narrative style of the approved example.\n"
        "  - Mark anything needing human scientific judgement: [REVIEWER REQUIRED: <reason>]\n"
        "  - Output markdown only, no preamble or closing remarks."
    )

    response = llm.chat.completions.create(
        model=MODEL,
        max_completion_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


# ── 4. human review loop ───────────────────────────────────────────────────

def review_loop(section: str, few_shot: str, figures: str, template: str) -> str:
    feedback_history: list[str] = []
    iteration = 0

    while True:
        iteration += 1
        print(f"\n{'='*62}")
        print(f"  {section}  —  draft {iteration}")
        print(f"{'='*62}")
        print("  Calling LLM … please wait\n")

        draft = draft_section(section, few_shot, figures, template, feedback_history)

        print(draft)
        print("\n" + "─"*62)
        print("  [A] Approve and finalise")
        print("  [F] Give feedback for another draft")
        print("  [S] Skip this section")
        choice = input("\nChoice (A/F/S): ").strip().upper()

        if choice == "A":
            print(f"\n✓  '{section}' approved.\n")
            return draft

        if choice == "S":
            print(f"\n—  '{section}' skipped.\n")
            return ""

        if choice == "F":
            fb = input("Feedback: ").strip()
            if fb:
                feedback_history.append(fb)
            print("\nRegenerating with your feedback …")
        else:
            print("Please enter A, F, or S.")


# ── 5. main ────────────────────────────────────────────────────────────────

def main():
    print("\nHELIX — Human Review Draft Loop")
    print(f"Model: {MODEL}  |  Endpoint: {BASE_URL or 'openai.com'}\n")

    print("Loading approved report …")
    few_shot = load_approved_report(APPROVED)

    print("Calculating figures from study data …")
    figures = calc_figures()

    template = TEMPLATE_MD.read_text()

    print("\nSections:")
    for i, s in enumerate(SECTIONS, 1):
        print(f"  {i}. {s}")
    choice = input("\nSection number or 'all': ").strip().lower()

    if choice == "all":
        selected = SECTIONS
    elif choice.isdigit() and 1 <= int(choice) <= len(SECTIONS):
        selected = [SECTIONS[int(choice) - 1]]
    else:
        print("Invalid choice — exiting.")
        return

    finalised: dict[str, str] = {}
    for section in selected:
        result = review_loop(section, few_shot, figures, template)
        if result:
            finalised[section] = result

    if finalised:
        out = Path(__file__).parent / "draft_output.md"
        with open(out, "w", encoding="utf-8") as f:
            for sec, content in finalised.items():
                f.write(f"## {sec}\n\n{content}\n\n---\n\n")
        print(f"\nSaved to: {out}")
    else:
        print("\nNothing finalised.")


if __name__ == "__main__":
    main()
