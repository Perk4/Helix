from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from .body_weight import (
    EXECUTOR_ID,
    EXECUTOR_VERSION,
    FIXTURE_PATH,
    OUTPUT_GRAIN,
    PACKAGE_ID,
    PACKAGE_VERSION,
    RULES,
    SOURCE_ARTIFACT_ID,
    TERMINAL_CLAIM_ID,
    BodyWeightComputation,
    compute_body_weight_summary,
    file_hash,
    load_frozen_fixture,
    load_section_consumers,
    provenance_failures,
    recompute_matches_fixture,
)
from .models import DataValidationRunRow
from .repository import StudyPackageRepository
from .run_plans import PinnedRunService, canonical_hash
from .schemas import (
    Claim,
    DataValidationCommand,
    DataValidationExecution,
    DataValidationReceipt,
    DataValidationRuleResult,
    FreezeRunCommand,
    PinnedRun,
    ProvenanceEdge,
    SectionClaimReference,
    StudyEvidencePackage,
    ValidationResult,
    ValidationStatus,
    WorkflowEvent,
)

PACKAGE_RELATIVE = Path("skills/helix-evidence-pipeline/packages/data-validation/body-weight/package.json")
EXECUTOR_RELATIVE = Path("backend/app/body_weight.py")


class DataValidationConflictError(RuntimeError):
    pass


class UnknownValidationPackageError(ValueError):
    pass


