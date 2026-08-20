"""Pinned WP06 evidence adapters for Vizor and Zodl clients."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from scripts.wp06_legacy_client_adapter_runtime import (
    VIZOR_PIN,
    ZODL_ANDROID_PIN,
    ZODL_IOS_PIN,
    AdapterRuntime,
    ClientPin,
    run_vizor_cargo_evidence,
)
from scripts.wp06_legacy_client_contract import (
    SCENARIO_REGISTRY,
    CheckCode,
    CheckRecord,
    CheckStatus,
    Client,
    EvidenceGrade,
    Execution,
    LegacyClientResult,
    RolloutClassification,
    Scenario,
    TimelineEventCode,
    TimelineRecord,
    UnavailableReason,
)
from scripts.wp06_zodl_source_evidence import (
    ZODL_ANDROID_SOURCE_MAPPING,
    ZODL_IOS_SOURCE_MAPPING,
    ZodlScenarioMapping,
)

if TYPE_CHECKING:
    from pathlib import Path

LocalRustScenario = Literal[
    Scenario.EXACT_RETRY,
    Scenario.LOST_RESPONSE_RETRY,
    Scenario.TRANSACTION_STATUS_RECONCILIATION,
    Scenario.MEMPOOL_OBSERVATION,
]


def build_vizor_results(checkout: Path, runtime: AdapterRuntime) -> tuple[LegacyClientResult, ...]:
    """Run pinned Vizor Rust evidence and return the ordered matrix."""
    run_vizor_cargo_evidence(checkout, runtime)
    return tuple(_vizor_result(scenario) for scenario in SCENARIO_REGISTRY)


def build_zodl_android_results() -> tuple[LegacyClientResult, ...]:
    """Return the pinned Zodl Android source-review matrix."""
    return _zodl_results(Client.ZODL_ANDROID, ZODL_ANDROID_PIN, ZODL_ANDROID_SOURCE_MAPPING)


def build_zodl_ios_results() -> tuple[LegacyClientResult, ...]:
    """Return the pinned Zodl iOS source-review matrix."""
    return _zodl_results(Client.ZODL_IOS, ZODL_IOS_PIN, ZODL_IOS_SOURCE_MAPPING)


def _vizor_result(scenario: Scenario) -> LegacyClientResult:
    match scenario:
        case (
            Scenario.EXACT_RETRY
            | Scenario.LOST_RESPONSE_RETRY
            | Scenario.TRANSACTION_STATUS_RECONCILIATION
            | Scenario.MEMPOOL_OBSERVATION
        ):
            return _complete_vizor(scenario)
        case Scenario.SERVER_SWITCHING | Scenario.DIRECT_FALLBACK:
            return _unavailable_vizor(
                scenario,
                EvidenceGrade.LOCAL_FLUTTER_UNAVAILABLE,
                UnavailableReason.FLUTTER_TOOLCHAIN_UNAVAILABLE,
            )
        case (
            Scenario.TEMPORARY_PUBLIC_ABSENCE
            | Scenario.NODE_RESTART
            | Scenario.PRE_RELEASE_CONFLICT
            | Scenario.RELEASE_DEADLINE_PRESERVATION
        ):
            return _unavailable_vizor(
                scenario,
                EvidenceGrade.UNAVAILABLE,
                UnavailableReason.MANAGED_ZCASHD_UNAVAILABLE_ON_DARWIN_ARM64,
            )


def _complete_vizor(scenario: LocalRustScenario) -> LegacyClientResult:
    return LegacyClientResult(
        client=Client.VIZOR,
        client_release=VIZOR_PIN.release,
        scenario=scenario,
        evidence_grade=EvidenceGrade.LOCAL_RUST_UNIT,
        execution=Execution.COMPLETE,
        rollout_classification=RolloutClassification.ORDINARY_IMMEDIATE_ENDPOINT,
        checks=(CheckRecord(code=_check_code(scenario), status=CheckStatus.PASS),),
        timeline=_local_timeline(scenario),
    )


def _local_timeline(scenario: LocalRustScenario) -> tuple[TimelineRecord, ...]:
    retry = TimelineRecord(code=TimelineEventCode.CLIENT_RETRIES_OR_STATUS_QUERIES)
    final = TimelineRecord(code=TimelineEventCode.CLIENT_FINAL_STATE)
    match scenario:
        case Scenario.EXACT_RETRY | Scenario.LOST_RESPONSE_RETRY:
            return (
                TimelineRecord(code=TimelineEventCode.SUBMISSION_CALL),
                TimelineRecord(code=TimelineEventCode.CLIENT_VISIBLE_RESPONSE),
                retry,
                final,
            )
        case Scenario.TRANSACTION_STATUS_RECONCILIATION | Scenario.MEMPOOL_OBSERVATION:
            return (retry, final)


def _unavailable_vizor(
    scenario: Scenario, evidence: EvidenceGrade, reason: UnavailableReason
) -> LegacyClientResult:
    return LegacyClientResult(
        client=Client.VIZOR,
        client_release=VIZOR_PIN.release,
        scenario=scenario,
        evidence_grade=evidence,
        execution=Execution.UNAVAILABLE,
        rollout_classification=RolloutClassification.INCONCLUSIVE,
        checks=(CheckRecord(code=_check_code(scenario), status=CheckStatus.NOT_RUN),),
        timeline=(),
        unavailable_reason=reason,
    )


def _zodl_results(
    client: Client, pin: ClientPin, mappings: tuple[ZodlScenarioMapping, ...]
) -> tuple[LegacyClientResult, ...]:
    return tuple(
        LegacyClientResult(
            client=client,
            client_release=pin.release,
            scenario=mapping.scenario,
            evidence_grade=EvidenceGrade.SOURCE_DERIVED,
            execution=Execution.COMPLETE,
            rollout_classification=RolloutClassification.INCONCLUSIVE,
            checks=(CheckRecord(code=mapping.check_code, status=mapping.check_status),),
            timeline=(),
        )
        for mapping in mappings
    )


def _check_code(scenario: Scenario) -> CheckCode:
    match scenario:
        case Scenario.EXACT_RETRY:
            return CheckCode.DUPLICATE_RELEASE
        case Scenario.TRANSACTION_STATUS_RECONCILIATION | Scenario.MEMPOOL_OBSERVATION:
            return CheckCode.STATUS_POLLING
        case Scenario.DIRECT_FALLBACK:
            return CheckCode.DIRECT_FALLBACK
        case Scenario.RELEASE_DEADLINE_PRESERVATION:
            return CheckCode.RELEASE_DEADLINE
        case (
            Scenario.TEMPORARY_PUBLIC_ABSENCE
            | Scenario.LOST_RESPONSE_RETRY
            | Scenario.SERVER_SWITCHING
            | Scenario.NODE_RESTART
            | Scenario.PRE_RELEASE_CONFLICT
        ):
            return CheckCode.CLIENT_BEHAVIOR
