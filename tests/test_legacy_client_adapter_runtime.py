from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest
from scripts.legacy_client_adapter_runtime import (
    VIZOR_PIN,
    AdapterError,
    AdapterErrorCode,
    AdapterRuntime,
    CommandOutput,
    SubprocessCommandRunner,
    run_vizor_cargo_evidence,
)
from scripts.legacy_client_contract import Scenario
from scripts.vizor_evidence import VIZOR_RUST_EVIDENCE_REGISTRY, VizorEvidenceClaim

from tests.legacy_client_adapter_fakes import FakeCheckoutState, FixedToolProbe, RecordingRunner

if TYPE_CHECKING:
    from pathlib import Path


def test_subprocess_runner_executes_argument_tuple_without_shell(tmp_path: Path) -> None:
    runner = SubprocessCommandRunner()

    output = runner.output((sys.executable, "-c", "print('direct-command')"), tmp_path)

    assert output.return_code == 0
    assert output.stdout == "direct-command"


def test_vizor_evidence_registry_is_exact_ordered_and_unique() -> None:
    assert tuple(
        (evidence.test_name, evidence.scenarios, evidence.claim)
        for evidence in VIZOR_RUST_EVIDENCE_REGISTRY
    ) == (
        (
            "wallet::sync::transactions::tests::resubmit_includes_valid_outbound_pending",
            (Scenario.LOST_RESPONSE_RETRY,),
            VizorEvidenceClaim.RAW_BYTES_PRESERVED,
        ),
        (
            "wallet::sync::pczt::tests::pczt_duplicate_response_stores_locally_and_returns_broadcasted",
            (Scenario.EXACT_RETRY,),
            VizorEvidenceClaim.DUPLICATE_ACCEPTANCE,
        ),
        (
            "wallet::sync::pczt::tests::pczt_non_deadline_transport_failure_remains_ambiguous",
            (Scenario.LOST_RESPONSE_RETRY,),
            VizorEvidenceClaim.LOST_RESPONSE_STATE_PRESERVED,
        ),
        (
            "wallet::sync_engine::enhance::tests::get_transaction_transient_errors_retry_as_network",
            (Scenario.TRANSACTION_STATUS_RECONCILIATION,),
            VizorEvidenceClaim.STATUS_RETRY_CLASSIFICATION,
        ),
        (
            "wallet::sync_engine::mempool::tests::lookup_known_pending_tx_finds_unmined_tx",
            (Scenario.MEMPOOL_OBSERVATION,),
            VizorEvidenceClaim.MEMPOOL_OBSERVATION,
        ),
    )
    names = tuple(evidence.test_name for evidence in VIZOR_RUST_EVIDENCE_REGISTRY)
    assert len(names) == len(set(names))


def _exact_commands(checkout: Path) -> tuple[tuple[str, ...], ...]:
    manifest = str(checkout / "rust" / "Cargo.toml")
    return tuple(
        (
            "/toolchain/cargo",
            "test",
            "--locked",
            "--offline",
            "--manifest-path",
            manifest,
            "--lib",
            evidence.test_name,
            "--",
            "--exact",
        )
        for evidence in VIZOR_RUST_EVIDENCE_REGISTRY
    )


def _discovery_commands(checkout: Path) -> tuple[tuple[str, ...], ...]:
    return tuple((*command, "--list") for command in _exact_commands(checkout))


def _runtime(runner: RecordingRunner) -> AdapterRuntime:
    return AdapterRuntime(command_runner=runner, tool_probe=FixedToolProbe("/toolchain/cargo"))


def test_vizor_runs_each_exact_test_once_in_registry_order(tmp_path: Path) -> None:
    checkout = tmp_path / "vizor"
    checkout.mkdir()
    state = FakeCheckoutState(revision=VIZOR_PIN.revision, origin=VIZOR_PIN.repository)
    runner = RecordingRunner(state)

    run_vizor_cargo_evidence(checkout, _runtime(runner))

    expected_calls = tuple(
        (discovery, run)
        for discovery, run in zip(
            _discovery_commands(checkout), _exact_commands(checkout), strict=True
        )
    )
    assert runner.cargo_discovery_calls == [
        (command, checkout) for command, _ in expected_calls
    ]
    assert runner.status_calls == [(command, checkout) for _, command in expected_calls]
    assert runner.cargo_calls == [
        (command, checkout) for pair in expected_calls for command in pair
    ]


@pytest.mark.parametrize("failure_index", range(5))
def test_vizor_exact_tests_fail_fast_on_nonzero_status(
    tmp_path: Path, failure_index: int
) -> None:
    checkout = tmp_path / "vizor"
    checkout.mkdir()
    statuses = tuple(9 if index == failure_index else 0 for index in range(5))
    state = FakeCheckoutState(
        revision=VIZOR_PIN.revision,
        origin=VIZOR_PIN.repository,
        cargo_statuses=statuses,
    )
    runner = RecordingRunner(state)

    with pytest.raises(AdapterError) as caught:
        run_vizor_cargo_evidence(checkout, _runtime(runner))

    assert caught.value.code is AdapterErrorCode.CARGO_EVIDENCE_FAILED
    assert runner.cargo_discovery_calls == [
        (command, checkout)
        for command in _discovery_commands(checkout)[: failure_index + 1]
    ]
    assert runner.status_calls == [
        (command, checkout) for command in _exact_commands(checkout)[: failure_index + 1]
    ]
    assert runner.cargo_calls == [
        (command, checkout)
        for index in range(failure_index + 1)
        for command in (_discovery_commands(checkout)[index], _exact_commands(checkout)[index])
    ]


@pytest.mark.parametrize(
    ("failure_index", "discovery"),
    [
        (0, ""),
        (2, "other::module::test: test"),
        (
            4,
            f"{VIZOR_RUST_EVIDENCE_REGISTRY[0].test_name}: benchmark",
        ),
    ],
)
def test_vizor_evidence_stops_before_run_when_exact_test_listing_is_missing(
    tmp_path: Path, failure_index: int, discovery: str
) -> None:
    checkout = tmp_path / "vizor"
    checkout.mkdir()
    state = FakeCheckoutState(
        revision=VIZOR_PIN.revision,
        origin=VIZOR_PIN.repository,
        cargo_discoveries=tuple(
            CommandOutput(0, f"{evidence.test_name}: test")
            if index < failure_index
            else CommandOutput(0, discovery)
            for index, evidence in enumerate(VIZOR_RUST_EVIDENCE_REGISTRY)
        ),
    )
    runner = RecordingRunner(state)

    with pytest.raises(AdapterError) as caught:
        run_vizor_cargo_evidence(checkout, _runtime(runner))

    assert caught.value.code is AdapterErrorCode.CARGO_EVIDENCE_MISSING
    assert runner.cargo_discovery_calls == [
        (command, checkout)
        for command in _discovery_commands(checkout)[: failure_index + 1]
    ]
    assert runner.status_calls == [
        (command, checkout) for command in _exact_commands(checkout)[:failure_index]
    ]
    assert runner.cargo_calls == [
        (command, checkout)
        for index in range(failure_index)
        for command in (_discovery_commands(checkout)[index], _exact_commands(checkout)[index])
    ] + [(_discovery_commands(checkout)[failure_index], checkout)]
