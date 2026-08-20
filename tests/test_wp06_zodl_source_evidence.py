from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from scripts.wp06_legacy_client_adapters import (
    build_zodl_android_results,
    build_zodl_ios_results,
)
from scripts.wp06_legacy_client_contract import (
    CheckCode,
    CheckStatus,
    Client,
    EvidenceGrade,
    Execution,
    LegacyClientResult,
    RolloutClassification,
    Scenario,
    render_result,
)

if TYPE_CHECKING:
    from collections.abc import Callable

ANDROID_EXPECTED = (
    (Scenario.TEMPORARY_PUBLIC_ABSENCE, CheckCode.CLIENT_BEHAVIOR, CheckStatus.NOT_RUN),
    (Scenario.EXACT_RETRY, CheckCode.DUPLICATE_RELEASE, CheckStatus.NOT_RUN),
    (Scenario.LOST_RESPONSE_RETRY, CheckCode.CLIENT_BEHAVIOR, CheckStatus.PASS),
    (Scenario.TRANSACTION_STATUS_RECONCILIATION, CheckCode.STATUS_POLLING, CheckStatus.PASS),
    (Scenario.MEMPOOL_OBSERVATION, CheckCode.STATUS_POLLING, CheckStatus.NOT_RUN),
    (Scenario.SERVER_SWITCHING, CheckCode.CLIENT_BEHAVIOR, CheckStatus.PASS),
    (Scenario.DIRECT_FALLBACK, CheckCode.DIRECT_FALLBACK, CheckStatus.FAIL),
    (Scenario.NODE_RESTART, CheckCode.CLIENT_BEHAVIOR, CheckStatus.NOT_RUN),
    (Scenario.PRE_RELEASE_CONFLICT, CheckCode.CLIENT_BEHAVIOR, CheckStatus.NOT_RUN),
    (Scenario.RELEASE_DEADLINE_PRESERVATION, CheckCode.RELEASE_DEADLINE, CheckStatus.NOT_RUN),
)
IOS_EXPECTED = (
    (Scenario.TEMPORARY_PUBLIC_ABSENCE, CheckCode.CLIENT_BEHAVIOR, CheckStatus.NOT_RUN),
    (Scenario.EXACT_RETRY, CheckCode.DUPLICATE_RELEASE, CheckStatus.NOT_RUN),
    (Scenario.LOST_RESPONSE_RETRY, CheckCode.CLIENT_BEHAVIOR, CheckStatus.PASS),
    (Scenario.TRANSACTION_STATUS_RECONCILIATION, CheckCode.STATUS_POLLING, CheckStatus.NOT_RUN),
    (Scenario.MEMPOOL_OBSERVATION, CheckCode.STATUS_POLLING, CheckStatus.NOT_RUN),
    (Scenario.SERVER_SWITCHING, CheckCode.CLIENT_BEHAVIOR, CheckStatus.PASS),
    (Scenario.DIRECT_FALLBACK, CheckCode.DIRECT_FALLBACK, CheckStatus.NOT_RUN),
    (Scenario.NODE_RESTART, CheckCode.CLIENT_BEHAVIOR, CheckStatus.NOT_RUN),
    (Scenario.PRE_RELEASE_CONFLICT, CheckCode.CLIENT_BEHAVIOR, CheckStatus.NOT_RUN),
    (Scenario.RELEASE_DEADLINE_PRESERVATION, CheckCode.RELEASE_DEADLINE, CheckStatus.NOT_RUN),
)


@pytest.mark.parametrize(
    ("results", "expected"),
    [
        (build_zodl_android_results(), ANDROID_EXPECTED),
        (build_zodl_ios_results(), IOS_EXPECTED),
    ],
)
def test_zodl_wallet_release_check_mappings_are_exact(
    results: tuple[LegacyClientResult, ...],
    expected: tuple[tuple[Scenario, CheckCode, CheckStatus], ...],
) -> None:
    assert tuple(
        (result.scenario, result.checks[0].code, result.checks[0].status)
        for result in results
    ) == expected
    assert all(len(result.checks) == 1 for result in results)


@pytest.mark.parametrize(
    ("client", "builder"),
    [
        (Client.ZODL_ANDROID, build_zodl_android_results),
        (Client.ZODL_IOS, build_zodl_ios_results),
    ],
)
def test_zodl_source_review_stays_conservative_and_deterministic(
    client: Client,
    builder: Callable[[], tuple[LegacyClientResult, ...]],
) -> None:
    first = builder()
    second = builder()

    assert first == second
    assert tuple(render_result(result) for result in first) == tuple(
        render_result(result) for result in second
    )
    assert all(result.client is client for result in first)
    assert all(result.evidence_grade is EvidenceGrade.SOURCE_DERIVED for result in first)
    assert all(result.execution is Execution.COMPLETE for result in first)
    assert all(
        result.rollout_classification is RolloutClassification.INCONCLUSIVE for result in first
    )
    assert all(
        result.rollout_classification is not RolloutClassification.PRIVATE_ENDPOINT_ONLY
        for result in first
    )
    assert all(not result.timeline for result in first)
    assert all(result.unavailable_reason is None for result in first)
