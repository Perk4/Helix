import type {
  ApprovalRole,
  ChatMessage,
  ChatScope,
  EvidenceChainData,
  ExportReceipt,
  PlannerMode,
  SectionContentDraft,
  SectionListItem,
  SectionRunReceipt,
  ValidationRun,
  Workspace,
} from "./types";

const API_ROOT = (process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1").replace(
  /\/$/,
  "",
);

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

export async function getWorkspace(studyId: string): Promise<Workspace> {
  const value = await request(`/studies/${encodeURIComponent(studyId)}/workspace`);
  assertWorkspace(value);
  return value;
}

export async function runValidation(
  studyId: string,
  planner: PlannerMode,
): Promise<ValidationRun> {
  const value = await request(`/studies/${encodeURIComponent(studyId)}/validation-runs`, {
    method: "POST",
    body: JSON.stringify({ planner }),
  });
  assertValidationRun(value);
  return value;
}

export async function runSectionAgent(studyId: string): Promise<SectionRunReceipt> {
  const value = await request(`/studies/${encodeURIComponent(studyId)}/section-runs`, {
    method: "POST",
    body: JSON.stringify({
      section_package_id: "section.5_2_3_body_weight",
      idempotency_key: `workbench-${studyId}-body-weight-v1`,
    }),
  });
  assertSectionRunReceipt(value);
  return value;
}

export async function getSections(studyId: string): Promise<SectionListItem[]> {
  const value = await request(`/studies/${encodeURIComponent(studyId)}/sections`);
  if (!Array.isArray(value)) {
    throw new Error("The sections response does not match the generated API contract.");
  }
  return value as SectionListItem[];
}

export async function getSectionDraft(
  studyId: string,
  sectionId: string,
): Promise<SectionContentDraft | null> {
  const value = await request(
    `/studies/${encodeURIComponent(studyId)}/sections/${encodeURIComponent(sectionId)}/draft`,
  );
  return (value ?? null) as SectionContentDraft | null;
}

export async function generateSectionDraft(
  studyId: string,
  sectionId: string,
  feedback: string[] = [],
): Promise<SectionContentDraft> {
  const value = await request(
    `/studies/${encodeURIComponent(studyId)}/sections/${encodeURIComponent(sectionId)}/draft`,
    { method: "POST", body: JSON.stringify({ feedback }) },
  );
  return value as SectionContentDraft;
}

export async function reviseSectionDraft(
  studyId: string,
  sectionId: string,
  feedback: string,
): Promise<SectionContentDraft> {
  const value = await request(
    `/studies/${encodeURIComponent(studyId)}/sections/${encodeURIComponent(sectionId)}/revise`,
    { method: "POST", body: JSON.stringify({ feedback }) },
  );
  return value as SectionContentDraft;
}

export async function applySection(
  studyId: string,
  sectionId: string,
  version: number,
): Promise<SectionContentDraft> {
  const value = await request(
    `/studies/${encodeURIComponent(studyId)}/sections/${encodeURIComponent(sectionId)}/apply`,
    { method: "POST", body: JSON.stringify({ version }) },
  );
  return value as SectionContentDraft;
}

export async function discardSection(
  studyId: string,
  sectionId: string,
  version: number,
): Promise<SectionContentDraft> {
  const value = await request(
    `/studies/${encodeURIComponent(studyId)}/sections/${encodeURIComponent(sectionId)}/discard`,
    { method: "POST", body: JSON.stringify({ version }) },
  );
  return value as SectionContentDraft;
}

export async function verifySection(studyId: string, sectionId: string): Promise<SectionContentDraft> {
  const value = await request(
    `/studies/${encodeURIComponent(studyId)}/sections/${encodeURIComponent(sectionId)}/verify`,
    { method: "POST", body: JSON.stringify({}) },
  );
  return value as SectionContentDraft;
}

export async function getChat(studyId: string): Promise<ChatMessage[]> {
  const value = await request(`/studies/${encodeURIComponent(studyId)}/chat`);
  if (!Array.isArray(value)) {
    throw new Error("The chat response does not match the generated API contract.");
  }
  return value as ChatMessage[];
}

export async function sendChat(
  studyId: string,
  message: string,
  scope: ChatScope,
  sectionId: string | null,
): Promise<ChatMessage> {
  const value = await request(`/studies/${encodeURIComponent(studyId)}/chat`, {
    method: "POST",
    body: JSON.stringify({ message, scope, section_id: sectionId }),
  });
  return value as ChatMessage;
}

export async function getEvidence(
  studyId: string,
  claimId: string,
): Promise<EvidenceChainData> {
  const value = await request(
    `/studies/${encodeURIComponent(studyId)}/claims/${encodeURIComponent(claimId)}/evidence`,
  );
  assertEvidenceChain(value);
  return value;
}

