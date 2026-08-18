# Zakura and Zebra Upstream Strategy

## Goals

- Keep the Zakura fork straightforward to compare with `zakura-core/zakura`.
- Minimize the number and size of privacy-specific integration seams.
- Avoid placing cross-stack code or documentation into the node fork.
- Make upstream merges routine rather than a later reconstruction project.
- Reuse stable policy and conformance behavior when adding Zebra, without assuming source-level equivalence.

## Zakura remotes

The Zakura fork should normally have:

```text
origin    project-maintained Zakura fork
upstream  zakura-core/zakura
```

Track the tested base and project revision in the integration repository:

```toml
[components.zakura]
repository = "https://github.com/<project>/zakura"
upstream = "https://github.com/zakura-core/zakura"
revision = "<tested-project-commit>"
upstream_base = "<merged-upstream-commit>"
path = "../zakura"
```

## Narrow node seams

Prefer these integration points:

1. an additive private/local queue request carrying admission context;
2. a node-independent admission-policy crate;
3. a separate verified private pool;
4. one release/promotion operation into the ordinary public mempool;
5. configuration and diagnostics isolated in privacy-specific modules;
6. ordinary public gossip, RPC, indexer, and mining paths left unchanged after promotion.

Avoid:

- adding privacy policy branches throughout unrelated public query paths;
- changing transaction or block representations;
- storing cross-stack schemas directly in node internals;
- coupling OHTTP or TEE code to the node;
- copying the same integration code into Zebra later.

## Upstream update procedure

For a routine Zakura upstream update:

1. fetch `upstream`;
2. record the current project revision and upstream target;
3. merge or rebase according to the fork's chosen policy;
4. resolve mechanical conflicts without adding new privacy behavior;
5. run Zakura's normal test suite;
6. run the privacy package tests;
7. run the Zakura inspection command demonstrating private admission and release;
8. update the integration repository's `revision` and `upstream_base`;
9. commit the upstream update separately from feature development.

A small script should report changes in privacy-sensitive upstream areas, including:

- mempool request and response types;
- verifier result types;
- successful insertion and eviction;
- chain-tip reset and retry;
- mempool events and pending gossip;
- local transaction submission;
- block-template selection;
- transaction lookup;
- logging and metrics around transaction processing.

The report is advisory. It helps direct human inspection but does not replace tests.

## Zebra timing

Begin the Zebra adapter only after:

- Zakura private admission and release work end to end;
- the node-independent admission crate has a stable public API;
- at least one ordinary Zakura upstream update has been completed successfully;
- shared conformance scenarios are expressed without Zakura-specific types.

Create a normal Zebra fork with its own `upstream` remote. Implement a Zebra-specific adapter around the same conceptual contracts. Do not add conditional Zakura/Zebra code throughout one node repository.

## Shared crate extraction

When Zebra becomes the second consumer, evaluate extraction of the node-independent admission crate. The extraction should be a dedicated change with:

- unchanged behavior;
- stable serialized interfaces where needed;
- independent tests;
- explicit versioning;
- revision pins updated in the integration repository.
