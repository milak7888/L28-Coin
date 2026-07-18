# L28 Creator Wallet Control Proof v0.1

**Status:** Specification only; non-activation.

## Purpose

This protocol defines an offline public proof that a signer controls the
private key corresponding to the historical L28 creator public identity. A
successful proof establishes key control only. It does not prove a live balance,
spendability, allocation ownership, transfer authority, or network status.

## Fixed public identity

Version 0.1 accepts only this public identity:

- Creator alias: `L28_CREATOR`
- Public key:
  `c03a4ffd7e94cba2199f6a95a94f13d5aa0c6090f0c3f06aa59f6afc8dd26ff5`
- Address:
  `L28d7d0903ab9e10e706c418c31fac95109577cdea6`

The address must equal `L28` plus the first 40 lowercase hexadecimal
characters of `SHA-256(public_key_bytes)`.

## Proof schema

A proof is exactly one JSON object:

```json
{
  "proof_version": "l28-creator-wallet-control-proof/v0.1",
  "domain": "l28-creator-wallet-control-proof/v0.1",
  "challenge_id": "64 lowercase hexadecimal characters",
  "public_key": "64 lowercase hexadecimal characters",
  "address": "L28...",
  "signature": "128 lowercase hexadecimal characters"
}
```

No fields may be missing or added. Duplicate JSON keys, non-finite values,
invalid UTF-8, or non-object values must fail closed.

## Signature preimage

The signature is over the proof object with `signature` omitted. Its bytes are
the UTF-8 encoding of canonical JSON with:

- keys sorted lexicographically;
- `ensure_ascii=false`;
- separators exactly `(",", ":")`;
- no NaN or infinity values.

The signature uses Ed25519 and is lowercase hexadecimal encoding of the 64 raw
signature bytes. The public key is the 32 raw key bytes encoded as lowercase
hexadecimal.

This is intentionally wallet-compatible with the existing L28 wallet signing
format. It is not an M2M envelope and must not call the M2M envelope verifier.

## Challenge and replay boundary

`challenge_id` is a caller-supplied, fresh, unpredictable 32-byte value encoded
as lowercase hexadecimal. The verifier must require an exact caller-supplied
expected challenge ID.

The offline verifier has no storage and cannot globally prevent replay. It
therefore proves only that this exact challenge was signed. Challenge issuance,
expiry, one-time consumption, and audit retention remain external policy
responsibilities.

## Verification requirements

The future verifier must:

1. accept JSON text or bytes only;
2. enforce exact schema, lengths, lowercase encoding, and bounded input;
3. require the fixed version, domain, public key, and derived address;
4. require exact equality with the expected challenge ID;
5. verify using `Ed25519PublicKey.from_public_bytes(...).verify(...)`;
6. fail closed with stable sanitized result codes;
7. return immutable deterministic results without mutating caller input.

## Explicit exclusions

This protocol does not load wallet files, scan wallet directories, read private
keys or seed phrases, create signatures, build transactions, update a ledger,
select a canonical live balance, connect to peers, start a node, or authorize a
transfer.

## Test-vector requirement

Before implementation is released, public vectors must cover a valid proof and
malformed input, address mismatch, public-key mismatch, challenge mismatch,
signature mismatch, duplicate-key, oversized-input, and replay-boundary cases.
Vectors must use a dedicated non-production test key, never the creator key.