export async function recordDisposition(
  studyId: string,
  resultId: string,
  message: string,
): Promise<Workspace> {
  const value = await request(
    `/studies/${encodeURIComponent(studyId)}/validation-results/${encodeURIComponent(resultId)}/dispositions`,
    {
      method: "POST",
      body: JSON.stringify({
        decision: resultId === "VR-006" ? "approved_exception" : "corrected",
        reason: `Synthetic prototype disposition. ${message}`,
        reviewer: "Dr. Avery Reviewer",
      }),
    },
  );
  assertWorkspace(value);
  return value;
}

export async function recordApproval(
  studyId: string,
  role: ApprovalRole,
): Promise<Workspace> {
  const records: Record<ApprovalRole, { reviewer: string; meaning: string }> = {
    pathologist: { reviewer: "Dr. Avery Pathologist", meaning: "Scientific review complete" },
    peer_reviewer: { reviewer: "Dr. Priya Reviewer", meaning: "Independent peer review complete" },
    qau: { reviewer: "Morgan QA", meaning: "Quality assurance statement recorded" },
    study_director: { reviewer: "Dr. Sam Director", meaning: "Final report approval" },
  };
  const value = await request(`/studies/${encodeURIComponent(studyId)}/approvals`, {
    method: "POST",
    body: JSON.stringify({ role, ...records[role] }),
  });
  assertWorkspace(value);
  return value;
}

export function artifactDownloadUrl(studyId: string, artifactId: string): string {
  return `${API_ROOT}/studies/${encodeURIComponent(studyId)}/exports/${encodeURIComponent(artifactId)}`;
}

export async function exportPackage(studyId: string): Promise<ExportReceipt> {
  const value = await request(`/studies/${encodeURIComponent(studyId)}/exports`, {
    method: "POST",
    body: JSON.stringify({
      actor: "Dr. Sam Director",
      idempotency_key: `workbench-${studyId}-export-v1`,
    }),
  });
  assertExportReceipt(value);
  return value;
}

async function request(path: string, init?: RequestInit): Promise<unknown> {
  const response = await fetch(`${API_ROOT}${path}`, {
    ...init,
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  const value: unknown = await response.json();
  if (!response.ok) {
    throw new ApiError(errorMessage(value), response.status);
  }
  return value;
}

function errorMessage(value: unknown): string {
  if (isObject(value) && typeof value.detail === "string") {
    return value.detail;
  }
  return "The HELIX API returned an unexpected error.";
}

function assertWorkspace(value: unknown): asserts value is Workspace {
  if (
    !isObject(value) ||
    value.label !== "SYNTHETIC / NOT FOR SUBMISSION" ||
    !isObject(value.study) ||
    typeof value.study.study_id !== "string" ||
    !Array.isArray(value.manifest) ||
    !Array.isArray(value.stages) ||
    !Array.isArray(value.validations) ||
    !isObject(value.release_gate) ||
    typeof value.release_gate.status !== "string" ||
    !isObject(value.report)
  ) {
    throw new Error("The workspace response does not match the generated API contract.");
  }
}

function assertValidationRun(value: unknown): asserts value is ValidationRun {
  if (
    !isObject(value) ||
    typeof value.run_id !== "string" ||
    typeof value.llm_used !== "boolean" ||
    !Array.isArray(value.results)
  ) {
    throw new Error("The validation response does not match the generated API contract.");
  }
}

function assertSectionRunReceipt(value: unknown): asserts value is SectionRunReceipt {
  if (
    !isObject(value) ||
    value.status !== "candidate_recorded" ||
    value.agent_runtime !== "codex_sdk" ||
    typeof value.candidate_hash !== "string" ||
    typeof value.envelope_hash !== "string" ||
    typeof value.codex_thread_id !== "string" ||
    typeof value.skill_hash !== "string"
  ) {
    throw new Error("The section-run response does not match the generated API contract.");
  }
}

function assertEvidenceChain(value: unknown): asserts value is EvidenceChainData {
  if (
    !isObject(value) ||
    !isObject(value.claim) ||
    typeof value.claim.claim_id !== "string" ||
    !Array.isArray(value.sources) ||
    !Array.isArray(value.validations)
  ) {
    throw new Error("The evidence response does not match the generated API contract.");
  }
}

function assertExportReceipt(value: unknown): asserts value is ExportReceipt {
  if (
    !isObject(value) ||
    value.status !== "exported" ||
    typeof value.exported_at !== "string" ||
    !Array.isArray(value.artifacts)
  ) {
    throw new Error("The export response does not match the generated API contract.");
  }
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
