"""Strict, identifier-free WP06 legacy-client compatibility results."""

from __future__ import annotations

import json
from enum import StrEnum, unique
from typing import Annotated, ClassVar, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .wp06_contract_schema_rules import (
    FORMAT_VERSION_BEFORE_VALIDATOR,
    LEGACY_CLIENT_RESULT_SCHEMA_RULES,
)

SCHEMA_ID: Final = "urn:zcash:privacy-stack:wp06-legacy-client-result:1"
SCHEMA_TITLE: Final = "WP06 Legacy Client Result"
NonEmptyString = Annotated[str, Field(min_length=1)]


@unique
class Client(StrEnum):
    """Supported legacy client lanes."""

    VIZOR = "vizor"
    ZODL_ANDROID = "zodl-android"
    ZODL_IOS = "zodl-ios"


@unique
class Scenario(StrEnum):
    """WP06 compatibility scenarios in registry order."""

    TEMPORARY_PUBLIC_ABSENCE = "temporary_public_absence"
    EXACT_RETRY = "exact_retry"
    LOST_RESPONSE_RETRY = "lost_response_retry"
    TRANSACTION_STATUS_RECONCILIATION = "transaction_status_reconciliation"
    MEMPOOL_OBSERVATION = "mempool_observation"
    SERVER_SWITCHING = "server_switching"
    DIRECT_FALLBACK = "direct_fallback"
    NODE_RESTART = "node_restart"
    PRE_RELEASE_CONFLICT = "pre_release_conflict"
    RELEASE_DEADLINE_PRESERVATION = "release_deadline_preservation"


SCENARIO_REGISTRY: Final[tuple[Scenario, ...]] = tuple(Scenario)


@unique
class EvidenceGrade(StrEnum):
    """Strength and availability of the recorded evidence."""

    LOCAL_RUST_UNIT = "local_rust_unit"
    LOCAL_FLUTTER_UNAVAILABLE = "local_flutter_unavailable"
    SOURCE_DERIVED = "source_derived"
    INTEGRATED_EMPIRICAL = "integrated_empirical"
    UNAVAILABLE = "unavailable"


@unique
class UnavailableReason(StrEnum):
    """Stable unavailable states for planned WP06 adapter lanes."""

    VIZOR_CHECKOUT_UNAVAILABLE = "vizor_checkout_unavailable"
    VIZOR_REVISION_MISMATCH = "vizor_revision_mismatch"
    VIZOR_WORKTREE_DIRTY = "vizor_worktree_dirty"
    VIZOR_ORIGIN_MISMATCH = "vizor_origin_mismatch"
    CARGO_UNAVAILABLE = "cargo_unavailable"
    FLUTTER_TOOLCHAIN_UNAVAILABLE = "flutter_toolchain_unavailable"
    MANAGED_ZCASHD_UNAVAILABLE_ON_DARWIN_ARM64 = "managed_zcashd_unavailable_on_darwin_arm64"


@unique
class Execution(StrEnum):
    """Whether the selected evidence collection, including source review, completed."""

    COMPLETE = "complete"
    UNAVAILABLE = "unavailable"


@unique
class RolloutClassification(StrEnum):
    """Conservative WP06 endpoint rollout classification."""

    ORDINARY_IMMEDIATE_ENDPOINT = "ordinary_immediate_endpoint"
    PRIVATE_ENDPOINT_ONLY = "private_endpoint_only"
    INCONCLUSIVE = "inconclusive"
    INCOMPATIBLE = "incompatible"


@unique
class CheckCode(StrEnum):
    """Fixed compatibility checks that never carry unstructured evidence."""

    CLIENT_BEHAVIOR = "client_behavior"
    DUPLICATE_RELEASE = "duplicate_release"
    RELEASE_DEADLINE = "release_deadline"
    DIRECT_FALLBACK = "direct_fallback"
    STATUS_POLLING = "status_polling"


@unique
class CheckStatus(StrEnum):
    """Outcome for one fixed compatibility check."""

    PASS = "pass"  # noqa: S105
    FAIL = "fail"
    NOT_RUN = "not_run"


@unique
class TimelineEventCode(StrEnum):
    """The seven human-inspection stages required by WP06."""

    SUBMISSION_CALL = "submission_call"
    SERVER_ACCEPTANCE = "server_acceptance"
    CLIENT_VISIBLE_RESPONSE = "client_visible_response"
    CLIENT_RETRIES_OR_STATUS_QUERIES = "client_retries_or_status_queries"
    PUBLIC_RELEASE = "public_release"
    CLIENT_FINAL_STATE = "client_final_state"
    FALLBACK_OR_ENDPOINT_CHANGE = "fallback_or_endpoint_change"