class DataValidationService:
    def __init__(self, session: Session, pinned_runs: PinnedRunService, repository_root: Path):
        self.session = session
        self.pinned_runs = pinned_runs
        self.repository_root = repository_root.resolve()
        self.repository = StudyPackageRepository(session)

    def execute(self, study_id: str, command: DataValidationCommand) -> DataValidationExecution:
        if command.package_id != PACKAGE_ID:
            raise UnknownValidationPackageError(f"Unknown Data Validation Package {command.package_id}")
        package = self.repository.get(study_id)
        if package.pinned_run is None:
            self.pinned_runs.freeze(
                study_id,
                FreezeRunCommand(
                    actor=command.actor,
                    idempotency_key=f"dvp-freeze-{study_id}",
                ),
            )
            package = self.repository.get(study_id)
        pinned = package.pinned_run
        if pinned is None:
            raise DataValidationConflictError("Freeze the authorized manifest first")
        if pinned.status != "planned":
            raise DataValidationConflictError("The Pinned Run requires study-type review")
        node = next((item for item in pinned.run_plan.nodes if item.node_id == PACKAGE_ID), None)
        if node is None or node.status == "blocked":
            raise DataValidationConflictError("validation.body_weight is not executable in this Pinned Run")

        prior = self.repository.get_data_validation_run(study_id, command.idempotency_key)
        if prior is not None:
            if prior.run_id != pinned.run_id or prior.package_id != command.package_id:
                raise DataValidationConflictError("The idempotency key was already used for another command")
            return self._replay(prior)

        existing = self.repository.get_data_validation_for_run(study_id, pinned.run_id, command.package_id)
        if existing is not None:
            self.repository.add_data_validation_alias(
                existing,
                idempotency_key=command.idempotency_key,
            )
            self.session.commit()
            return self._replay(existing)

        package = self.repository.get(study_id, for_update=True)
        pinned = package.pinned_run
        if pinned is None:
            raise DataValidationConflictError("Freeze the authorized manifest first")
        existing = self.repository.get_data_validation_for_run(study_id, pinned.run_id, command.package_id)
        if existing is not None:
            self.repository.add_data_validation_alias(existing, idempotency_key=command.idempotency_key)
            self.session.commit()
            return self._replay(existing)

        execution = self._run(package, pinned, command)
        stored = execution.model_copy(
            update={"receipt": execution.receipt.model_copy(update={"idempotent_replay": False})}
        )
        updated = self._persist_execution(package, stored)
        self.repository.save(updated)
        self.repository.add_data_validation_run(
            study_id=study_id,
            run_id=pinned.run_id,
            package_id=command.package_id,
            idempotency_key=command.idempotency_key,
            execution=stored,
        )
        self.repository.append_event(
            study_id=study_id,
            event_type=stored.event.event,
            actor=stored.event.actor,
            payload={"outcome": stored.event.outcome, **stored.event.details},
            idempotency_key=f"dvp:{pinned.run_id}:{command.package_id}",
            occurred_at=datetime.fromisoformat(stored.event.timestamp.replace("Z", "+00:00")),
        )
        self.session.commit()
        return stored

    def _run(
        self,
        package: StudyEvidencePackage,
        pinned: PinnedRun,
        command: DataValidationCommand,
    ) -> DataValidationExecution:
        computation = compute_body_weight_summary(package)
        fixture = load_frozen_fixture(self.repository_root)
        results = self._rule_results(computation, fixture)
        blocked = any(
            result.status == ValidationStatus.FAIL and result.enforcement_class == "hard_blocker"
            for result in results
        )
        claims = [] if blocked else computation.claims
        edges = [] if blocked else computation.provenance_edges
        created_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        receipt_seed = canonical_hash(
            {
                "run_id": pinned.run_id,
                "package_id": PACKAGE_ID,
                "package_hash": file_hash(self.repository_root / PACKAGE_RELATIVE),
                "executor_hash": file_hash(self.repository_root / EXECUTOR_RELATIVE),
                "claim_ids": [claim.claim_id for claim in claims],
                "result_ids": [result.result_id for result in results],
            }
        )
        event_id = f"EV-DVP-{receipt_seed.removeprefix('sha256:')[16:28].upper()}"
        receipt = DataValidationReceipt(
            receipt_id=f"RCP-DVP-{receipt_seed.removeprefix('sha256:')[:16].upper()}",
            run_id=pinned.run_id,
            package_id=PACKAGE_ID,
            package_version=PACKAGE_VERSION,
            package_hash=file_hash(self.repository_root / PACKAGE_RELATIVE),
            node_id=PACKAGE_ID,
            executor_id=EXECUTOR_ID,
            executor_version=EXECUTOR_VERSION,
            executor_hash=file_hash(self.repository_root / EXECUTOR_RELATIVE),
            rule_bundle_id=PACKAGE_ID,
            rule_ids=[rule_id for rule_id, _, _ in RULES],
            source_artifact_id=SOURCE_ARTIFACT_ID,
            source_hash=self._source_hash(package),
            governed_versions=pinned.run_plan.governed_versions,
            input_fingerprint=self._input_fingerprint(pinned),
            claim_ids=[claim.claim_id for claim in claims],
            result_ids=[result.result_id for result in results],
            event_id=event_id,
            status="blocked" if blocked else "passed",
            idempotent_replay=False,
        )
        event = WorkflowEvent(
            event_id=event_id,
            event="data_validation_completed",
            actor=command.actor,
            timestamp=created_at,
            outcome=receipt.status,
            details={
                "run_id": pinned.run_id,
                "package_id": PACKAGE_ID,
                "receipt_id": receipt.receipt_id,
                "executor_id": EXECUTOR_ID,
                "source_artifact_id": SOURCE_ARTIFACT_ID,
            },
        )
        references = [
            SectionClaimReference(
                section_id=section_id,
                section_package_id=section_package_id,
                title=title,
                claim_id=TERMINAL_CLAIM_ID,
                executor_receipt_id=receipt.receipt_id,
            )
            for section_id, section_package_id, title in load_section_consumers(self.repository_root)
            if TERMINAL_CLAIM_ID in receipt.claim_ids
        ]
        return DataValidationExecution(
            receipt=receipt,
            claims=claims,
            results=results,
            provenance_edges=edges,
            section_references=references,
            event=event,
        )

    def _rule_results(
        self,
        computation: BodyWeightComputation,
        fixture: dict[str, object],
    ) -> list[DataValidationRuleResult]:
        matched, recompute_evidence = recompute_matches_fixture(computation, fixture)
        provenance_evidence = provenance_failures(computation)
        grain_ids = [issue.record_id for issue in computation.grain_issues]
        checks = [
            (
                "VR-BW-GRAIN",
                "body-weight-required-grain",
                "1.0.0",
                not computation.grain_issues,
                grain_ids or [OUTPUT_GRAIN],
                (
                    "Every body-weight record has grain and projects to study_day × sex × dose_group."
                    if not computation.grain_issues
                    else (
                        f"{len(computation.grain_issues)} body-weight records are missing grain "
                        "or a provenance edge required to project study_day × sex × dose_group."
                    )
                ),
            ),
            (
                "VR-BW-RECOMPUTE",
                "body-weight-summary-recompute",
                "1.0.0",
                matched,
                recompute_evidence or [TERMINAL_CLAIM_ID, str(FIXTURE_PATH)],
                (
                    "Recomputed body-weight summaries match the frozen fixture."
                    if matched
                    else "Recomputed body-weight summaries do not match the frozen fixture."
                ),
            ),
            (
                "VR-BW-PROVENANCE",
                "body-weight-cell-provenance",
                "1.0.0",
                not provenance_evidence,
                provenance_evidence or [edge.edge_id for edge in computation.provenance_edges[:12]],
                (
                    "Every numeric body-weight claim has complete hashes, transforms, and edges."
                    if not provenance_evidence
                    else "A body-weight claim is missing a provenance edge, source hash, or transform."
                ),
            ),
        ]
        return [
            DataValidationRuleResult(
                result_id=result_id,
                rule_id=rule_id,
                rule_version=rule_version,
                enforcement_class="hard_blocker",
                status=ValidationStatus.PASS if passed else ValidationStatus.FAIL,
                scope_id=PACKAGE_ID if rule_id != "body-weight-summary-recompute" else TERMINAL_CLAIM_ID,
                evidence_ids=evidence_ids,
                message=message,
                waivable=False,
                package_id=PACKAGE_ID,
                executor_id=EXECUTOR_ID,
            )
            for result_id, rule_id, rule_version, passed, evidence_ids, message in checks
        ]

    def _persist_execution(
        self,
        package: StudyEvidencePackage,
        execution: DataValidationExecution,
    ) -> StudyEvidencePackage:
        executions = [
            item
            for item in package.data_validation_executions
            if not (
                item.receipt.run_id == execution.receipt.run_id
                and item.receipt.package_id == execution.receipt.package_id
            )
        ]
        executions.append(execution)
        claims = _upsert_claims(package.claims, execution.claims)
        edges = _upsert_edges(package.provenance_edges, execution.provenance_edges)
        events = [*package.events, execution.event]
        return package.model_copy(
            update={
                "data_validation_executions": executions,
                "claims": claims,
                "provenance_edges": edges,
                "events": events,
            }
        )

    def _replay(self, row: DataValidationRunRow) -> DataValidationExecution:
        execution = DataValidationExecution.model_validate(row.execution)
        return execution.model_copy(
            update={"receipt": execution.receipt.model_copy(update={"idempotent_replay": True})}
        )

    @staticmethod
    def _source_hash(package: StudyEvidencePackage) -> str:
        artifact = next((item for item in package.manifest if item.artifact_id == SOURCE_ARTIFACT_ID), None)
        if artifact is None:
            raise DataValidationConflictError("The pinned run is missing the body-weight source artifact")
        return artifact.checksum

    @staticmethod
    def _input_fingerprint(pinned: PinnedRun) -> str:
        node = next(item for item in pinned.run_plan.nodes if item.node_id == PACKAGE_ID)
        return node.input_fingerprint


