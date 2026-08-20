# Compatibility and Independent Adoption

## Compatibility dimensions

- **Consensus compatibility:** transactions and blocks remain ordinary Zcash data.
- **P2P compatibility:** existing peers accept released transactions without modification.
- **Wire compatibility:** existing clients can still use existing RPC/gRPC messages.
- **Behavioral compatibility:** existing clients remain coherent during delayed public propagation.
- **Trust compatibility:** claimed privacy does not depend on one operator controlling roles assumed independent.

## Independently adoptable changes

| Change | Adopter | Requires other changes | Main gain |
|---|---|---|---|
| Zakura private pool and temporal release | Node operator | No wallet or peer change for a dedicated endpoint | Weakens external timing correlation |
| Fixed logical P2P egress | Node operator | None | Removes client-geographic egress signals |
| Metadata-minimized node operation | Node operator | None | Reduces retained and accidental metadata |
| Wallet range bucketing | Wallet developer | Existing compatible server | Hides exact synchronization start |
| Common wallet polling | Wallet developer | None | Reduces event-driven activity fingerprinting |
| Zaino privacy endpoint | Server operator | Client opt-in for restricted methods | Reduces server-side metadata collection |
| Canonical read objects | Server operator can publish | Wallet use required for privacy benefit | Makes reads common and cacheable |
| OHTTP private write | Wallet + gateway + independent relay | Standard relay availability | Separates client IP from transaction content |
| TEE attestation | Gateway + wallet | Supported platform | Constrains gateway-host access |
| Active-attack hardening | Several components | Depends on selected mechanisms | Raises probe, spam, replay, and rollback cost |

## Legacy endpoint strategy

Ordinary immediate submission is the universal safe operational fallback and recommendation for every evaluated legacy release. This operational guidance is distinct from each scenario's machine `rollout_classification`: completed directly supported Vizor unit scenarios may record `ordinary_immediate_endpoint`, while unavailable and source-derived non-empirical rows remain `inconclusive`. `inconclusive` never authorizes delay and therefore falls back operationally to immediate submission. The current WP06 evidence does not authorize `private_endpoint_only`, and opt-in batching on legacy endpoints remains unsupported. The deterministic [`wp06_delayed_admission_runner.py`](../scripts/wp06_delayed_admission_runner.py) checks representative invariants only; it is not wallet execution, endpoint integration, or `integrated_empirical` evidence and cannot authorize delayed admission. A private endpoint requires future integrated empirical evidence; the maximum supported private delay is unestablished. Do not create a cross-stack ADR until that evidence exists. See [WP06 legacy-client compatibility](LEGACY_CLIENT_COMPATIBILITY.md) for the pinned matrices, evidence limits, and commands.

## No network upgrade requirement

The intended implementation does not change:

- transaction format;
- block format;
- Zcash consensus;
- ordinary peer protocol semantics after release.

This is a deployment and client-infrastructure privacy architecture rather than a consensus upgrade.
