# Repository Ownership

## Canonical repositories

### `zcash-privacy-stack`

Owns composition rather than component implementation:

- cross-stack architecture and threat model;
- cross-component ADRs;
- shared schemas and interface definitions;
- `components.lock.toml` with tested revisions;
- bootstrap, orchestration, and end-to-end inspection commands;
- relay deployment packaging;
- compatibility and conformance scenarios;
- documentation describing how components fit together.

It must not vendor Zakura, Zebra, Zaino, or wallet source.

### Zakura fork

Owns:

- node-side admission and release implementation;
- node-local tests and diagnostics;
- Zakura-specific ADRs;
- documentation of node configuration and semantics;
- compatibility with Zakura upstream;
- the initially embedded node-independent admission crate.

It must not become the canonical home of OHTTP, wallet, light-client, or full-stack architecture decisions.

### `zcash-private-gateway`

Owns:

- OHTTP gateway handling;
- narrow private-submission protocol;
- request padding and replay handling;
- node-admission client;
- optional TEE runtime and attestation implementation;
- gateway-specific ADRs and inspection commands.

### Zaino fork

Create when server implementation work begins. It owns:

- privacy endpoint behavior;
- canonical read-object generation;
- server-side method profiles;
- Zaino-specific ADRs and tests;
- upstream Zaino maintenance.

### Wallet repository

Owns:

- OHTTP client support;
- relay selection and retry behavior;
- attestation appraisal;
- fail-closed behavior;
- range bucketing and read/write session separation;
- wallet-specific ADRs and UI behavior.

### Zebra fork

Create when the Zakura implementation is stable enough to port. It owns only the Zebra adapter and Zebra-specific node changes.

## ADR placement rule

Place an ADR according to the scope of its consequences.

### Integration repository ADRs

Examples:

- repository topology;
- use of standard OHTTP rather than a custom relay protocol;
- independent relay/gateway roles;
- cross-stack policy schema;
- separation of read and write planes;
- decision to use canonical read objects;
- criteria for extracting a shared crate.

### Component ADRs

Examples in Zakura:

- separate private pool versus visibility flags;
- admission context representation;
- release promotion semantics;
- private dependency handling;
- reorg behavior.

Examples in the gateway:

- inner request format;
- padding size;
- replay-key design;
- TEE key lifecycle.

### Link rather than duplicate

A component README may summarize and link to a cross-stack ADR. Do not copy the full decision into several repositories because duplicated ADRs drift.

## Shared code extraction

Do not create a shared-code repository merely because code appears conceptually generic.

Start the admission state machine as a clean crate in the Zakura workspace. Extract it only when:

1. Zebra or another real consumer needs it;
2. the interface has survived the Zakura implementation;
3. extraction removes real duplication;
4. the new repository has a clear release and compatibility policy.

Until then, keep shared schemas in `zcash-privacy-stack` and generated or vendored copies in component repositories as needed.
