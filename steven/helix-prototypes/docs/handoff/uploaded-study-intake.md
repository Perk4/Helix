# Handoff: creating a study from uploaded files

Two commits on `feat/chris-intake-on-steven`, branched from `feat/steven-workspace`
at `0ef0382`. **2 ahead, 0 behind** — a fast-forward.

`38 passed` — your 17, unchanged, plus 21 new.

```
76cf637  feat(helix): create a study from uploaded source files
7a6083e  fix(helix): three empty-collection bugs in gating and report assembly
```

They are deliberately separate. The fixes stand on their own and you can take them
without the feature.

---

## 1. What the feature does

`POST /api/v1/studies` accepts a study's own files — CSV, Excel, PDF, Word, or a zip
of them — and derives a `StudyEvidencePackage`, saved through the existing
`StudyPackageRepository`. The seeded fixture path is untouched; this is a second way
in, not a replacement.

```
POST /api/v1/studies        multipart: files[] + study_id, route,
                            protocol_version, authorized_by
```

Verified against a real 40-animal study: 200 body weights, 243 microscopic findings,
240 organ weights, 12 formulation records, 8 manifest entries with real SHA-256.

### Three outcomes, and the receipt says which each file got

| Outcome | What | Tier | Parsed |
|---|---|---|---|
| `data` | CSV/Excel whose **name** matches a known domain | 1 | yes |
| `authority` | PDF/Word | 2 protocol, 3 other | **no** |
| `rejected` | unknown extension, or tabular under an unknown name | — | — |

A PDF is checksummed into the frozen manifest and read by nothing. A signed protocol
governs a study without being machine-readable, and turning its prose into numbers
would manufacture evidence — this is the `A-STATS` situation your ADRs already
describe.

`weights.csv` is **rejected, not guessed**. It might be body weights. The domain comes
from the file name, never the contents, because a wrong guess mislabels every number
derived from it.

### The package is stored with no claims

This is the design decision most worth your review.

`intake` produces records, a study, and a frozen manifest. It produces **zero claims**.
Computing those is `section_executor`'s job, and a package that arrived with claims
would carry provenance nobody could check. The release gate is therefore blocked until
validation actually runs.

That choice is what exposed the three bugs below.

### Route and protocol version are required form fields

They are in no column. They are not inferred, and the caller is recorded as their
source. A study staged without them is rejected rather than run on invented context.

### Data quality is reported, not repaired

- The pathology grade scale is read **per study**. Studies disagree about whether
  grade 1 means Minimal or Mild; a grade carrying two different labels in one study is
  reported as an anomaly rather than resolved.
- A vehicle-control `ND` is a result, not a gap. It keeps the lab's own token — a zero
  would assert a measured concentration of zero.
- Rows that cannot be placed on the timeline are dropped **with a reason** in the receipt.
- `gross_pathology` is read and reported but not carried, because `StudyRecords` does
  not name it.

### Archives are treated as hostile input

Members are taken by base name, size and count are capped. Four zip-slip spellings are
tested — including `../../../body_weights.csv`, which uses a *recognised* domain name so
it cannot be refused on the name alone. It lands inside the study; nothing escapes.

---

## 2. Three bugs in existing code (`7a6083e`)

Every one is an empty collection reading as success. None could fire on the seeded
fixture, which always has claims, artifacts and results.

**`reporting.py` — `claim_report_text` used a defaultless `next()`.**
A package without `C-BW-HIGH` raised `StopIteration`, which surfaces as
`RuntimeError: coroutine raised StopIteration` and takes down the whole
`GET /workspace` response. It now renders a review marker. `claim_edges[...]` lookups
were the same shape and are now `.get(..., 0)`.

**`service.py` — `all([])` is `True`, in two places.**

```python
# derive_release_gate: a package with NO export artifacts read as fully EXPORTED
- if all(a.status == "exported" for a in package.export_artifacts):
+ if package.export_artifacts and all(...):

# export(): would have returned a success receipt for work it never did
- already_exported = all(a.status == "exported" for a in package.export_artifacts)
+ already_exported = bool(package.export_artifacts) and all(...)
```

