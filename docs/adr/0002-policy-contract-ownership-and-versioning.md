# ADR 0002: Policy Contract Ownership and Independent Versioning

- Status: Accepted
- Date: 2026-08-18

## Context

WP01 replaces placeholder privacy contract schemas and adds a capability document. The policy, capability, and canonical read manifest contracts cross component boundaries, but no component repository is a natural owner for all of them. Their compatibility rules must also allow a component to adopt one contract without forcing simultaneous releases of the others.

The private-admission Protocol Buffers interface already has its own package version. Its lifecycle is separate from the JSON contracts and is not part of the WP01 schema change.

## Decision

The `zcash-privacy-stack` integration repository is the canonical owner of the cross-stack JSON schemas and their examples. Component repositories may generate or vendor copies, but those copies are not authoritative. Components remain independently implementable, releasable, and adoptable.

The following contracts are independently versioned:

- privacy policy, through `policy_version`;
- privacy capabilities, through `capabilities_version`;
- canonical read manifest, through `format_version`;
- private admission, through the Protocol Buffers package `zcash.privacy.admission.v1`.

The three JSON version fields independently support major version 1. Their version numbers do not need to match. Support for one contract or version does not imply support for another. A capability document may report supported policy versions without coupling the capability contract's version to those policy versions.

The major-one JSON schemas use these stable identifiers:

- `urn:zcash:privacy-stack:privacy-policy:1`;
- `urn:zcash:privacy-stack:privacy-capabilities:1`;
- `urn:zcash:privacy-stack:canonical-read-manifest:1`.

These URNs identify schemas. They are not network endpoints or retrieval locations. Schemas must be self-contained and must not contain remote schema references.

Within a major version, optional additive fields are compatible. Readers ignore optional fields they do not understand. Tools that read and rewrite documents preserve unknown optional fields when their role requires lossless forwarding or editing. Deprecated fields remain optional and retain their compatible meaning through the rest of that major version.

Adding a required field, removing a field, changing a field's type, or changing its meaning incompatibly requires a new major version. Consumers must fail closed when a document declares an unsupported major version.

The package `zcash.privacy.admission.v1` remains independently versioned and unchanged by WP01. WP01 does not add generated bindings for it.

Validators are offline structural and semantic compatibility checks. They check documents against local schemas and cross-field rules. They do not discover or retrieve documents, establish authenticity, or prove that a service implements a claimed behavior.

WP01 adds no discovery transport, retrieval mechanism, authenticity mechanism, signatures, OHTTP implementation, attestation implementation, wallet behavior, node behavior, Zaino behavior, or generated bindings.

## Assumptions

- Cross-stack JSON contracts need a neutral canonical home.
- Components may adopt the contracts on different schedules.
- Major version 1 can evolve through optional additive fields without coordinated component releases.
- Transport, trust, and component behavior will be specified and implemented in later work packages.

## Consequences

### Positive

- Schema ownership and review responsibility are unambiguous.
- Policy, capabilities, manifest, and private-admission evolution remain decoupled.
- Major-one consumers can accept compatible additions while rejecting unsupported majors.
- Local validation does not imply transport, authenticity, or runtime support.

### Negative

- Component repositories must track canonical schema changes and manage derived copies.
- Lossless intermediaries and editors must preserve fields they do not understand.
- Incompatible changes require parallel major-version schemas and explicit adoption.

## Rejected alternatives

### Let each component own its copy

This would create competing contract definitions and make cross-component compatibility depend on repository-specific drift.

### Use one version for every interface

This would couple unrelated releases and prevent independent adoption of policy, capabilities, manifest, and private admission changes.

### Use schema identifiers as retrieval URLs

This would make validation depend on network availability and would blur identification with discovery. WP01 validation is deliberately offline.
