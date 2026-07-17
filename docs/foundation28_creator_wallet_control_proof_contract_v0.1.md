# Foundation 28 Creator Wallet Control-Proof Contract v0.1

**Status:** Specification only; non-activation.

## Purpose

This contract defines the public safety boundary for a future proof that a
holder controls the historical L28 creator wallet identity. It does not load a
wallet, read a private key, sign a challenge, create a transaction, construct a
node, validate a live ledger, or broadcast a message.

## Public identity reference

The historical creator alias is `L28_CREATOR`.

- Public key:
  `c03a4ffd7e94cba2199f6a95a94f13d5aa0c6090f0c3f06aa59f6afc8dd26ff5`
- Derived address:
  `L28d7d0903ab9e10e706c418c31fac95109577cdea6`

The address is derived by prefixing `L28` to the first 40 hexadecimal
characters of `SHA-256(public_key_bytes)`.

This establishes public-key/address consistency only. It does not prove
private-key possession or live spendability.

## Historical accounting boundary

Existing historical evidence reconciles:

- `28.0` L28 as the genesis reward associated with `L28_CREATOR`;
- `2,018,660.0` L28 in consolidation records targeting the derived address;
- `2,018,688.0` L28 as the resulting historical recorded reward total.

The value `2,824,584.0` is a historical declared-supply claim, not a creator
wallet balance. Historical continuity evidence does not prove that the
reconciled amount is a live or spendable wallet balance.

## Future control-proof requirements

A separately authorized implementation may verify wallet control only when:

1. A caller supplies a fresh, bounded, one-time public challenge.
2. The challenge has a dedicated domain and cannot be a transaction or approval.
3. The signer retains the private key locally; secrets are never logged,
   committed, transmitted, or requested by this contract.
4. Verification fails closed for malformed, expired, replayed, mismatched, or
   unverifiable challenges.
5. Public test vectors bind signature encoding and canonical challenge bytes.
6. A successful proof is key-control evidence only; it does not prove balance,
   authorize a transfer, or create spendability.

## Explicit exclusions

Foundation 28 does not open, recover, migrate, or export a wallet; request a
private key, password, seed phrase, or credential; sign a challenge or
transaction; select a live ledger; authorize transfers; construct a runtime
node; start a listener; or connect to peers.

## Required future authorization
