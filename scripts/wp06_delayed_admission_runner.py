"""Representative deterministic WP06 automation, not client or integrated empirical evidence."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum, unique
from typing import NewType, assert_never

TransactionKey = NewType("TransactionKey", str)
LogicalDeadlineToken = NewType("LogicalDeadlineToken", str)


@unique
class AdmissionState(StrEnum):
    """Closed states for one representative delayed admission."""

    ACCEPTED = "accepted"
    RELEASED = "released"


@unique
class EndpointRoute(StrEnum):
    """Endpoint routes observable by the representative automation."""

    DELAYED_ADMISSION = "delayed_admission"
    DIRECT_FALLBACK = "direct_fallback"


@unique
class DeadlineObservation(StrEnum):
    """Logical deadline observations without wall-clock semantics."""

    PENDING = "pending"
    REACHED = "reached"


@dataclass(frozen=True, slots=True)
class AdmissionRequest:
    """Typed input identifying one admission attempt."""

    transaction_key: TransactionKey
    logical_deadline: LogicalDeadlineToken
    endpoint_route: EndpointRoute


@dataclass(frozen=True, slots=True)
class RepresentativeDelayedAdmission:
    """Immutable local state for representative-only WP06 invariant checks."""

    first_admission: AdmissionRequest
    state: AdmissionState
    release_count: int
    endpoint_route: EndpointRoute
    fallback_observed: bool
    status_polling_observed: bool

    @classmethod
    def admit(cls, request: AdmissionRequest) -> RepresentativeDelayedAdmission:
        """Create the accepted state while retaining the first request."""
        match request.endpoint_route:
            case EndpointRoute.DELAYED_ADMISSION:
                fallback_observed = False
            case EndpointRoute.DIRECT_FALLBACK:
                fallback_observed = True
            case _:
                assert_never(request.endpoint_route)
        return cls(
            first_admission=request,
            state=AdmissionState.ACCEPTED,
            release_count=0,
            endpoint_route=request.endpoint_route,
            fallback_observed=fallback_observed,
            status_polling_observed=False,
        )

    def retry(self, request: AdmissionRequest) -> RepresentativeDelayedAdmission:
        """Observe a retry without replacing first-admission identity or deadline."""
        if request.transaction_key != self.first_admission.transaction_key:
            return self
        match request.endpoint_route:
            case EndpointRoute.DELAYED_ADMISSION:
                return replace(self, endpoint_route=EndpointRoute.DELAYED_ADMISSION)
            case EndpointRoute.DIRECT_FALLBACK:
                return replace(
                    self,
                    endpoint_route=EndpointRoute.DIRECT_FALLBACK,
                    fallback_observed=True,
                )
            case _:
                assert_never(request.endpoint_route)

    def release(self, deadline: DeadlineObservation) -> RepresentativeDelayedAdmission:
        """Release once only after the logical deadline is observed reached."""
        match deadline:
            case DeadlineObservation.PENDING:
                return self
            case DeadlineObservation.REACHED:
                match self.state:
                    case AdmissionState.ACCEPTED:
                        return replace(self, state=AdmissionState.RELEASED, release_count=1)
                    case AdmissionState.RELEASED:
                        return self
                    case _:
                        assert_never(self.state)
            case _:
                assert_never(deadline)

    def poll_status(self, transaction_key: TransactionKey) -> RepresentativeDelayedAdmission:
        """Detect polling only when it targets the admitted transaction key."""
        if transaction_key != self.first_admission.transaction_key:
            return self
        return replace(self, status_polling_observed=True)
