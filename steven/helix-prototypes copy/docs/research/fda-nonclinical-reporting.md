# FDA-aligned nonclinical report workflow

Research date: 2026-09-22.

This note defines the regulatory boundaries for the HELIX synthetic prototype. It is not legal advice. It does not certify Part 11 compliance, GLP compliance, SEND conformance, eCTD acceptance, or scientific validity.

## What the regulations require

A GLP final report is a controlled study record, not a free-form narrative. [21 CFR 58.185](https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-58/subpart-J/section-58.185) requires a final report for each nonclinical laboratory study. The report must cover these items:

1. The testing facility and study dates.
2. Protocol objectives, procedures, and changes.
3. Statistical methods.
4. Test and control article identity and characteristics.
5. Test and control article stability under administration conditions.
6. Methods.
7. The test system, including animal count, sex, weight range, source, species, strain, age, and identification method when applicable.
8. Dose, regimen, route, and duration.
9. Circumstances that may have affected data quality or integrity.
10. The study director and other responsible scientific and supervisory personnel.
11. Data transformations, calculations, summaries, analyses, and conclusions.
12. Signed and dated contributor reports.
13. Storage locations for specimens, raw data, and the final report.
14. The signed Quality Assurance Unit statement.

The study director signs and dates the final report. A later correction or addition is a signed and dated amendment that identifies the affected report part and the reason. HELIX must not overwrite a signed final report.

[21 CFR 58.130](https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-58/subpart-G/section-58.130) requires data changes to preserve the original entry and record the reason, date, and responsible person. [21 CFR 58.35](https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-58/subpart-B/section-58.35) makes the Quality Assurance Unit independent of study conduct. The Quality Assurance Unit reviews whether the final report reflects the raw data and prepares the signed inspection statement. [21 CFR 58.190](https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-58/subpart-J/section-58.190) requires indexed archives and controlled retrieval of raw data, protocols, specimens, and reports.

If Part 11 applies to the production system's electronic records, [21 CFR 11.10](https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-11/subpart-B/section-11.10) calls for system validation, accurate copies, record protection, access controls, secure time-stamped audit trails, sequencing checks, and authority checks. [21 CFR 11.50](https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-11/subpart-C/section-11.50) requires a signed electronic record to show the signer, signing time, and signature meaning. This prototype records those concepts but is not a validated Part 11 system.

## What the 28-day study guideline adds

The current [OECD Test Guideline 407](https://www.oecd.org/en/publications/test-no-407-repeated-dose-28-day-oral-toxicity-study-in-rodents_9789264070684-en.html), adopted on 2025-06-25 and corrected on 2025-09-18, defines the study-specific observations and report content for a 28-day oral rodent study. It calls for individual data and group summaries. Expected result areas include clinical observations, body weight, food and water consumption when applicable, hematology, clinical chemistry, organ weights, gross necropsy, and histopathology. Results are reported by sex and dose level. The report also describes the test chemical, vehicle, test animals, housing, study conditions, dose administration, statistical treatment, and discussion.

HELIX therefore uses a sponsor template with typed required fields. It does not present one document as an FDA-issued Word template. The structured template combines the required final-report contents in 21 CFR 58.185 with the endpoint detail in OECD TG 407.

## How submission data relates to the report

The June 2026 [FDA Study Data Technical Conformance Guide](https://www.fda.gov/media/153632/download) states that SEND organizes nonclinical tabulation datasets. The report and SEND data must remain traceable to the original data and consistent with each other. Each submitted SEND dataset needs complete metadata in `define.xml`. An `nsdrg.pdf` accompanies nonclinical study data when appropriate and explains implementation details, conformance issues, discrepancies, creation, verification, and traceability.

SEND applicability is contextual. The guide says that single-dose and repeat-dose general toxicology studies that support a commercial IND or marketing authorization require SEND. The FDA Data Standards Catalog, study start date, Center, application type, and study purpose determine the applicable standard and version. HELIX must store that context instead of hard-coding one SEND version.

The March 2025 [FDA Data Standards Catalog](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/data-standards-catalog), version 11.0, lists supported SEND, Define-XML, and eCTD versions and their requirement dates. The FDA [Study Data for Submission to CDER and CBER](https://www.fda.gov/industry/study-data-standards-resources/study-data-submission-cder-and-cber) page says that the format supported at the study start date governs the submission.

FDA recommends three technical checks before submission:

1. Run the applicable standards development organization conformance rules.
2. Run FDA business rules and eCTD technical rejection checks.
3. Correct discrepancies or explain meaningful discrepancies in the reviewer guide.

Appendix I of the June 2026 guide adds a direct reconciliation expectation. SEND analyses should match the study report, SEND should trace to raw data and the report, and unresolved anomalies should be described in the nSDRG. Technical validation does not replace scientific review.

## Where the artifacts go

[ICH M4S(R2)](https://database.ich.org/sites/default/files/M4S_R2_Guideline.pdf) organizes nonclinical study reports in CTD Module 4. Repeat-dose toxicity reports sit under Module `4.2.3.2`, ordered by species, route, and duration. M4S defines dossier organization. It does not define a universal sponsor report layout.

The FDA technical guide describes eCTD placement and metadata rules. It also keeps the report, SEND datasets, `define.xml`, and `nsdrg.pdf` as linked but distinct artifacts. A prepared package is not an accepted submission. The prototype labels export as synthetic and never displays `FDA approved`.

## HELIX workflow boundary

The supplied operating process has six source systems, report authoring, peer review, a Quality Assurance Unit audit, finalization, SEND preparation, and archival. Laboratories may implement those operations differently. The defensible common workflow is:

1. Authorize and freeze the exact protocol, template, source exports, and reference versions.
2. Parse external files into typed study records without altering the originals.
3. Resolve the study type, report template, FDA Catalog context, and applicable standard versions.
4. Use deterministic code for extraction, calculations, controlled terminology, and reconciliation.
5. Let an LLM locate evidence, propose allowlisted checks, and draft prose around validated claims. The LLM cannot perform authoritative calculations or downgrade a failed rule.
6. Bind each quantitative claim to source records, a versioned transform, and validation results.
7. Block incomplete sections and release while required evidence, dispositions, reviews, signatures, or package metadata remain open.
8. Keep scientific interpretation, adversity, biological relevance, NOAEL selection, Quality Assurance Unit work, and final approval with qualified people.
9. Export only after a separate explicit action. Record checksums and an append-only export event.

The source specification's five-to-six-week authoring estimate remains a product hypothesis. No FDA source sets that duration.

## Structured output used by the prototype

The report template stores these items for each field:

- `field_id` and section ownership.
- Required or optional status.
- Expected grain.
- Source expectation.
- Human-judgment status.
- Regulatory references.

Claims separately store current values, units, review status, and provenance edges. The release package stores the report, illustrative dataset archive, `define.xml`, `nsdrg.pdf`, the rule-bundle version, approvals, dispositions, and export checksums. The package, interface, and generated artifacts carry `SYNTHETIC / NOT FOR SUBMISSION`.