class InvariantCode(StrEnum):
    """Stable machine-readable cross-field validation failures."""

    UNAVAILABLE_REASON_REQUIRED = "unavailable_reason_required"
    UNAVAILABLE_CHECKS_MUST_BE_NOT_RUN = "unavailable_checks_must_be_not_run"
    UNAVAILABLE_TIMELINE_FORBIDDEN = "unavailable_timeline_forbidden"
    UNAVAILABLE_ROLLOUT_MUST_BE_INCONCLUSIVE = "unavailable_rollout_must_be_inconclusive"
    COMPLETE_REASON_FORBIDDEN = "complete_reason_forbidden"
    UNAVAILABLE_EVIDENCE_REQUIRES_UNAVAILABLE_EXECUTION = (
        "unavailable_evidence_requires_unavailable_execution"
    )
    EVIDENCE_CANNOT_AUTHORIZE_PRIVATE_ENDPOINT = "evidence_cannot_authorize_private_endpoint"


class _ContractRecord(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid", strict=True)


class CheckRecord(_ContractRecord):
    """One typed check result without free-form evidence data."""

    code: CheckCode
    status: CheckStatus

    @property
    def is_not_run(self) -> bool:
        """Return whether this check was not run."""
        match self.status:
            case CheckStatus.NOT_RUN:
                return True
            case CheckStatus.PASS | CheckStatus.FAIL:
                return False


class TimelineRecord(_ContractRecord):
    """One typed WP06 timeline stage."""

    code: TimelineEventCode


class LegacyClientResult(_ContractRecord):
    """The complete immutable WP06 result for one client-version scenario."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        title=SCHEMA_TITLE,
        json_schema_extra={
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": SCHEMA_ID,
            "allOf": list(LEGACY_CLIENT_RESULT_SCHEMA_RULES),
        },
    )

    format_version: Annotated[Literal[1], FORMAT_VERSION_BEFORE_VALIDATOR] = 1
    client: Client
    client_release: NonEmptyString
    scenario: Scenario
    evidence_grade: EvidenceGrade
    execution: Execution
    rollout_classification: RolloutClassification
    checks: Annotated[tuple[CheckRecord, ...], Field(min_length=1)]
    timeline: tuple[TimelineRecord, ...]
    unavailable_reason: UnavailableReason | None = None

    @model_validator(mode="after")
    def validate_invariants(self) -> LegacyClientResult:
        """Reject result combinations that overstate executable evidence."""
        _validate_execution(self)
        _validate_evidence(self)
        return self


def _validate_execution(result: LegacyClientResult) -> None:
    match result.execution:
        case Execution.UNAVAILABLE:
            _validate_unavailable_result(result)
        case Execution.COMPLETE:
            match result.unavailable_reason:
                case None:
                    pass
                case UnavailableReason():
                    raise ValueError(InvariantCode.COMPLETE_REASON_FORBIDDEN)


def _validate_unavailable_result(result: LegacyClientResult) -> None:
    match result.unavailable_reason:
        case UnavailableReason():
            pass
        case None:
            raise ValueError(InvariantCode.UNAVAILABLE_REASON_REQUIRED)
    if not all(check.is_not_run for check in result.checks):
        raise ValueError(InvariantCode.UNAVAILABLE_CHECKS_MUST_BE_NOT_RUN)
    if result.timeline:
        raise ValueError(InvariantCode.UNAVAILABLE_TIMELINE_FORBIDDEN)
    match result.rollout_classification:
        case RolloutClassification.INCONCLUSIVE:
            pass
        case (
            RolloutClassification.ORDINARY_IMMEDIATE_ENDPOINT
            | RolloutClassification.PRIVATE_ENDPOINT_ONLY
            | RolloutClassification.INCOMPATIBLE
        ):
            raise ValueError(InvariantCode.UNAVAILABLE_ROLLOUT_MUST_BE_INCONCLUSIVE)


def _validate_evidence(result: LegacyClientResult) -> None:
    match result.evidence_grade:
        case EvidenceGrade.LOCAL_FLUTTER_UNAVAILABLE | EvidenceGrade.UNAVAILABLE:
            match result.execution:
                case Execution.UNAVAILABLE:
                    pass
                case Execution.COMPLETE:
                    raise ValueError(
                        InvariantCode.UNAVAILABLE_EVIDENCE_REQUIRES_UNAVAILABLE_EXECUTION
                    )
        case EvidenceGrade.LOCAL_RUST_UNIT | EvidenceGrade.SOURCE_DERIVED:
            match result.rollout_classification:
                case RolloutClassification.PRIVATE_ENDPOINT_ONLY:
                    raise ValueError(InvariantCode.EVIDENCE_CANNOT_AUTHORIZE_PRIVATE_ENDPOINT)
                case (
                    RolloutClassification.ORDINARY_IMMEDIATE_ENDPOINT
                    | RolloutClassification.INCONCLUSIVE
                    | RolloutClassification.INCOMPATIBLE
                ):
                    pass
        case EvidenceGrade.INTEGRATED_EMPIRICAL:
            pass


def render_result(result: LegacyClientResult) -> str:
    """Render one result as deterministically ordered compact JSON."""
    return json.dumps(result.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
