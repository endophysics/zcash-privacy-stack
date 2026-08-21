# Legacy Client Compatibility

## Scope and conclusion

This report evaluates these immutable wallet releases:

| Client | Release | Commit |
|---|---|---|
| Vizor | `0.0.48` | [`d60ea8ef853d02e6ea31573e75c5603db1d7addb`](https://github.com/chainapsis/vizor-wallet/tree/d60ea8ef853d02e6ea31573e75c5603db1d7addb) |
| Zodl Android | `3.9.3-2393` | [`39cf778399dc49e2fa24fe08b9b1cd83adf0fa7f`](https://github.com/zodl-inc/zodl-android/tree/39cf778399dc49e2fa24fe08b9b1cd83adf0fa7f) |
| Zodl iOS | `3.9.5` | [`993d31f333f6fe118819f5c8464008801c3f8908`](https://github.com/zodl-inc/zodl-ios/tree/993d31f333f6fe118819f5c8464008801c3f8908) |

The evidence does not authorize delayed admission for any release. Ordinary immediate submission is the universal safe operational fallback and recommendation for every evaluated release. This operational guidance is distinct from each scenario's machine `rollout_classification`: completed directly supported Vizor unit scenarios may record `ordinary_immediate_endpoint`, while unavailable and source-derived non-empirical rows remain `inconclusive`. `inconclusive` never authorizes delay and therefore falls back operationally to immediate submission. The maximum supported private delay is unestablished, not a guessed duration.

## Evidence grades

- `local_rust_unit` means the exact pinned Vizor Rust unit tests ran locally. It does not cover Flutter, a wallet runtime, managed zcashd, or delayed admission.
- `source_derived` means the pinned wallet-release source was reviewed. `Execution.COMPLETE` means that evidence collection completed. It does not turn source review into empirical execution.
- `local_flutter_unavailable` means the planned Flutter lane was not run because its toolchain was unavailable.
- `unavailable` means the managed-zcashd lane was not run on Darwin arm64.
- `integrated_empirical` is reserved for future client-through-endpoint execution that observes submission, delayed public absence, release, retries or status queries, fallback or endpoint changes, and final client state.

`PASS` and `FAIL` below report only the named check at its stated evidence grade. `NOT_RUN` makes no behavior claim. Flutter, managed-zcashd, Zodl runtime, and delayed admission were not exercised.

## Output and validation contract

The `just inspect-legacy-client CLIENT=...` recipe accepts the documented `CLIENT=vizor`, `CLIENT=zodl-android`, or `CLIENT=zodl-ios` syntax and the optional `FORMAT=human` or `FORMAT=jsonl` syntax. It safely shell-quotes both recipe values before passing them to the CLI, so shell metacharacters remain inert invalid arguments rather than commands. Vizor defaults to the sibling checkout at `../vizor-wallet`; direct CLI `--vizor-checkout` overrides nonstandard layouts.

Human output always renders the same seven authoritative stages for every scenario: submission call, server acceptance, client-visible response, client retry or status query, public release, client final state, and fallback or endpoint change. Each stage is exactly `observed`, `not_observed`, or `not_run`. `observed` records only a stage present in collected evidence, `not_observed` records its absence from completed evidence, and `not_run` marks unavailable execution. Every unavailable scenario also emits its stable typed `unavailable_reason`. No timeline stage is inferred from source review or unavailable execution.

JSONL records validate against the checked [`legacy-client-result.schema.json`](../interfaces/legacy-client-result.schema.json). The schema is generated from and checked for equality with the Pydantic model. It mirrors the semantic invariants: `checks` is nonempty; unavailable execution requires a typed reason, only `NOT_RUN` checks, an empty timeline, and `inconclusive` rollout; complete execution forbids an unavailable reason; unavailable evidence requires unavailable execution; and `local_rust_unit` or `source_derived` evidence cannot authorize `private_endpoint_only`.

## Vizor matrix

Release `0.0.48`, commit `d60ea8ef853d02e6ea31573e75c5603db1d7addb`.

| Scenario | Check | Status | Evidence | Execution | Adapter classification |
|---|---|---|---|---|---|
| `temporary_public_absence` | `client_behavior` | `NOT_RUN` | `unavailable` | `unavailable` | `inconclusive` |
| `exact_retry` | `duplicate_release` | `PASS` | `local_rust_unit` | `complete` | `ordinary_immediate_endpoint` |
| `lost_response_retry` | `client_behavior` | `PASS` | `local_rust_unit` | `complete` | `ordinary_immediate_endpoint` |
| `transaction_status_reconciliation` | `status_polling` | `PASS` | `local_rust_unit` | `complete` | `ordinary_immediate_endpoint` |
| `mempool_observation` | `status_polling` | `PASS` | `local_rust_unit` | `complete` | `ordinary_immediate_endpoint` |
| `server_switching` | `client_behavior` | `NOT_RUN` | `local_flutter_unavailable` | `unavailable` | `inconclusive` |
| `direct_fallback` | `direct_fallback` | `NOT_RUN` | `local_flutter_unavailable` | `unavailable` | `inconclusive` |
| `node_restart` | `client_behavior` | `NOT_RUN` | `unavailable` | `unavailable` | `inconclusive` |
| `pre_release_conflict` | `client_behavior` | `NOT_RUN` | `unavailable` | `unavailable` | `inconclusive` |
| `release_deadline_preservation` | `release_deadline` | `NOT_RUN` | `unavailable` | `unavailable` | `inconclusive` |

The four passing scenarios are grounded by five exact tests. For each registry entry, the adapter first uses Cargo test discovery to require the complete exact named test, then runs that exact test with `cargo test --locked --offline`. A missing name, test failure, absent locked dependency cache, or other offline Cargo failure stops collection before any result is printed. This fail-closed path prevents a filtered zero-test run or network-dependent resolution from becoming evidence.

- Lost-response raw-byte preservation: [`resubmit_includes_valid_outbound_pending`](https://github.com/chainapsis/vizor-wallet/blob/d60ea8ef853d02e6ea31573e75c5603db1d7addb/rust/src/wallet/sync/transactions.rs#L5542-L5554)
- Exact-retry duplicate acceptance: [`pczt_duplicate_response_stores_locally_and_returns_broadcasted`](https://github.com/chainapsis/vizor-wallet/blob/d60ea8ef853d02e6ea31573e75c5603db1d7addb/rust/src/wallet/sync/pczt.rs#L1156-L1170)
- Lost-response ambiguous-state preservation: [`pczt_non_deadline_transport_failure_remains_ambiguous`](https://github.com/chainapsis/vizor-wallet/blob/d60ea8ef853d02e6ea31573e75c5603db1d7addb/rust/src/wallet/sync/pczt.rs#L1190-L1212)
- Status retry classification: [`get_transaction_transient_errors_retry_as_network`](https://github.com/chainapsis/vizor-wallet/blob/d60ea8ef853d02e6ea31573e75c5603db1d7addb/rust/src/wallet/sync_engine/enhance.rs#L635-L650)
- Mempool observation: [`lookup_known_pending_tx_finds_unmined_tx`](https://github.com/chainapsis/vizor-wallet/blob/d60ea8ef853d02e6ea31573e75c5603db1d7addb/rust/src/wallet/sync_engine/mempool.rs#L1038-L1048)

## Zodl Android matrix

Release `3.9.3-2393`, commit `39cf778399dc49e2fa24fe08b9b1cd83adf0fa7f`. All rows are `source_derived`, `complete`, and `inconclusive`.

| Scenario | Check | Status |
|---|---|---|
| `temporary_public_absence` | `client_behavior` | `NOT_RUN` |
| `exact_retry` | `duplicate_release` | `NOT_RUN` |
| `lost_response_retry` | `client_behavior` | `PASS` |
| `transaction_status_reconciliation` | `status_polling` | `PASS` |
| `mempool_observation` | `status_polling` | `NOT_RUN` |
| `server_switching` | `client_behavior` | `PASS` |
| `direct_fallback` | `direct_fallback` | `FAIL` |
| `node_restart` | `client_behavior` | `NOT_RUN` |
| `pre_release_conflict` | `client_behavior` | `NOT_RUN` |
| `release_deadline_preservation` | `release_deadline` | `NOT_RUN` |

Immutable wallet-source evidence:

- Lost-response handling: [`MultiEndpointTransactionSubmitter.kt`, lines 190 to 208](https://github.com/zodl-inc/zodl-android/blob/39cf778399dc49e2fa24fe08b9b1cd83adf0fa7f/ui-lib/src/main/java/co/electriccoin/zcash/ui/common/datasource/MultiEndpointTransactionSubmitter.kt#L190-L208) and [lines 312 to 345](https://github.com/zodl-inc/zodl-android/blob/39cf778399dc49e2fa24fe08b9b1cd83adf0fa7f/ui-lib/src/main/java/co/electriccoin/zcash/ui/common/datasource/MultiEndpointTransactionSubmitter.kt#L312-L345)
- Status reconciliation: [`TransactionRepository.kt`, lines 96 to 115](https://github.com/zodl-inc/zodl-android/blob/39cf778399dc49e2fa24fe08b9b1cd83adf0fa7f/ui-lib/src/main/java/co/electriccoin/zcash/ui/common/repository/TransactionRepository.kt#L96-L115) and [lines 206 to 348](https://github.com/zodl-inc/zodl-android/blob/39cf778399dc49e2fa24fe08b9b1cd83adf0fa7f/ui-lib/src/main/java/co/electriccoin/zcash/ui/common/repository/TransactionRepository.kt#L206-L348)
- Server switching: [`AutomaticServerRepository.kt`, lines 83 to 106](https://github.com/zodl-inc/zodl-android/blob/39cf778399dc49e2fa24fe08b9b1cd83adf0fa7f/ui-lib/src/main/java/co/electriccoin/zcash/ui/common/repository/AutomaticServerRepository.kt#L83-L106)
- Concurrent submission is not direct fallback: [`MultiEndpointTransactionSubmitter.kt`, lines 135 to 189](https://github.com/zodl-inc/zodl-android/blob/39cf778399dc49e2fa24fe08b9b1cd83adf0fa7f/ui-lib/src/main/java/co/electriccoin/zcash/ui/common/datasource/MultiEndpointTransactionSubmitter.kt#L135-L189) and [lines 229 to 257](https://github.com/zodl-inc/zodl-android/blob/39cf778399dc49e2fa24fe08b9b1cd83adf0fa7f/ui-lib/src/main/java/co/electriccoin/zcash/ui/common/datasource/MultiEndpointTransactionSubmitter.kt#L229-L257)

## Zodl iOS matrix

Release `3.9.5`, commit `993d31f333f6fe118819f5c8464008801c3f8908`. All rows are `source_derived`, `complete`, and `inconclusive`.

| Scenario | Check | Status |
|---|---|---|
| `temporary_public_absence` | `client_behavior` | `NOT_RUN` |
| `exact_retry` | `duplicate_release` | `NOT_RUN` |
| `lost_response_retry` | `client_behavior` | `PASS` |
| `transaction_status_reconciliation` | `status_polling` | `NOT_RUN` |
| `mempool_observation` | `status_polling` | `NOT_RUN` |
| `server_switching` | `client_behavior` | `PASS` |
| `direct_fallback` | `direct_fallback` | `NOT_RUN` |
| `node_restart` | `client_behavior` | `NOT_RUN` |
| `pre_release_conflict` | `client_behavior` | `NOT_RUN` |
| `release_deadline_preservation` | `release_deadline` | `NOT_RUN` |

Immutable wallet-source evidence:

- Lost-response handling: [`SDKSynchronizerLive.swift`, lines 628 to 647](https://github.com/zodl-inc/zodl-ios/blob/993d31f333f6fe118819f5c8464008801c3f8908/secant/Sources/Dependencies/SDKSynchronizer/SDKSynchronizerLive.swift#L628-L647)
- Server switching: [`AutoServerSelectionLiveKey.swift`, lines 52 to 91](https://github.com/zodl-inc/zodl-ios/blob/993d31f333f6fe118819f5c8464008801c3f8908/secant/Sources/Dependencies/AutoServerSelection/AutoServerSelectionLiveKey.swift#L52-L91)

## SDK evidence boundary

The Zodl wallet release trees do not immutably pin SDK revisions. Android has an empty `SDK_COMMIT_PIN` and declares `ZCASH_SDK_VERSION=3.0.2-SNAPSHOT` in [`gradle.properties`, lines 108 to 127](https://github.com/zodl-inc/zodl-android/blob/39cf778399dc49e2fa24fe08b9b1cd83adf0fa7f/gradle.properties#L108-L127) and [lines 201 to 204](https://github.com/zodl-inc/zodl-android/blob/39cf778399dc49e2fa24fe08b9b1cd83adf0fa7f/gradle.properties#L201-L204). iOS points to the local package `../zcash-swift-wallet-sdk` in [`project.pbxproj`, lines 1302 to 1306](https://github.com/zodl-inc/zodl-ios/blob/993d31f333f6fe118819f5c8464008801c3f8908/secant.xcodeproj/project.pbxproj#L1302-L1306).

SDK-only behavior is therefore excluded from wallet-release evidence. No behavior from an unpinned SDK snapshot is cited as a Zodl release finding.

## Rollout guidance

- Operational fallback: use ordinary immediate submission for every evaluated release.
- Machine `ordinary_immediate_endpoint`: completed directly supported Vizor unit scenarios may record this classification.
- Machine `inconclusive`: unavailable and source-derived non-empirical rows retain this classification. It never authorizes delay, so the operational fallback is immediate submission.
- `private_endpoint_only`: not authorized. It requires future integrated empirical evidence for the pinned client and endpoint behavior.
- Opt-in legacy endpoint batching: unsupported.

The available evidence does not establish a safe numeric delay. No cross-stack ADR is created until integrated empirical evidence exists.

## Representative delayed-admission automation

[`scripts/delayed_admission_runner.py`](../scripts/delayed_admission_runner.py) is deterministic representative-only automation. Its typed local state proves these model invariants:

- an exact retry is idempotent;
- repeated release calls cannot duplicate release;
- a retry cannot reset the first logical deadline;
- a direct-fallback route is detected;
- status polling is detected only for the admitted transaction.

The runner uses representative transaction keys and logical deadline tokens without a clock, wallet, network, or endpoint. It is not wallet execution, endpoint integration, delayed-admission execution, or `integrated_empirical` evidence. Its results do not change any client matrix or authorize `private_endpoint_only`.

## Reproduce the report records

Human output is the default:

```bash
just inspect-legacy-client CLIENT=vizor
just inspect-legacy-client CLIENT=zodl-android
just inspect-legacy-client CLIENT=zodl-ios
```

JSON Lines output uses the same ordered ten-scenario records:

```bash
just inspect-legacy-client CLIENT=vizor FORMAT=jsonl
just inspect-legacy-client CLIENT=zodl-android FORMAT=jsonl
just inspect-legacy-client CLIENT=zodl-ios FORMAT=jsonl
```

The JSONL contract is [`interfaces/legacy-client-result.schema.json`](../interfaces/legacy-client-result.schema.json). Vizor inspection also requires the clean sibling checkout at the pinned commit, discovers each exact named test, and runs it with locked offline Cargo before producing records. Zodl commands render the pinned source-review matrices and do not run either wallet.

For a reproducible Linux toolchain and an immutable Vizor checkout, run `just container-test`. It pins Python, `uv`, `just`, Rust, and the Vizor Git revision, then runs the full Python quality gates and exact offline Cargo evidence tests. `just container-inspect-legacy-client CLIENT=... FORMAT=...` renders records from the same image without relying on host toolchains or a mutable sibling checkout.
