"""HELIX draft pipeline — standalone section-by-section report drafting.

Flow per section:
  1. COMPUTE  : pipeline.section_executor.compute_<section>(package)
                → SectionResult  (deterministic, no LLM, fully traced)
  2. RETRIEVE : pipeline.approved_report_retrieval.get_all_examples()
                → few-shot examples from the approved-report knowledge base
  3. BUILD    : section_executor.build_draft_messages(result)
                → [system: skill.md + meta_prompt, user: computed facts JSON]
                   + few-shot injected into the user turn
  4. RENDER   : LLM (gpt-5.5 via APIM) writes the narrative prose
  5. REVIEW   : human approves / gives feedback / skips

Set env vars before running:
  APIM_API_KEY   — your APIM key
  APIM_BASE_URL  — e.g. https://lgts1tetamapi01.azure-api.net/gpt51/openai
  APIM_MODEL     — model deployment name (default: gpt-5.5)
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from openai import OpenAI

from pipeline.approved_report_retrieval import add_report, get_all_examples
from pipeline.schemas import StudyEvidencePackage
from pipeline.section_executor import REGISTRY, SectionResult, build_draft_messages

# ── paths ─────────────────────────────────────────────────────────────────────
HERE        = Path(__file__).parent
BUNDLE_JSON = HERE / "synthetic-e2e" / "helix-synthetic-bundle.json"
APPROVED_MD = HERE / "synthetic-e2e" / "data" / "misc" / "approved_report_1.md"
KB_PATH     = HERE / "pipeline" / "approved_kb.json"

# ── LLM client ────────────────────────────────────────────────────────────────
API_KEY  = os.environ.get("APIM_API_KEY", "")
BASE_URL = os.environ.get("APIM_BASE_URL", "")
MODEL    = os.environ.get("APIM_MODEL", "gpt-5.5")

if not API_KEY:
    raise SystemExit(
        "\n[ERROR] Set APIM_API_KEY first:\n"
        "  $env:APIM_API_KEY  = 'your-key'\n"
        "  $env:APIM_BASE_URL = 'https://lgts1tetamapi01.azure-api.net/gpt51/openai'\n"
        "  $env:APIM_MODEL    = 'gpt-5.5'\n"
    )

def _build_llm() -> OpenAI:
    if BASE_URL and "azure-api.net" in BASE_URL:
        return OpenAI(
            api_key=API_KEY,
            base_url=f"{BASE_URL.rstrip('/')}/deployments/{MODEL}",
            default_query={"subscription-key": API_KEY},
        )
    if BASE_URL:
        return OpenAI(api_key=API_KEY, base_url=BASE_URL)
    return OpenAI(api_key=API_KEY)

llm = _build_llm()

# ── section-id → approved-report section number mapping ───────────────────────
SECTION_NUM: dict[str, str | None] = {
    "summary":               None,
    "1_objective":           "1",
    "2_experimental_design": "2",
    "3_materials_methods":   "3",
    "4_deviations":          "4",
    "5_1_formulation":       "5.1",
    "5_2_1_mortality":       "5.2.1",
    "5_2_2_clinical_obs":    "5.2.2",
    "5_2_3_body_weight":     "5.2.3",
    "5_3_1_organ_weights":   "5.3.1",
    "5_3_2_macroscopic":     "5.3.2",
    "5_3_3_microscopic":     "5.3.3",
    "5_3_4_conclusion":      "5.3.4",
    "7_qa_statement":        "7",
}


# ── step 1: load package (2-line loader, no SQLAlchemy) ───────────────────────
def load_package(path: Path) -> StudyEvidencePackage:
    return StudyEvidencePackage.model_validate(json.loads(path.read_text()))


# ── step 2: retrieve few-shot examples from approved-report KB ────────────────
def _few_shot_block(kb: dict, section_id: str) -> str:
    sec_num = SECTION_NUM.get(section_id)
    if not sec_num or not kb:
        return ""
    try:
        examples = get_all_examples(kb, "TOX", sec_num)
    except KeyError:
        return ""
    if not examples:
        return ""
    lines = [
        "APPROVED EXAMPLES — same section from previously approved reports."
        " Match this style exactly:",
        "",
    ]
    for ex in examples:
        lines.append(f"--- {ex['report_id']} | {ex['section_title']} ---")
        lines.append(ex["content"][:1500])  # cap per example to avoid token overflow
        lines.append("")
    return "\n".join(lines)


# ── step 4: LLM render ────────────────────────────────────────────────────────
def render_draft(result: SectionResult, few_shot: str, prior_feedback: list[str]) -> str:
    messages = build_draft_messages(result)

    extra = ""
    if few_shot:
        extra += few_shot + "\n\n---\n\n"
    if prior_feedback:
        extra += (
            "PREVIOUS REVIEWER FEEDBACK — incorporate all of these:\n"
            + "\n".join(f"  • {fb}" for fb in prior_feedback)
            + "\n\n---\n\n"
        )
    if extra:
        messages[1]["content"] = extra + messages[1]["content"]

    response = llm.chat.completions.create(
        model=MODEL,
        max_completion_tokens=2000,
        messages=messages,
    )
    return response.choices[0].message.content.strip()


# ── step 5: human review loop ─────────────────────────────────────────────────
def review_loop(result: SectionResult, kb: dict) -> str:
    few_shot = _few_shot_block(kb, result.section_id)
    feedback_history: list[str] = []
    iteration = 0

    while True:
        iteration += 1
        print(f"\n{'='*64}")
        print(f"  {result.title}  —  draft {iteration}")
        print(f"  data_available={result.data_available}  "
              f"provenance={len(result.provenance)} records")
        print(f"{'='*64}")
        if not result.data_available:
            print(f"  [NOTE] {result.note}")
        print("  Calling LLM … please wait\n")

        draft = render_draft(result, few_shot, feedback_history)

        print(draft)
        if result.note:
            print(f"\n  [NOTE] {result.note}")
        print("\n" + "─"*64)
        print("  [A] Approve and finalise")
        print("  [F] Give feedback for another draft")
        print("  [S] Skip this section")
        choice = input("\nChoice (A/F/S): ").strip().upper()

        if choice == "A":
            print(f"\n✓  '{result.title}' approved.\n")
            return draft
        if choice == "S":
            print(f"\n—  '{result.title}' skipped.\n")
            return ""
        if choice == "F":
            fb = input("Feedback: ").strip()
            if fb:
                feedback_history.append(fb)
            print("\nRegenerating with your feedback …")
        else:
            print("Please enter A, F, or S.")


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"\nHELIX Draft Pipeline")
    print(f"Model : {MODEL}")
    print(f"Endpoint : {BASE_URL or 'openai default'}\n")

    # Step 1: load study evidence package
    print("Loading study evidence package …")
    package = load_package(BUNDLE_JSON)
    print(f"  Study   : {package.study.study_id}")
    print(f"  Species : {package.study.species}")
    print(f"  Animals : {len(package.records.animals)}")
    print(f"  Groups  : {len(package.study.dose_groups)}\n")

    # Step 2: build approved-report knowledge base
    kb: dict = {}
    if APPROVED_MD.exists():
        print(f"Building approved-report KB …")
        try:
            kb = add_report(str(APPROVED_MD), kb_path=str(KB_PATH))
            report_type = list(kb.keys())[0] if kb else "?"
            n_reports = len(kb.get(report_type, {}))
            print(f"  KB ready: {n_reports} report(s) indexed under type '{report_type}'\n")
        except Exception as e:
            print(f"  [WARN] Could not build KB: {e} — skipping few-shot injection.\n")
    else:
        print(f"  [WARN] {APPROVED_MD.name} not found — skipping few-shot injection.\n")

    # Section selection
    section_ids = list(REGISTRY.keys())
    print("Available sections:")
    for i, sid in enumerate(section_ids, 1):
        print(f"  {i:>2}. {sid}")

    raw = input("\nEnter number(s) (comma-separated) or 'all': ").strip().lower()

    if raw == "all":
        selected = section_ids
    else:
        selected = []
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit() and 1 <= int(part) <= len(section_ids):
                selected.append(section_ids[int(part) - 1])
            else:
                print(f"  [WARN] Ignoring '{part}'")

    if not selected:
        print("No valid sections selected.")
        return

    # Steps 3-5: compute → retrieve → render → review, one section at a time
    finalised: dict[str, str] = {}
    for sid in selected:
        print(f"\n{'─'*64}")
        print(f"  Computing section: {sid}")
        result = REGISTRY[sid](package)
        approved = review_loop(result, kb)
        if approved:
            finalised[sid] = approved

    # Assemble and save
    if finalised:
        out_path = HERE / "draft_output.md"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"# HELIX Draft Report — {package.study.study_id}\n\n")
            for content in finalised.values():
                f.write(f"{content}\n\n---\n\n")
        print(f"\nFinalised draft saved to: {out_path}")
        print(f"Sections completed : {len(finalised)}/{len(selected)}")
    else:
        print("\nNo sections finalised.")


if __name__ == "__main__":
    main()
