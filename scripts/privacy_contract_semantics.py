"""Typed semantic rules for structurally valid privacy contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, ClassVar, Final, assert_never

from pydantic import BaseModel, ConfigDict, ValidationError

from scripts.privacy_contract_types import ContractKind, JsonLocation, ValidationIssue

if TYPE_CHECKING:
    from scripts.privacy_contract_json import JsonDocument


SUPPORTED_MAJOR: Final = 1


class _ContractModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore", frozen=True)


class _Validity(_ContractModel):
    valid_from: datetime
    valid_until: datetime


class _PolicyNode(_ContractModel):
    implementation: str


class _PrivateWrite(_ContractModel):
    enabled: bool
    submission_protocol: str
    minimum_delay_ms: int
    maximum_delay_ms: int


class _Policy(_Validity):
    policy_version: str
    network: str
    node: _PolicyNode
    private_write: _PrivateWrite


class _Capabilities(_Validity):
    capabilities_version: str


class _ManifestObject(_ContractModel):
    start_height: int | None = None
    end_height: int | None = None


class _Manifest(_ContractModel):
    format_version: str
    objects: tuple[_ManifestObject, ...]


@dataclass(frozen=True, slots=True)
class SemanticOptions:
    """Freshness options supplied to semantic contract validation."""

    check_freshness: bool
    at: datetime | None


def semantic_issues(
    kind: ContractKind,
    document: JsonDocument,
    options: SemanticOptions,
) -> tuple[ValidationIssue, ...]:
    """Apply the semantic rules for one structurally valid contract."""
    try:
        match kind:
            case ContractKind.PRIVACY_POLICY:
                policy = _Policy.model_validate(document)
                return _policy_issues(policy, options)
            case ContractKind.PRIVACY_CAPABILITIES:
                capabilities = _Capabilities.model_validate(document)
                return _capabilities_issues(capabilities, options)
            case ContractKind.CANONICAL_READ_MANIFEST:
                manifest = _Manifest.model_validate(document)
                return _manifest_issues(manifest)
            case _:
                assert_never(kind)
    except ValidationError:
        return (
            ValidationIssue(
                "document.typed_boundary",
                (),
                (("contract_kind", kind.value),),
            ),
        )


def _policy_issues(
    policy: _Policy,
    options: SemanticOptions,
) -> tuple[ValidationIssue, ...]:
    issues = [*_version_issues(policy.policy_version, ("policy_version",))]
    issues.extend(_validity_issues("policy", policy, options))
    if policy.private_write.minimum_delay_ms > policy.private_write.maximum_delay_ms:
        issues.append(
            ValidationIssue(
                "policy.delay.order",
                ("private_write",),
                (("earlier", "minimum_delay_ms"),),
            )
        )
    direct_is_enabled = (
        policy.private_write.enabled
        and policy.private_write.submission_protocol == "development-direct-v1"
    )
    development_node = policy.network == "regtest" and policy.node.implementation == "development"
    if direct_is_enabled and not development_node:
        issues.append(
            ValidationIssue(
                "policy.development_direct.requires_development_node",
                ("private_write", "submission_protocol"),
                (("implementation", policy.node.implementation),),
            )
        )
    return tuple(issues)


def _capabilities_issues(
    capabilities: _Capabilities,
    options: SemanticOptions,
) -> tuple[ValidationIssue, ...]:
    return (
        *_version_issues(capabilities.capabilities_version, ("capabilities_version",)),
        *_validity_issues("capabilities", capabilities, options),
    )


def _manifest_issues(manifest: _Manifest) -> tuple[ValidationIssue, ...]:
    issues = [*_version_issues(manifest.format_version, ("format_version",))]
    for index, manifest_object in enumerate(manifest.objects):
        start = manifest_object.start_height
        end = manifest_object.end_height
        if start is not None and end is not None and start > end:
            issues.append(
                ValidationIssue(
                    "manifest.range.order",
                    ("objects", index),
                    (("earlier", "start_height"),),
                )
            )
    return tuple(issues)


def _version_issues(version: str, location: JsonLocation) -> tuple[ValidationIssue, ...]:
    major, _, _ = version.partition(".")
    if major == str(SUPPORTED_MAJOR):
        return ()
    return (
        ValidationIssue(
            "version.unsupported",
            location,
            (("supported_major", str(SUPPORTED_MAJOR)),),
        ),
    )


def _validity_issues(
    namespace: str,
    validity: _Validity,
    options: SemanticOptions,
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    if validity.valid_until <= validity.valid_from:
        issues.append(
            ValidationIssue(
                f"{namespace}.validity.order",
                (),
                (("earlier", "valid_from"),),
            )
        )
    if not options.check_freshness:
        return tuple(issues)
    effective_at = datetime.now(UTC) if options.at is None else options.at.astimezone(UTC)
    at_text = effective_at.isoformat()
    if effective_at < validity.valid_from:
        issues.append(
            ValidationIssue(
                f"{namespace}.validity.not_yet_valid",
                (),
                (("at", at_text),),
            )
        )
    if effective_at >= validity.valid_until:
        issues.append(
            ValidationIssue(
                f"{namespace}.validity.expired",
                (),
                (("at", at_text),),
            )
        )
    return tuple(issues)
