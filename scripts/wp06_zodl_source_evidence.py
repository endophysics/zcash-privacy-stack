"""Pinned Zodl wallet-release source evidence for WP06."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from scripts.wp06_legacy_client_contract import CheckCode, CheckStatus, Scenario


@dataclass(frozen=True, slots=True)
class ZodlScenarioMapping:
    """One source-reviewed wallet scenario check."""

    scenario: Scenario
    check_code: CheckCode
    check_status: CheckStatus


# SDK-only findings are excluded because wallet releases do not pin immutable SDK revisions.
ZODL_ANDROID_SOURCE_MAPPING: Final[tuple[ZodlScenarioMapping, ...]] = (
    ZodlScenarioMapping(
        Scenario.TEMPORARY_PUBLIC_ABSENCE, CheckCode.CLIENT_BEHAVIOR, CheckStatus.NOT_RUN
    ),
    ZodlScenarioMapping(Scenario.EXACT_RETRY, CheckCode.DUPLICATE_RELEASE, CheckStatus.NOT_RUN),
    ZodlScenarioMapping(Scenario.LOST_RESPONSE_RETRY, CheckCode.CLIENT_BEHAVIOR, CheckStatus.PASS),
    ZodlScenarioMapping(
        Scenario.TRANSACTION_STATUS_RECONCILIATION, CheckCode.STATUS_POLLING, CheckStatus.PASS
    ),
    ZodlScenarioMapping(
        Scenario.MEMPOOL_OBSERVATION, CheckCode.STATUS_POLLING, CheckStatus.NOT_RUN
    ),
    ZodlScenarioMapping(Scenario.SERVER_SWITCHING, CheckCode.CLIENT_BEHAVIOR, CheckStatus.PASS),
    ZodlScenarioMapping(Scenario.DIRECT_FALLBACK, CheckCode.DIRECT_FALLBACK, CheckStatus.FAIL),
    ZodlScenarioMapping(Scenario.NODE_RESTART, CheckCode.CLIENT_BEHAVIOR, CheckStatus.NOT_RUN),
    ZodlScenarioMapping(
        Scenario.PRE_RELEASE_CONFLICT, CheckCode.CLIENT_BEHAVIOR, CheckStatus.NOT_RUN
    ),
    ZodlScenarioMapping(
        Scenario.RELEASE_DEADLINE_PRESERVATION, CheckCode.RELEASE_DEADLINE, CheckStatus.NOT_RUN
    ),
)

ZODL_IOS_SOURCE_MAPPING: Final[tuple[ZodlScenarioMapping, ...]] = (
    ZodlScenarioMapping(
        Scenario.TEMPORARY_PUBLIC_ABSENCE, CheckCode.CLIENT_BEHAVIOR, CheckStatus.NOT_RUN
    ),
    ZodlScenarioMapping(Scenario.EXACT_RETRY, CheckCode.DUPLICATE_RELEASE, CheckStatus.NOT_RUN),
    ZodlScenarioMapping(Scenario.LOST_RESPONSE_RETRY, CheckCode.CLIENT_BEHAVIOR, CheckStatus.PASS),
    ZodlScenarioMapping(
        Scenario.TRANSACTION_STATUS_RECONCILIATION,
        CheckCode.STATUS_POLLING,
        CheckStatus.NOT_RUN,
    ),
    ZodlScenarioMapping(
        Scenario.MEMPOOL_OBSERVATION, CheckCode.STATUS_POLLING, CheckStatus.NOT_RUN
    ),
    ZodlScenarioMapping(Scenario.SERVER_SWITCHING, CheckCode.CLIENT_BEHAVIOR, CheckStatus.PASS),
    ZodlScenarioMapping(
        Scenario.DIRECT_FALLBACK, CheckCode.DIRECT_FALLBACK, CheckStatus.NOT_RUN
    ),
    ZodlScenarioMapping(Scenario.NODE_RESTART, CheckCode.CLIENT_BEHAVIOR, CheckStatus.NOT_RUN),
    ZodlScenarioMapping(
        Scenario.PRE_RELEASE_CONFLICT, CheckCode.CLIENT_BEHAVIOR, CheckStatus.NOT_RUN
    ),
    ZodlScenarioMapping(
        Scenario.RELEASE_DEADLINE_PRESERVATION, CheckCode.RELEASE_DEADLINE, CheckStatus.NOT_RUN
    ),
)
