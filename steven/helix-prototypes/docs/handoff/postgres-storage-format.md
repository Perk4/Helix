# Storage format for an ingested study

Short version: **there is no new format to design.** A study is one
`StudyEvidencePackage` serialised to JSON and stored in a single JSONB column. That is
already how `study_packages` works, and `synthetic-e2e/helix-synthetic-bundle.json` is a
worked example of it — that file *is* the column contents.

The upload endpoint produces the same shape, so nothing downstream needs to know whether
a study arrived as a fixture or as files.

---

## The table

```python
JsonDocument = JSON().with_variant(JSONB, "postgresql")   # JSONB on PG, JSON on SQLite

class StudyPackageRow(Base):
    __tablename__ = "study_packages"
    study_id:   Mapped[str]  = mapped_column(String(80), primary_key=True)
    package_id: Mapped[str]  = mapped_column(String(80), unique=True)
    label:      Mapped[str]  = mapped_column(String(120))
    version:    Mapped[int]  = mapped_column(Integer, default=1)
    data:       Mapped[dict] = mapped_column(JsonDocument)   # ← the whole package
    created_at / updated_at
```

Round trip, both directions, in `StudyPackageRepository`:

```python
data = package.model_dump(mode="json")          # save
StudyEvidencePackage.model_validate(row.data)   # get  — validated on the way out
```

Four scalar columns are promoted for lookup and `version` increments on every save. The
model is the schema: anything that does not satisfy `StudyEvidencePackage` cannot be read
back, so a malformed document fails at the boundary rather than downstream.

## The document

```jsonc
{
  "package_id": "PKG-YZ-389",
  "label": "SYNTHETIC / NOT FOR SUBMISSION",   // Literal — enforced by the model
  "workflow_state": "gated",

  "manifest": [                                // frozen sources, one per uploaded file
    { "artifact_id": "A-ANIMAL-ROSTER", "kind": "source_data",
      "name": "animal_roster.csv", "version": "uploaded", "authority_tier": 1,
      "checksum": "sha256:4c8a9c9b…", "locked": true,
      "authorized_by": "C. Orquera" }
  ],

  "study": {
    "study_id": "STUDY-YZ-389",                // ^STUDY-[A-Z0-9-]+$
    "study_type_id": "REPEAT_DOSE_28D_RODENT",
    "species": "Sprague-Dawley (Crl:CD(SD)) Rat",
    "route": "oral gavage",                    // declared on upload, not inferred
    "duration_days": 28,                       // derived from the last body-weight day
    "protocol_version": "1.0",
    "dose_groups": [ { "group_id": "G1", "label": "Vehicle Control", "dose": 0.0,
                       "dose_unit": "mg/kg/day", "sexes": ["F","M"],
                       "planned_n_per_sex": 5 } ]
  },

  "records": {                                 // ← what intake fills; 7 named domains
    "animals":              [ { "animal_id": "M101", "group_id": "G1", "sex": "M",
                                "randomization_id": "RAND-1-M-1" } ],
    "body_weights":         [ { "record_id": "BW-M101-1", "domain": "BW",
                                "animal_id": "M101", "timepoint": "DAY 1",
                                "test_code": "BW", "value": 228.3, "unit": "g",
                                "grain": "animal_x_day",
                                "source_pointer": "A-BW#M101:DAY1" } ],
    "clinical_observations":[ { "record_id": "CL-M101-1-7-1", "timepoint": "DAYS 1-7",
                                "value": "No abnormality detected",
                                "grain": "animal_x_interval" } ],
    "organ_weights":        [ { "record_id": "OM-M101-LIVER", "test_code": "LIVER",
                                "value": 11.24, "unit": "g", "grain": "animal" } ],
    "microscopic_findings": [ { "finding_id": "MI-M101-LIVER", "tissue": "Liver",
                                "finding": "No abnormality detected",
                                "severity": "none", "controlled_term": "NORMAL" } ],
    "formulation":          [ … ],
    "food_consumption":     []                 // empty = not collected, not zero
  },

  "report_sections": [ { "section_id": "S1", "template_id": "TPL-28D-RAT-FDA-OECD-V1",
                         "status": "needs_review" } ],

  "claims": [],                                // ← empty at intake, by design
  "provenance_edges": [],
  "validation_results": [],
  "review_dispositions": [],
  "approvals": [],
  "gate_decisions": [ { "gate_id": "GATE-RELEASE", "status": "blocked" } ],
  "export_artifacts": [],
  "retrieval_index": [],
  "events": []
}
```

### Why the empty lists are the interesting part

`claims` is empty because intake produces evidence, not conclusions — `section_executor`
fills it. `food_consumption` is empty because the study did not collect it, which is not
the same as the values being zero. `gate_decisions` says blocked because nothing has been
checked.

Every one of those is a state the codebase previously could not represent: an empty
collection used to read as success in three places (see `7a6083e`).

---

## Size: measured, not guessed

Against the real database, for the largest study in the drop (PCDRUG, 150 animals,
9,338 records):

| | |
|---|---|
| raw JSON text | 2,239 KB |
| `pg_column_size(data)` | **204 KB** |
| compression | **91 %** |
| total relation size | 280 kB |

TOAST compresses the document by an order of magnitude, so a 2 MB study occupies about
200 KB and a `save()` rewrites that, not the raw figure. A 28-day study is 191 KB raw.

**So do not split the schema.** I expected write amplification to be a problem and
measured it instead of assuming; it is not one at this scale. Revisit only if a package
with the full claim and provenance-edge set — tens of thousands of edges — turns out to
compress badly, which the current data gives no reason to expect.

---

## Operational notes for this database

`titaniumdb` is shared. PostgreSQL 16.15 on Cosmos DB for PostgreSQL (Citus).

- **Teams isolate by schema**: `team04`, `team05`, `team07`, `team8`, `team9`,
  `craft_team6`, `policypulse`. There is no HELIX schema yet, and no `study_packages`
  table anywhere in the database.
- **`team04` is not us** despite the `04` in the repo name — it holds `borrower_profiles`
  and `hmda_sample`, a lending project.
- `public` already has 18 tables from other projects. Scope the connection so
  `create_schema` cannot land tables there:

```
postgresql+psycopg://…/titaniumdb?sslmode=require&options=-csearch_path%3Dhelix
```

Verified working: `create_schema`, auto-seed, `GET /workspace`, and
`POST /api/v1/studies` all ran against this database in a throwaway schema, which was
dropped afterwards.
