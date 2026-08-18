# Interface Versioning

This document defines the normative ownership and compatibility rules for the WP01 interface contracts. The terms MUST, MUST NOT, SHOULD, and MAY express requirements.

## Canonical ownership

The `zcash-privacy-stack` integration repository MUST be the canonical source for cross-stack JSON schemas and their examples. Component repositories MAY contain generated or vendored copies, but those copies MUST NOT become independent sources of truth.

Component implementations and releases remain independent. A component MAY adopt any contract without implementing the other contracts, except where that component's own behavior explicitly depends on them.

## Independent version domains

Each interface has its own version domain:

| Interface | Version marker | Supported major in WP01 |
|---|---|---|
| Privacy policy | `policy_version` | 1 |
| Privacy capabilities | `capabilities_version` | 1 |
| Canonical read manifest | `format_version` | 1 |
| Private admission | `zcash.privacy.admission.v1` package | Independently versioned, unchanged by WP01 |

The three JSON version fields and every item in `supported_policy_versions` MUST use canonical `MAJOR.MINOR.PATCH` decimal notation: each component MUST be `0` or a non-zero decimal integer without leading zeros, and prerelease or build suffixes are not permitted. Their values evolve independently and MUST NOT be assumed to match. Supporting one version domain MUST NOT imply support for another. In particular, `supported_policy_versions` reports policy compatibility and does not set or constrain `capabilities_version`.

A consumer MUST reject a malformed version. It MUST fail closed if the declared major version is unsupported. Failure MUST occur before the document is used to make policy, capability, or manifest decisions.

## Stable schema identifiers

The major-one schema identifiers are:

| Contract | Schema identifier |
|---|---|
| Privacy policy | `urn:zcash:privacy-stack:privacy-policy:1` |
| Privacy capabilities | `urn:zcash:privacy-stack:privacy-capabilities:1` |
| Canonical read manifest | `urn:zcash:privacy-stack:canonical-read-manifest:1` |

These URNs are stable identifiers, not endpoints. Implementations MUST NOT fetch them. A schema MUST NOT contain a remote `$ref` or otherwise require network retrieval. Validation MUST use the locally available canonical schema or a faithful derived copy.

## Compatibility within a major version

An update within a major version MAY add optional fields. Readers MUST ignore optional fields they do not understand after validating the declared major version. A forwarder, editor, or other tool expected to reproduce a document MUST preserve unknown optional fields unchanged. A consumer that only reads a document does not need to retain ignored fields.

Deprecation does not remove a field. Once deprecated, a field MUST remain optional and keep a compatible type and meaning through the rest of its major version. Producers SHOULD stop depending on deprecated fields before adopting the next major version.

Minor versions SHOULD identify additive, backward-compatible contract changes. Patch versions SHOULD identify clarifications or corrections that do not change accepted document meaning. Consumers MUST base compatibility first on the major version and MUST NOT require exact minor or patch equality unless a separate contract feature explicitly calls for it.

## Changes that require a new major version

Any incompatible contract change MUST increment the affected interface's major version. This includes:

- adding a required field;
- removing a field;
- changing a field's type;
- making an optional field required;
- changing a field's meaning incompatibly;
- changing validation rules incompatibly so that a document valid under the earlier contract is rejected;
- reusing a deprecated field for a different purpose.

A major bump applies only to the affected interface. A new policy major does not by itself require a new capabilities major, manifest major, or private-admission package. Implementations MAY support more than one major at the same time, but they MUST validate and interpret each document under its declared major.

## Private-admission boundary

The private-admission Protocol Buffers interface uses the package `zcash.privacy.admission.v1`. That package is independently versioned and remains unchanged in WP01. The JSON fields `policy_version`, `capabilities_version`, and `format_version` MUST NOT be treated as the Protocol Buffers package version. WP01 adds no generated private-admission bindings.

## Validator scope

WP01 validators are offline structural and semantic compatibility checks. They MAY check JSON structure, declared major support, formats, ranges, and cross-field invariants. They MUST NOT retrieve schemas or contract documents from the network.

A successful validation result means only that the supplied document is structurally and semantically compatible with the locally supported contract. It does not establish document authenticity, authorize an operator, verify a signature, appraise attestation, or prove that advertised behavior exists.

## WP01 exclusions

WP01 defines schemas, examples, version rules, and offline validation only. It adds no:

- discovery transport or endpoint;
- schema, policy, capability, or manifest retrieval mechanism;
- authenticity or authorization mechanism;
- signature creation or verification;
- OHTTP implementation;
- attestation implementation or appraisal;
- wallet behavior;
- node behavior;
- Zaino behavior;
- generated bindings.

Fields that describe URLs, signatures, OHTTP, attestation, wallet behavior, node behavior, or Zaino behavior are data contracts only. Their presence MUST NOT be read as a claim that WP01 implements the mechanism they describe.
