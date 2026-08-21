from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from scripts import inspect_legacy_client
from scripts.legacy_client_contract import (
    SCENARIO_REGISTRY,
    Client,
    Scenario,
    TimelineEventCode,
)

from tests.test_inspect_legacy_client import inspect_fixture

if TYPE_CHECKING:
    from pathlib import Path


def _timeline_lines(output: str, scenario: Scenario) -> tuple[str, ...]:
    section = output.split(f"scenario={scenario.value}\n", maxsplit=1)[1].split(
        "\nscenario=", maxsplit=1
    )[0]
    return tuple(line for line in section.splitlines() if line.startswith("timeline="))


def _expected_timeline(
    observed: frozenset[TimelineEventCode], status: inspect_legacy_client.HumanTimelineStatus
) -> tuple[str, ...]:
    return tuple(
        "timeline={} status={}".format(
            event.value,
            inspect_legacy_client.HumanTimelineStatus.OBSERVED.value
            if event in observed
            else status.value,
        )
        for event in TimelineEventCode
    )


def test_human_renderer_renders_truthful_complete_timeline_matrix(tmp_path: Path) -> None:
    _, vizor_output, _ = inspect_fixture(
        Client.VIZOR, tmp_path / "vizor", inspect_legacy_client.OutputFormat.HUMAN
    )
    _, android_output, _ = inspect_fixture(
        Client.ZODL_ANDROID, tmp_path / "android", inspect_legacy_client.OutputFormat.HUMAN
    )

    assert _timeline_lines(vizor_output, Scenario.EXACT_RETRY) == _expected_timeline(
        frozenset(
            (
                TimelineEventCode.SUBMISSION_CALL,
                TimelineEventCode.CLIENT_VISIBLE_RESPONSE,
                TimelineEventCode.CLIENT_RETRIES_OR_STATUS_QUERIES,
                TimelineEventCode.CLIENT_FINAL_STATE,
            )
        ),
        inspect_legacy_client.HumanTimelineStatus.NOT_OBSERVED,
    )
    assert _timeline_lines(android_output, Scenario.LOST_RESPONSE_RETRY) == _expected_timeline(
        frozenset(), inspect_legacy_client.HumanTimelineStatus.NOT_OBSERVED
    )
    unavailable_start = f"scenario={Scenario.TEMPORARY_PUBLIC_ABSENCE.value}\n"
    unavailable_section = vizor_output.split(unavailable_start, maxsplit=1)[1].split(
        "\nscenario=", maxsplit=1
    )[0]
    assert _timeline_lines(vizor_output, Scenario.TEMPORARY_PUBLIC_ABSENCE) == _expected_timeline(
        frozenset(), inspect_legacy_client.HumanTimelineStatus.NOT_RUN
    )
    assert unavailable_section.count(
        "unavailable_reason=managed_zcashd_unavailable_on_darwin_arm64"
    ) == 1


@pytest.mark.parametrize("client", tuple(Client))
def test_human_timeline_has_seventy_ordered_status_lines_and_is_deterministic(
    tmp_path: Path, client: Client
) -> None:
    first = inspect_fixture(client, tmp_path / "first", inspect_legacy_client.OutputFormat.HUMAN)
    second = inspect_fixture(client, tmp_path / "second", inspect_legacy_client.OutputFormat.HUMAN)

    assert first[0] == second[0] == 0
    assert first[2] == second[2] == ""
    assert first[1] == second[1]
    timeline_lines = tuple(line for line in first[1].splitlines() if line.startswith("timeline="))
    assert len(timeline_lines) == len(SCENARIO_REGISTRY) * len(TimelineEventCode)
    assert all(
        line.endswith(
            (
                "status=observed",
                "status=not_observed",
                "status=not_run",
            )
        )
        for line in timeline_lines
    )
