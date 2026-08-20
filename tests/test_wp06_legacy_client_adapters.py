from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

import pytest
from scripts.wp06_legacy_client_adapter_runtime import (
    VIZOR_PIN,
    ZODL_ANDROID_PIN,
    ZODL_IOS_PIN,
    AdapterError,
    AdapterErrorCode,
    AdapterRuntime,
)
from scripts.wp06_legacy_client_adapters import (
    build_vizor_results,
    build_zodl_android_results,
    build_zodl_ios_results,
)
from scripts.wp06_legacy_client_contract import (
    SCENARIO_REGISTRY,
    CheckCode,
    CheckStatus,
    Client,
    EvidenceGrade,
    Execution,
    LegacyClientResult,
    RolloutClassification,
    Scenario,
    UnavailableReason,
)
from scripts.wp06_vizor_evidence import VIZOR_RUST_EVIDENCE_REGISTRY

from tests.wp06_adapter_fakes import FakeCheckoutState, FixedToolProbe, RecordingRunner

if TYPE_CHECKING:
    from pathlib import Path

VALID_STATE = FakeCheckoutState(revision=VIZOR_PIN.revision, origin=VIZOR_PIN.repository)
CHECKOUT_UNAVAILABLE_STATE = FakeCheckoutState(
    revision=VIZOR_PIN.revision,
    origin=VIZOR_PIN.repository,
    revision_status=1,
)
REVISION_MISMATCH_STATE = FakeCheckoutState(revision="wrong", origin=VIZOR_PIN.repository)
ORIGIN_MISMATCH_STATE = FakeCheckoutState(revision=VIZOR_PIN.revision, origin="wrong")
DIRTY_STATE = FakeCheckoutState(
    revision=VIZOR_PIN.revision,
    origin=VIZOR_PIN.repository,
    status=" M changed",
)
CARGO_FAILURE_STATE = FakeCheckoutState(
    revision=VIZOR_PIN.revision,
    origin=VIZOR_PIN.repository,
    cargo_status=7,
)


def _runtime(state: FakeCheckoutState, cargo: str | None = "/toolchain/cargo") -> AdapterRuntime:
    return AdapterRuntime(command_runner=RecordingRunner(state), tool_probe=FixedToolProbe(cargo))


def test_client_pins_are_exact() -> None:
    assert (VIZOR_PIN.release, VIZOR_PIN.revision, VIZOR_PIN.repository) == (
        "0.0.48",
        "d60ea8ef853d02e6ea31573e75c5603db1d7addb",
        "https://github.com/chainapsis/vizor-wallet",
    )
    assert (ZODL_ANDROID_PIN.release, ZODL_ANDROID_PIN.revision, ZODL_ANDROID_PIN.repository) == (
        "3.9.3-2393",
        "39cf778399dc49e2fa24fe08b9b1cd83adf0fa7f",
        "https://github.com/zodl-inc/zodl-android",
    )
    assert (ZODL_IOS_PIN.release, ZODL_IOS_PIN.revision, ZODL_IOS_PIN.repository) == (
        "3.9.5",
        "993d31f333f6fe118819f5c8464008801c3f8908",
        "https://github.com/zodl-inc/zodl-ios",
    )


def test_vizor_results_have_exact_order_and_evidence_mapping(tmp_path: Path) -> None:
    checkout = tmp_path / "vizor"
    checkout.mkdir()

    results = build_vizor_results(checkout, _runtime(VALID_STATE))

    assert tuple(result.scenario for result in results) == SCENARIO_REGISTRY
    assert Counter(result.evidence_grade for result in results) == {
        EvidenceGrade.LOCAL_RUST_UNIT: 4,
        EvidenceGrade.LOCAL_FLUTTER_UNAVAILABLE: 2,
        EvidenceGrade.UNAVAILABLE: 4,
    }
    assert all(
        LegacyClientResult.model_validate(result.model_dump()) == result for result in results
    )
    complete = {result.scenario for result in results if result.execution is Execution.COMPLETE}
    assert complete == {
        Scenario.EXACT_RETRY,
        Scenario.LOST_RESPONSE_RETRY,
        Scenario.TRANSACTION_STATUS_RECONCILIATION,
        Scenario.MEMPOOL_OBSERVATION,
    }
    assert tuple(
        (result.scenario, result.checks[0].code, result.checks[0].status)
        for result in results
        if result.execution is Execution.COMPLETE
    ) == (
        (Scenario.EXACT_RETRY, CheckCode.DUPLICATE_RELEASE, CheckStatus.PASS),
        (Scenario.LOST_RESPONSE_RETRY, CheckCode.CLIENT_BEHAVIOR, CheckStatus.PASS),
        (
            Scenario.TRANSACTION_STATUS_RECONCILIATION,
            CheckCode.STATUS_POLLING,
            CheckStatus.PASS,
        ),
        (Scenario.MEMPOOL_OBSERVATION, CheckCode.STATUS_POLLING, CheckStatus.PASS),
    )
    assert all(
        len(result.checks) == 1
        for result in results
        if result.execution is Execution.COMPLETE
    )


