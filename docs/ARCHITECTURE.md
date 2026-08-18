# Architecture

## Purpose

Reduce network-level metadata leakage for Zcash light-wallet users through independently adoptable write-side and read-side improvements.

## Private write path

```text
Wallet
  │
  │ common policy retrieval
  │ standard OHTTP encapsulation
  │ fixed request padding
  ▼
Independent OHTTP relay
  │
  │ sees client network metadata
  │ cannot decrypt transaction
  ▼
Private gateway
  │
  │ decrypts request
  │ optionally runs in an attested TEE
  │ sees relay rather than client IP
  ▼
Node private-admission interface
  │
  │ verifies transaction immediately
  ▼
Separate verified private pool
  │
  │ no public mempool effect
  │ minimum residence time
  │ temporal batching
  ▼
Atomic promotion into ordinary public mempool
  │
  │ unchanged public events and gossip
  ▼
Fixed logical Zcash P2P egress
```

The relay creates network-identity/content separation. The TEE constrains gateway-host access. The private pool prevents pre-release leakage and public-state oracles. Temporal release weakens direct submission-to-broadcast timing linkage. Fixed egress replaces wallet-specific origins with one service origin.

## Read path

```text
Wallet
  │
  │ rounded range requests or canonical objects
  │ common polling schedule
  ▼
Privacy-oriented Zaino/light-client infrastructure
  │
  │ common compact-block ranges
  │ full-block or block-group transaction bundles
  │ subtree-root bundles
  │ common mempool epochs
  ▼
Local wallet trial decryption and scanning
```

The read path aims to make requests describe common public data rather than a particular wallet. Detecting a relevant note should not trigger a distinctive network request.

## Independent adoption

### Operator-only node track

A Zakura operator can deploy:

- private verified admission;
- temporal release;
- fixed logical egress;
- metadata-minimized node operation.

This improves resistance to external P2P and timing observers even when legacy wallets submit directly to the operator.

### Wallet-only read track

A wallet can deploy:

- range bucketing;
- common polling;
- read/write session separation;
- reduced personalized mempool queries.

This improves metadata privacy against existing compatible light-client servers.

### Private write track

One wallet, one gateway operator, and one independent standard relay can deploy OHTTP private submission without a network upgrade.

### Full stack

Combining OHTTP, TEE attestation, private node admission, temporal mixing, fixed egress, and common read data provides the strongest intended privacy properties.

## Node boundary

The node must not contain OHTTP or TEE logic. Its narrow responsibility is:

```text
serialized transaction + admission context
        ↓
verification
        ↓
private accepted state
        ↓
release/promotion
```

This boundary is intended to support Zakura first and Zebra later.
