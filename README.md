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
```

`bootstrap` clones missing configured siblings and safely detaches them at their pins. It refuses dirty trees and mismatched remotes rather than resetting, cleaning, or force-checking out. `status` emits machine-readable component records. `inspect` adds the current WP00 boundary: Zakura checkout/status is the only inspection boundary, and no end-to-end service exists yet.

Unconfigured optional components are reported and skipped; they do not create repositories. Configured optional components retain their pin and are bootstrapped when present in the lock.

No component is vendored here. Do not use Git submodules, subtrees, or optional-repository creation.

## Local Verification

Tests use only temporary local Git fixtures:

```bash
uv run pytest
uv run ruff check .
uv run basedpyright
```

Cross-stack ADRs are stored in `docs/adr/`. Component-local decisions are stored with component code.
