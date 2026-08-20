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
just inspect-zakura
just policy-example
just policy-validate examples/privacy-policy-v1.json
just policy-validate --check-freshness --at 2026-06-01T00:00:00Z examples/privacy-policy-v1.json
just interface-summary
```

`bootstrap` clones missing configured siblings and safely detaches them at their pins. It refuses dirty trees and mismatched remotes rather than resetting, cleaning, or force-checking out. `status` emits machine-readable component records. `inspect` retains its existing checkout/status boundary and semantics.

`inspect-zakura` is the local acceptance observer. It prints a stable identity preamble containing the pinned node commit, upstream base, managed-zcashd P2P observer, and host, then delegates directly to Zakura's `just inspect-private-release` recipe from the pinned, clean Zakura checkout. Zakura streams an identifier-free transcript containing the policy hash, exact release configuration, numeric private/public mempool counts, connected zcashd P2P observer event, and coarse transaction timeline. The wrapper does not duplicate that orchestration or parse and restate its output.

The observer accepts either a detached checkout or an attached branch when `HEAD` exactly matches the pin and the worktree is clean. `bootstrap` and `status` retain their stricter remote and detached-HEAD invariants. To vary local inspection timing, set `TEST_ZCASHD_COMPAT_PRIVATE_RELEASE_EPOCH_MS`, `TEST_ZCASHD_COMPAT_PRIVATE_RELEASE_MINIMUM_DELAY_MS`, and `TEST_ZCASHD_COMPAT_PRIVATE_RELEASE_MAXIMUM_DELAY_MS`; Zakura validates the values and prints the resulting policy and timing records.

Managed zcashd releases are unavailable on Darwin arm64/aarch64. On those hosts, when `TEST_ZCASHD_PATH` is unset, the command reports `execution=unavailable`, a stable reason, and `override=TEST_ZCASHD_PATH`, then exits successfully without invoking `just` or Cargo. Set `TEST_ZCASHD_PATH` only to a trusted executable zcashd file to run the same Zakura acceptance surface; the wrapper does not download or install zcashd. Invalid overrides fail before invocation.

This command is local inspection evidence rather than a production logging mode. Its stable transcript excludes transaction and admission identifiers. `PATH`, the resolved local `just` executable, `TEST_ZCASHD_PATH`, and the inherited process environment are trusted operator inputs; do not run the command in an attacker-controlled CI environment. No transaction identifiers are added to default production logs.

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
