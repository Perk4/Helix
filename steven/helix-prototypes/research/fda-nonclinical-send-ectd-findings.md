# HELIX nonclinical reporting and submission findings

Research date: 2026-09-21. This note interprets the supplied HELIX concept as a workflow for a GLP nonclinical study report and its related FDA submission data. It is not legal advice and it does not certify a system or a submission.

## Overview

HELIX addresses a real operational seam. A study team must preserve the GLP record, author a final report, prepare machine-readable study data when SEND is required, document metadata and known issues, then package the artifacts in eCTD. Those outputs must agree, but they have different regulatory purposes.

The product should keep three gates distinct:

1. GLP record integrity and final-report control.
2. SEND and metadata conformance.
3. eCTD package acceptance.

A green technical validation result is not a scientific finding, a QAU conclusion, or FDA acceptance of the report's science.

## Authority map

| Category | What HELIX must treat as authoritative | Product consequence |
| --- | --- | --- |
| FDA regulation | 21 CFR Part 58 applies to nonclinical laboratory studies that support FDA research or marketing permits. It requires controlled raw-data changes, a final report, signed study-director report, QAU statement, and record retention and retrieval. [21 CFR 58.130](https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-58/subpart-G/section-58.130), [21 CFR 58.185](https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-58/subpart-J/section-58.185), [21 CFR 58.190](https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-58/subpart-J/section-58.190) | Do not let the application overwrite source records or a signed report. Capture original value, reason, person, and time for corrections. Route finalization through study-director and QAU controls. |
| FDA regulation when applicable | Part 11 applies to electronic records required by FDA regulations and maintained or submitted electronically. A closed system needs validation, accurate copies, protection and retrieval, authorized access, and secure time-stamped audit trails. Signed electronic records also carry signer, time, and signature meaning. [Part 11 scope guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/part-11-electronic-records-electronic-signatures-scope-and-application), [21 CFR 11.10](https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-11/subpart-B/section-11.10), [21 CFR 11.50](https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-11/subpart-B/section-11.50) | Make applicability a documented assessment. Do not market a prototype as "Part 11 compliant." Provide the evidence a validated production system would need. |
| FDA requirement set | The FDA Data Standards Catalog determines the supported and required standard version by study start date. FDA may refuse to file or receive submissions that fail required Catalog standards. [FDA study-data submission page](https://www.fda.gov/industry/study-data-standards-resources/study-data-submission-cder-and-cber), [FDA Data Standards Catalog](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/data-standards-catalog) | Store the catalog snapshot, study start date, Center, application type, and selected SENDIG/Define-XML/eCTD version. Never hard-code a SEND version as universally correct. |
| FDA guidance and technical specifications | The June 2026 Study Data Technical Conformance Guide is nonbinding guidance. It describes SEND scope, the nSDRG, Define-XML, validation, traceability, and eCTD placement. It calls for SEND for in-scope general toxicology studies supporting commercial IND or marketing applications, submitted with the nonclinical PDF study report. [sdTCG](https://www.fda.gov/media/153632/download) | Turn recommendations into visible preflight checks. Let a user document a meaningful exception in the nSDRG instead of silently suppressing it. |
| CDISC convention | SENDIG organizes nonclinical datasets. CDISC conformance rules test whether datasets conform to a published SENDIG. These are implementation rules. They become submission-critical only when the applicable FDA Catalog requires that standard/version. [CDISC SEND primer](https://www.cdisc.org/standards/foundational/send/primer), [CDISC SEND Conformance Rules](https://www.cdisc.org/standards/foundational/send/send-conformance-rules-v3-0) | Keep the mapping and conformance engine versioned. Show its rule source and version beside every result. |
| eCTD and ICH structure | FDA says eCTD is the standard application, amendment, supplement, and report format for CDER and CBER, using the Catalog-supported version. ICH M4S organizes nonclinical study reports in CTD Module 4. [FDA eCTD resources](https://www.fda.gov/drugs/electronic-regulatory-submission-and-review/ectd-resources), [ICH M4S](https://database.ich.org/sites/default/files/M4S_R2_Guideline.pdf) | Treat report authoring, SEND export, define.xml, nSDRG, and eCTD packaging as linked deliverables. A Word-like report template is not itself an FDA template. |

## Required procedure for an in-scope study

1. Freeze the study input manifest. Record the protocol version, source-system export checksum, authority, lock status, and study-start date. Preserve links to the GLP raw data. Under Part 58, automated data changes must retain the original, reason, date, and responsible individual.
2. Map source records to a versioned SEND model. Use the Catalog snapshot to choose the required SENDIG, controlled terminology, and Define-XML version. SEND scope depends on the study and application context. A 28-day repeat-dose study supporting a commercial IND is normally in the type of general toxicology work FDA describes as requiring SEND.
3. Generate report values only from approved, versioned mappings. Every numeric claim needs a stable source pointer and a representation of its grain. The report should never be the only place a calculation lives.
4. Run three labeled validation layers. First run CDISC conformance rules. Then run FDA eCTD technical-rejection and Business Rules. Finally run product reconciliation checks between raw data, SEND, tables, and report prose. FDA recommends fixing discrepancies or explaining meaningful ones in the relevant reviewer guide. [sdTCG, section 8](https://www.fda.gov/media/153632/download)
5. Produce the supporting submission artifacts. A SEND package needs a functioning `define.xml`; FDA says each nonclinical study should have a separate SEND data-definition file. The nSDRG is a PDF named `nsdrg.pdf`; it explains special considerations, discrepancies, creation, verification, and traceability. [sdTCG, sections 2.2 and 4.1.4.5](https://www.fda.gov/media/153632/download)
6. Package and preflight in the current eCTD format. Confirm path, lowercase naming, study tagging or document-type keyword, Trial Summary, report, datasets, `define.xml`, nSDRG, and all required leaf metadata. eCTD technical rejection criteria operate during FDA inbound processing. [eCTD submission standards](https://www.fda.gov/drugs/electronic-regulatory-submission-and-review/ectd-submission-standards-ectd-v322-and-regional-m1)
7. Collect human approvals and retain the evidence. A study director signs and dates the final report. Corrections after finalization must be an identified, signed, dated amendment. QAU retains its own required role. [21 CFR 58.185](https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-58/subpart-J/section-58.185)

## Validation design for the synthetic end-to-end prototype

The prototype should simulate, never claim, an FDA submission. Label every record `SYNTHETIC / NOT FOR SUBMISSION`.

| Validation layer | Synthetic check | Status shown in UI |
| --- | --- | --- |
| Source integrity | Manifest checksum, locked-source state, immutable source ID, row provenance | `source verified` or `source blocked` |
| Study design and grain | Animal identity, sex, dose group, time point, specimen and endpoint agree with the protocol and intended grain | `mapping error` with the conflicting rows |
| SEND conformance | Required variables, controlled terminology, date representation, key uniqueness, datatype, cross-domain reference | `SEND rule error` or `SEND warning` |
| Report reconciliation | Table and prose values match the derived SEND and source records; expected group and unit match | `report mismatch` with source and report locations |
| Submission metadata | `define.xml`, nSDRG, Trial Summary, file naming, eCTD location and tags are present | `package blocked` |
| Human review | Pathologist and QA disposition every alert. Study director signs the locked final report. | `ready for signature`, never `FDA approved` |

Two deliberately injected defects make the prototype honest and useful. First, a body-weight table can show `n=10` where the report field requires sex-stratified `n=5`. Second, a microscopic finding can have a report severity that disagrees with the synthetic MI record. Both should block final assembly until corrected or formally resolved with a reason and reviewer identity.

## Product controls worth keeping

- Preserve an append-only event log for ingest, mapping, validation, manual edit, review, signature, and export.
- Bind report fields to source record IDs and derived-calculation IDs. Provide a click-through evidence drawer rather than relying on a prose footnote.
- Separate automation output from scientific interpretation. HELIX may draft text from verified values, but a qualified person owns interpretation and the final signed report.
- Version the template, mapping, controlled terminology, rule bundle, catalog snapshot, and submission build. A historical study must remain reproducible after standards change.
- Model dispositions as `open`, `corrected`, `explained in nSDRG`, or `approved exception`. Do not use a generic green check for every non-error.

## Important corrections to the supplied concept

- "Every data point must trace to raw data" is a strong and sensible product objective. Part 58 instead specifies control of data creation and changes, report contents, archive access, and retention. HELIX should describe raw-data linkage as its implementation of those obligations, not as a verbatim regulatory sentence.
- SEND is not automatically required for every nonclinical study. The Catalog, study start date, study purpose, application type, and SEND scope determine the outcome.
- FDA does not prescribe one report `docx` template or one nSDRG template. The sdTCG says FDA prefers but does not require the referenced example nSDRG template.
- Technical validation does not evaluate scientific correctness. FDA's sample-data process says validation addresses conformance and not scientific review. [FDA sample-submission process](https://www.fda.gov/drugs/electronic-regulatory-submission-and-review/submit-standardized-data-sample-fda)

throughput checkpoint: n/a, read-only investigation
