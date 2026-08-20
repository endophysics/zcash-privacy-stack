"""Pinned Vizor Rust evidence registry."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, unique
from typing import Final

from scripts.wp06_legacy_client_contract import Scenario


@unique
class VizorEvidenceClaim(StrEnum):
    """Behavioral claim grounded by one pinned Vizor Rust test."""

    RAW_BYTES_PRESERVED = "raw_bytes_preserved"
    DUPLICATE_ACCEPTANCE = "duplicate_acceptance"
    LOST_RESPONSE_STATE_PRESERVED = "lost_response_state_preserved"
    STATUS_RETRY_CLASSIFICATION = "status_retry_classification"
    MEMPOOL_OBSERVATION = "mempool_observation"


@dataclass(frozen=True, slots=True)
class VizorRustEvidence:
    """Exact Rust test and the WP06 scenarios it grounds."""

    test_name: str
    scenarios: tuple[Scenario, ...]
    claim: VizorEvidenceClaim


VIZOR_RUST_EVIDENCE_REGISTRY: Final[tuple[VizorRustEvidence, ...]] = (
    VizorRustEvidence(
        "wallet::sync::transactions::tests::resubmit_includes_valid_outbound_pending",
        (Scenario.LOST_RESPONSE_RETRY,),
        VizorEvidenceClaim.RAW_BYTES_PRESERVED,
    ),
    VizorRustEvidence(
        "wallet::sync::pczt::tests::pczt_duplicate_response_stores_locally_and_returns_broadcasted",
        (Scenario.EXACT_RETRY,),
        VizorEvidenceClaim.DUPLICATE_ACCEPTANCE,
    ),
    VizorRustEvidence(
        "wallet::sync::pczt::tests::pczt_non_deadline_transport_failure_remains_ambiguous",
        (Scenario.LOST_RESPONSE_RETRY,),
        VizorEvidenceClaim.LOST_RESPONSE_STATE_PRESERVED,
    ),
    VizorRustEvidence(
        "wallet::sync_engine::enhance::tests::get_transaction_transient_errors_retry_as_network",
        (Scenario.TRANSACTION_STATUS_RECONCILIATION,),
        VizorEvidenceClaim.STATUS_RETRY_CLASSIFICATION,
    ),
    VizorRustEvidence(
        "wallet::sync_engine::mempool::tests::lookup_known_pending_tx_finds_unmined_tx",
        (Scenario.MEMPOOL_OBSERVATION,),
        VizorEvidenceClaim.MEMPOOL_OBSERVATION,
    ),
)