**`service.py` — "nothing failed" is not "passed".**
With those two fixed, an unvalidated package fell through to `READY_FOR_SIGNATURE`,
because an empty validation set produces no blocking failures. A package that has never
been validated is now blocked. Packages that *have* been validated are unaffected.

Two regression tests pin the gate behaviour.

---

## 3. Things you may want to change

**`main.py` and `service.py` are the shared seam.** You touched both in the section-run
work (49 and 54 lines); we added 75 and 17. Ours sit on top of yours cleanly because we
branched from your branch, but they are the files most likely to conflict when `main`
is merged.

**`frontend/src/app/page.tsx` hard-codes `studyId="STUDY-HLX-028"`.** Not changed on this
branch, but worth knowing: any study id other than that one shows "Unknown study" while
the backend serves it correctly. A one-line `process.env.NEXT_PUBLIC_STUDY_ID ?? "STUDY-HLX-028"`
fixes it with no behaviour change when unset.

**`docs/implementation/first-vertical-slice.md` asserts the candidate contains `286.2 g`.**
That is the seeded fixture's combined high-dose mean. It will not hold for an uploaded
study.

**No UI for the upload.** The endpoint is API-only. Your frontend has no file input
anywhere — stage 01 "Authorized upload" renders a read-only manifest panel. If you want
it demoable by clicking, that is a small React page somebody needs to write.

---

## 4. Codex on Azure — verified working

Relevant to the section-run path, and to `feat(actions): support Azure Codex review config`.

Codex supports Azure OpenAI as a custom provider, so **no OpenAI account is needed**:

```toml
[model_providers.azure]
name         = "Azure"
base_url     = "https://<resource>.openai.azure.com/openai"
env_key      = "AZURE_OPENAI_API_KEY"
query_params = { api-version = "2025-04-01-preview" }
wire_api     = "responses"
```

Proven live with `codex exec` against our `gpt-5.5` deployment: `provider: azure`,
real session id, expected output. Confirmed alongside it:

- The **Responses API returns 200** on the direct Azure endpoint, the same endpoint with
  `api-version`, and the APIM gateway. `wire_api = "responses"` is a hard requirement.
- Neither `OPENAI_API_KEY` nor `APIM_KEY` authenticates to `api.openai.com` (both 401).
  They are Azure keys; the custom-provider route is the only one.
- **The direct Azure endpoint needs VPN** — it answered 403 off-VPN and 400 on. The APIM
  gateway worked in both cases, so prefer APIM as `base_url` for CI or anything off-VPN.

---

## 5. Azure blob storage

There is one storage account, `lgts1tetamstg01` (rg `lgts1tetarg`, eastus, StorageV2,
`allowBlobPublicAccess: false`), and a connection string for it already exists in the
team `.env`.

Two caveats:

- Our AAD identities have **no data-plane role**. `--auth-mode login` fails on blobs;
  only shared-key access works. Worth requesting `Storage Blob Data Contributor` rather
  than shipping a key.
- None of the 12 containers are ours — they belong to other teams. There is no HELIX
  container yet.

One thing to raise with whoever administers the subscription: the account key grants
read access to **every** container, including another team's `search_credentials/`.

---

## 6. What is not in this branch

About 12,900 lines remain on `feat/chris-helix-port`, unported on purpose:

- Five Data Validation Packages with inferential statistics (scipy Dunnett, Fisher),
  enforcement classes, and contract conformance against the seven schemas
- A span-level provenance verifier — measured recall 13/13, precision 9/9 on a
  hand-built defect set
- ADRs 0022–0030 and a risk register
- An independent audit script that imports no application code and recomputes from
  source

The five executors overlap `section_executor.py` on `main` by design — same idea,
different axis (data domain vs report section). Merging two designs is a team decision,
not something to copy in. Happy to walk through the differences.