def as_validation_results(execution: DataValidationExecution) -> list[ValidationResult]:
    return [
        ValidationResult(
            result_id=result.result_id,
            rule_id=result.rule_id,
            scope_id=result.scope_id,
            severity="blocker" if result.enforcement_class != "warning" else "warning",
            status=result.status,
            evidence_ids=result.evidence_ids,
            message=result.message,
            rule_version=result.rule_version,
            tool_name=result.executor_id,
            enforcement_class=result.enforcement_class,
            waivable=result.waivable,
            package_id=result.package_id,
            executor_id=result.executor_id,
        )
        for result in execution.results
    ]


def _upsert_claims(existing: list[Claim], produced: list[Claim]) -> list[Claim]:
    if not produced:
        return existing
    incoming = {claim.claim_id: claim for claim in produced}
    claims: list[Claim] = []
    seen: set[str] = set()
    for claim in existing:
        replacement = incoming.get(claim.claim_id)
        if replacement is not None:
            claims.append(replacement)
            seen.add(claim.claim_id)
        else:
            claims.append(claim)
    claims.extend(claim for claim in produced if claim.claim_id not in seen)
    return claims


def _upsert_edges(
    existing: list[ProvenanceEdge],
    produced: list[ProvenanceEdge],
) -> list[ProvenanceEdge]:
    if not produced:
        return existing
    produced_ids = {edge.claim_id for edge in produced}
    retained = [edge for edge in existing if edge.claim_id not in produced_ids]
    return [*retained, *produced]
