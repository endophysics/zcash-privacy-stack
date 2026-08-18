# Zcash Privacy Stack

This integration repository keeps component pins and local operator commands. It requires Python 3.11 or later, `uv`, and `just`.

## Layout And Zakura Pin

Keep the integration repository and component checkouts as sibling directories:

```text
workspace/
|-- zcash-privacy-stack/
`-- zakura/
```

`components.lock.toml` records three distinct Zakura values: `repository` is the project checkout's `origin`, `upstream` is the Zakura upstream remote, and `revision` is the exact project commit to detach at. The `upstream_base` pin records the corresponding upstream base. Do not replace these roles or edit pins casually.

## Commands

```bash
just bootstrap
just status
just inspect
just policy-example
just policy-validate examples/privacy-policy-v1.json
just policy-validate --check-freshness --at 2026-06-01T00:00:00Z examples/privacy-policy-v1.json
just interface-summary
```

`bootstrap` clones missing configured siblings and safely detaches them at their pins. It refuses dirty trees and mismatched remotes rather than resetting, cleaning, or force-checking out. `status` emits machine-readable component records. `inspect` adds the current WP00 boundary: Zakura checkout/status is the only inspection boundary, and no end-to-end service exists yet.

Unconfigured optional components are reported and skipped; they do not create repositories. Configured optional components retain their pin and are bootstrapped when present in the lock.

No component is vendored here. Do not use Git submodules, subtrees, or optional-repository creation.

## Offline Privacy Contract Commands

`policy-example` emits the checked-in privacy-policy example with structured explanations. `policy-validate` validates a local privacy-policy JSON file using the local schema and semantic rules. Its default mode checks structure and semantics without freshness because the example has a bounded validity window. Add `--check-freshness --at RFC3339-UTC` for deterministic freshness validation, as shown above. `interface-summary` emits the static contract identifiers, version fields, and cross-contract concept metadata as structured JSON.

These commands do not retrieve documents or schemas and do not establish document authenticity, authorization, signatures, or advertised behavior. A successful result only reports compatibility with the locally supported contract. See [interface versioning](docs/INTERFACE_VERSIONING.md) for independent version domains, stable identifiers, and additive compatibility, and [compatibility and adoption](docs/COMPATIBILITY_AND_ADOPTION.md) for adoption guidance.

## Local Verification

Tests use only temporary local Git fixtures:

```bash
uv run pytest
uv run ruff check .
uv run basedpyright
```

Cross-stack ADRs are stored in `docs/adr/`. Component-local decisions are stored with component code.
