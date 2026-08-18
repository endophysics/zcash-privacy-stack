# ADR 0001: Separate Component Repositories with a Thin Integration Repository

- Status: Accepted
- Date: 2026-08-18

## Context

The privacy system spans a maintained Zakura fork, a later Zebra fork, an OHTTP gateway, an independently operated relay, wallet changes, and Zaino/light-client-server changes. The components should be independently adoptable, while the complete stack still needs a reproducible local checkout and an integrated inspection path.

The Zakura fork must remain easy to update from `zakura-core/zakura`. Putting cross-stack architecture, gateway code, wallet interfaces, and read-server work in that fork would obscure the node-specific delta and increase upstream maintenance cost.

Possible repository models included:

- using the Zakura fork as a monorepo;
- a new product monorepo containing imported node source;
- separate repositories pinned by a revision manifest;
- Git submodules;
- Git subtree;
- `git-subrepo`;
- an external patch stack.

## Decision

Use ordinary component repositories plus a thin `zcash-privacy-stack` integration repository.

The integration repository owns:

- cross-stack architecture and ADRs;
- shared interface schemas;
- exact tested component revisions in `components.lock.toml`;
- bootstrap and local orchestration;
- end-to-end inspection and conformance scenarios;
- relay deployment packaging.

Component code, tests, and component-local ADRs remain in their respective repositories.

Initially use a revision manifest and bootstrap script rather than Git submodules. Do not import Zakura, Zebra, or Zaino using subtree or `git-subrepo`.

A node-independent admission crate may initially live in the Zakura workspace. Extract it only after a second real consumer, expected to be Zebra, exists and the interface is stable.

## Assumptions

- Component repositories can be checked out as sibling directories.
- Cross-repository changes do not need to be atomic in one Git commit.
- The integration repository can pin branch commits during development and merged commits for stable combinations.
- A bootstrap script and lock file are sufficient for the current number of components.
- The system is pre-production, so the repository structure should optimize iteration and upstream clarity rather than release governance.

## Consequences

### Positive

- Zakura and Zebra remain conventional upstream forks.
- Cross-stack decisions have a neutral canonical home.
- Each component can be adopted and developed independently.
- The exact tested stack remains reproducible through pinned revisions.
- Coding agents work with ordinary Git repositories and branches.
- The project can adopt submodules later if one-checkout Git-native pinning becomes valuable.

### Negative

- Coordinated changes require commits in more than one repository.
- The integration lock file must be updated after component changes.
- Bootstrap and local orchestration scripts must manage sibling checkouts.
- Pull requests do not show the entire cross-component diff in one place.

## Rejected alternatives

### Put everything in Zakura

Fast for a disposable prototype, but makes the node fork the accidental owner of unrelated gateway, wallet, relay, and light-client work.

### Product monorepo with imported Zakura

Provides atomic refactoring but weakens the ordinary upstream-fork workflow and makes later Zebra support cumbersome.

### Git submodules immediately

Technically sound, but adds detached-HEAD and recursive-checkout workflow overhead before there is evidence that a manifest and bootstrap script are insufficient.

### Git subtree or `git-subrepo`

Would copy large, frequently updated node source into the integration repository and work against transparent upstream maintenance.

### External patch stack

Useful for auditing a final delta, but poor as the primary implementation and testing environment.
