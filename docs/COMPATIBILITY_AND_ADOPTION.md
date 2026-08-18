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

Retain ordinary immediate submission during development. Add private submission through an additive endpoint or explicit configuration. Enable delayed behavior for existing endpoints only after WP06 demonstrates compatible client behavior.

## No network upgrade requirement

The intended implementation does not change:

- transaction format;
- block format;
- Zcash consensus;
- ordinary peer protocol semantics after release.

This is a deployment and client-infrastructure privacy architecture rather than a consensus upgrade.
