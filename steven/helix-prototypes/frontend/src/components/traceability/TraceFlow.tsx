import type { CandidateEvaluation, EvidenceChainData, ValidationResult } from "@/lib/types";

import { Kicker, cx } from "../ui";

// Lane C (#22). The five-step flow for one open rule (research/helix-e2e-workbench-v1.html,
// `TRACE`). Every value comes from `getEvidence` and the stored candidate evaluation.

export type FlowTone = "pass" | "warn" | "block";

type Step = { key: string; kicker: string; value: string; detail: string[] };

/**
 * Which steps a rule checks. Presentation only (the reference highlights the steps the
 * rule covers); it never changes a result. Unknown rules highlight the validated claim.
 */
const RULE_FOCUS: Record<string, number[]> = {
  "manifest-locked": [0, 1],
  "bw-key-unique": [1],
  "claim-provenance": [0, 4],
  "grain-sex-stratified": [2, 3, 4],
  "mi-severity-reconcile": [3, 4],
  "noael-human-judgment": [3, 4],
};

export function ruleFocus(ruleId: string): number[] {
  return RULE_FOCUS[ruleId] ?? [3];
}

export function buildSteps(chain: EvidenceChainData, evaluation: CandidateEvaluation | undefined): Step[] {
  const { claim, sources } = chain;
  const first = sources.at(0);
  const last = sources.at(-1);
  const authority = chain.lineage?.at(0)?.authority_tier;
  const hashes = sourceHashes(chain);
  const ruleVersions = ruleVersionList(chain).join(" · ");
  const bindings = evaluation?.provenance_receipt.bindings.filter((binding) => binding.claim_id === claim.claim_id) ?? [];
  const conformance = evaluation?.template_conformance_receipt;

  return [
    {
      key: "source",
      kicker: "1 · Frozen source",
      value: sources.length > 0 ? `${sources.length} ${first?.domain ?? ""} records`.replace("  ", " ") : "No source records",
      detail: [
        first ? (last && last !== first ? `${first.source_pointer} … ${last.source_pointer}` : first.source_pointer) : "Scientific judgment: no source value",
        hashes.length > 0 ? `hash ${shortHash(hashes[0])}${hashes.length > 1 ? ` +${hashes.length - 1}` : ""}` : "no source hash",
      ],
    },
    {
      key: "facts",
      kicker: "2 · Normalized facts",
      value: displayGrain(first?.grain ?? claim.grain),
      detail: [
        [
          `domain=${first?.domain ?? "none"}`,
          `unit=${first?.unit ?? claim.unit ?? "none"}`,
          `authority=${authority ?? "n/a"}`,
        ].join(" · "),
      ],
    },
    {
      key: "transform",
      kicker: "3 · Transform",
      value: chain.transform_id ?? "No transform",
      detail: [
        `version=${chain.transform_version ?? claim.transform_version ?? "n/a"} · inputs=${sources.length}`,
        chain.recomputed_value === null ? "recomputed=not calculated" : `recomputed=${formatNumber(chain.recomputed_value)} ${claim.unit}`,
      ],
    },
    {
      key: "claim",
      kicker: "4 · Validated claim",
      value: claim.value === null ? "Needs review" : `${formatNumber(claim.value)} ${claim.unit}`,
      detail: [
        `${claim.claim_id} · exact match ${chain.exact_match === null ? "n/a" : chain.exact_match ? "yes" : "no"}`,
        `${chain.validations.length} rule results${ruleVersions ? ` · ${ruleVersions}` : ""}`,
      ],
    },
    {
      key: "report",
      kicker: "5 · Report field",
      value: `Section ${claim.section_id}`,
      detail: [
        chain.report_text,
        evaluation
          ? `${bindings.length} provenance bindings · template ${conformance?.status ?? "n/a"}`
          : "No candidate evaluation recorded",
      ],
    },
  ];
}

export function TraceFlow({
  chain,
  evaluation,
  result,
  tone,
}: {
  chain: EvidenceChainData;
  evaluation: CandidateEvaluation | undefined;
  result: ValidationResult;
  tone: FlowTone;
}) {
  const focus = ruleFocus(result.rule_id);
  return (
    <ol className="hx-flow" aria-label="Traceability flow" data-testid="trace-flow">
      {buildSteps(chain, evaluation).map((step, index) => {
        const focused = focus.includes(index);
        return (
          <li key={step.key} className={cx(focused && `f-${tone}`)} data-step={step.key} data-focused={focused || undefined}>
            <Kicker size="sm" className={cx("hx-flow-kicker", focused && `is-${tone}`)}>
              {step.kicker}
            </Kicker>
            <div className="val">{step.value}</div>
            {step.detail.map((line, lineIndex) => (
              <div key={lineIndex} className="hx-mono hx-flow-detail">
                {line}
              </div>
            ))}
          </li>
        );
      })}
    </ol>
  );
}

export function shortHash(value: string): string {
  const [algo, digest] = value.includes(":") ? value.split(":", 2) : ["", value];
  return `${algo ? `${algo}:` : ""}${digest.slice(0, 12)}`;
}

export function displayGrain(grain: string): string {
  return grain.replaceAll("_x_", " × ").replaceAll("_", " ");
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(value);
}

/** Source hashes the server returned: the chain's, else the claim's, else the lineage edges'. */
export function sourceHashes(chain: EvidenceChainData): string[] {
  if (chain.source_hashes?.length) return chain.source_hashes;
  if (chain.claim.source_hashes?.length) return chain.claim.source_hashes;
  return [...new Set((chain.lineage ?? []).map((edge) => edge.source_hash).filter((hash): hash is string => Boolean(hash)))];
}

/** Rule versions the server returned: the chain's map, else the claim's, else each attached result's. */
export function ruleVersionList(chain: EvidenceChainData): string[] {
  const map = Object.keys(chain.rule_versions ?? {}).length ? chain.rule_versions : chain.claim.rule_versions;
  if (map && Object.keys(map).length > 0) return Object.entries(map).map(([rule, version]) => `${rule}@${version}`);
  return [...new Set(chain.validations.map((result) => `${result.rule_id}@${result.rule_version}`))];
}
