"""Tests for representative WP06 automation, not client or integrated empirical evidence."""

from __future__ import annotations

from scripts.wp06_delayed_admission_runner import (
    AdmissionRequest,
    AdmissionState,
    DeadlineObservation,
    EndpointRoute,
    LogicalDeadlineToken,
    RepresentativeDelayedAdmission,
    TransactionKey,
)

ADMITTED_KEY = TransactionKey("representative-admitted-transaction")
OTHER_KEY = TransactionKey("representative-other-transaction")
INITIAL_DEADLINE = LogicalDeadlineToken("representative-initial-deadline")
REPLACEMENT_DEADLINE = LogicalDeadlineToken("representative-replacement-deadline")


def _admitted() -> RepresentativeDelayedAdmission:
    return RepresentativeDelayedAdmission.admit(
        AdmissionRequest(
            transaction_key=ADMITTED_KEY,
            logical_deadline=INITIAL_DEADLINE,
            endpoint_route=EndpointRoute.DELAYED_ADMISSION,
        )
    )


def test_representative_exact_retry_is_idempotent_without_client_execution() -> None:
    admitted = _admitted()

    retried = admitted.retry(admitted.first_admission)

    assert retried == admitted
    assert retried.first_admission is admitted.first_admission
    assert retried.state is AdmissionState.ACCEPTED


def test_representative_retry_cannot_reset_first_logical_deadline() -> None:
    admitted = _admitted()
    retry = AdmissionRequest(
        transaction_key=ADMITTED_KEY,
        logical_deadline=REPLACEMENT_DEADLINE,
        endpoint_route=EndpointRoute.DELAYED_ADMISSION,
    )

    retried = admitted.retry(retry)

    assert retried.first_admission.logical_deadline == INITIAL_DEADLINE
    assert retried.first_admission.logical_deadline != retry.logical_deadline


def test_representative_duplicate_calls_cannot_duplicate_release() -> None:
    admitted = _admitted().retry(_admitted().first_admission)

    released = admitted.release(DeadlineObservation.REACHED)
    repeated = released.release(DeadlineObservation.REACHED)

    assert released.state is AdmissionState.RELEASED
    assert released.release_count == 1
    assert repeated == released


def test_representative_release_before_logical_deadline_is_rejected() -> None:
    admitted = _admitted()

    result = admitted.release(DeadlineObservation.PENDING)

    assert result == admitted
    assert result.state is AdmissionState.ACCEPTED
    assert result.release_count == 0


def test_representative_direct_fallback_is_detected_without_empirical_claim() -> None:
    admitted = _admitted()
    fallback_retry = AdmissionRequest(
        transaction_key=ADMITTED_KEY,
        logical_deadline=REPLACEMENT_DEADLINE,
        endpoint_route=EndpointRoute.DIRECT_FALLBACK,
    )

    observed = admitted.retry(fallback_retry)

    assert observed.endpoint_route is EndpointRoute.DIRECT_FALLBACK
    assert observed.fallback_observed
    assert observed.first_admission == admitted.first_admission


def test_representative_polling_for_admitted_transaction_is_detected() -> None:
    admitted = _admitted()

    observed = admitted.poll_status(ADMITTED_KEY)

    assert observed.status_polling_observed


def test_representative_polling_for_different_transaction_is_not_detected() -> None:
    admitted = _admitted()

    observed = admitted.poll_status(OTHER_KEY)

    assert observed == admitted
    assert not observed.status_polling_observed