def test_vizor_unavailable_lanes_use_exact_reasons(tmp_path: Path) -> None:
    checkout = tmp_path / "vizor"
    checkout.mkdir()

    by_scenario = {
        item.scenario: item for item in build_vizor_results(checkout, _runtime(VALID_STATE))
    }

    for scenario in (Scenario.SERVER_SWITCHING, Scenario.DIRECT_FALLBACK):
        assert (
            by_scenario[scenario].unavailable_reason
            is UnavailableReason.FLUTTER_TOOLCHAIN_UNAVAILABLE
        )
    managed = UnavailableReason.MANAGED_ZCASHD_UNAVAILABLE_ON_DARWIN_ARM64
    for scenario in (
        Scenario.TEMPORARY_PUBLIC_ABSENCE,
        Scenario.NODE_RESTART,
        Scenario.PRE_RELEASE_CONFLICT,
        Scenario.RELEASE_DEADLINE_PRESERVATION,
    ):
        assert by_scenario[scenario].unavailable_reason is managed


@pytest.mark.parametrize(
    ("client", "results"),
    [
        (Client.ZODL_ANDROID, build_zodl_android_results()),
        (Client.ZODL_IOS, build_zodl_ios_results()),
    ],
)
def test_zodl_results_are_pinned_source_review_not_empirical(
    client: Client, results: tuple[LegacyClientResult, ...]
) -> None:
    assert tuple(result.scenario for result in results) == SCENARIO_REGISTRY
    assert all(result.client is client for result in results)
    assert all(result.evidence_grade is EvidenceGrade.SOURCE_DERIVED for result in results)
    assert all(result.execution is Execution.COMPLETE for result in results)
    assert all(
        result.rollout_classification is RolloutClassification.INCONCLUSIVE for result in results
    )
    assert all(not result.timeline for result in results)


def test_no_adapter_authorizes_private_delay(tmp_path: Path) -> None:
    checkout = tmp_path / "vizor"
    checkout.mkdir()
    all_results = (
        *build_vizor_results(checkout, _runtime(VALID_STATE)),
        *build_zodl_android_results(),
        *build_zodl_ios_results(),
    )

    assert all(
        result.rollout_classification is not RolloutClassification.PRIVATE_ENDPOINT_ONLY
        for result in all_results
    )


@pytest.mark.parametrize(
    ("state", "error_code"),
    [
        (CHECKOUT_UNAVAILABLE_STATE, AdapterErrorCode.VIZOR_CHECKOUT_UNAVAILABLE),
        (REVISION_MISMATCH_STATE, AdapterErrorCode.VIZOR_REVISION_MISMATCH),
        (ORIGIN_MISMATCH_STATE, AdapterErrorCode.VIZOR_ORIGIN_MISMATCH),
        (DIRTY_STATE, AdapterErrorCode.VIZOR_WORKTREE_DIRTY),
    ],
)
def test_vizor_preflight_failures_raise_typed_error_without_cargo(
    tmp_path: Path, state: FakeCheckoutState, error_code: AdapterErrorCode
) -> None:
    checkout = tmp_path / "vizor"
    checkout.mkdir()
    runner = RecordingRunner(state)
    runtime = AdapterRuntime(command_runner=runner, tool_probe=FixedToolProbe("/toolchain/cargo"))

    with pytest.raises(AdapterError) as caught:
        _ = build_vizor_results(checkout, runtime)

    assert caught.value.code is error_code
    assert not runner.status_calls


def test_missing_checkout_and_cargo_fail_stably(tmp_path: Path) -> None:
    with pytest.raises(AdapterError) as missing:
        _ = build_vizor_results(tmp_path / "missing", _runtime(VALID_STATE))
    assert missing.value.code is AdapterErrorCode.VIZOR_CHECKOUT_UNAVAILABLE

    checkout = tmp_path / "vizor"
    checkout.mkdir()
    with pytest.raises(AdapterError) as no_cargo:
        _ = build_vizor_results(checkout, _runtime(VALID_STATE, cargo=None))
    assert no_cargo.value.code is AdapterErrorCode.CARGO_UNAVAILABLE

    with pytest.raises(AdapterError) as cargo_failed:
        _ = build_vizor_results(checkout, _runtime(CARGO_FAILURE_STATE))
    assert cargo_failed.value.code is AdapterErrorCode.CARGO_EVIDENCE_FAILED


def test_vizor_results_are_deterministic_across_repeated_evidence_runs(tmp_path: Path) -> None:
    checkout = tmp_path / "vizor"
    checkout.mkdir()
    runner = RecordingRunner(VALID_STATE)
    runtime = AdapterRuntime(command_runner=runner, tool_probe=FixedToolProbe("/toolchain/cargo"))

    first = build_vizor_results(checkout, runtime)
    second = build_vizor_results(checkout, runtime)

    assert len(runner.status_calls) == 2 * len(VIZOR_RUST_EVIDENCE_REGISTRY)
    assert first == second
