# Foundation 67 — Isolated Ed25519 Receipt Signing

- **Status:** implemented (isolated PureEd25519 sign/verify over Foundation 66 material)
- **Baseline:** `0dcbcbfd894a7ff0caa0fb41ccca2f2a6d4ec66d` (Foundation 66 on main)
- **Branch:** `foundation67-isolated-ed25519-receipt-signing`
- **Normative parents:** Foundation 64 contract; Foundation 65 map; Foundation 66 schema/canonical material

## 1. Paths and symbols

| Path | Role |
|---|---|
| `coin/uaii_signed_receipt.py` | Extended with isolated sign/verify |
| `tests/test_uaii_signed_receipt_signing.py` | Disposable-key focused F67 tests |
| `tests/test_uaii_signed_receipt.py` | Foundation 66 suite (flags updated) |
| `docs/foundation67_isolated_ed25519_receipt_signing.md` | This record |

Primary symbols:

- `sign_unsigned_receipt_facts`
- `verify_signed_receipt_facts`
- `required_signer_identity` / `required_signer_identity_field`
- `public_key_id_for_raw`
- `STATUS_SIGNER_IDENTITY_FIELD` (Foundation 64 §5.6)

## 2. Crypto dependency

| Item | Evidence |
|---|---|
| Library | `cryptography==49.0.0` |
| Declaration | `requirements-m2m.txt` (unchanged by Foundation 67) |
| Convention | PureEd25519 via `Ed25519PublicKey.verify` (same family as `coin/m2m_verifier.py` verify-only path and creator-wallet verifiers) |
| Signing boundary | Caller-supplied `Callable[[bytes], bytes]` — module imports **public-key verify only**, never `Ed25519PrivateKey` |

## 3. Signing and verification contract

1. Validate unsigned facts (Foundation 66).
2. Enforce §5.6 identity binding: `expected_signer_identity` MUST equal the
   required identity field for `settlement_status`.
3. Build `signable_bytes` exclusively through `build_signable_bytes`.
4. Invoke isolated signer callable on those exact bytes; require raw 64-byte
   signature; hex-encode for receipt fields.
5. Confirm signature verifies against the declared `signer_public_key`.
6. Insert digest + signature with empty `receipt_id`; compute `receipt_id`;
   return complete 27-field facts.

Verification:

1. Schema-validate signed facts.
2. Algorithm must be `ed25519-pure/v0.1`.
3. Resolve §5.6 required identity.
4. Reconstruct unsigned facts; recompute digest (`digest_mismatch` on drift).
5. PureEd25519 verify over reconstructed signable bytes (`signature_invalid`).
6. Recompute receipt ID (`receipt_id_invalid`).

Canonicalization remains CanonUaii only. M2M canonicalize is forbidden.

## 4. Private-material boundary

- Production module never imports private-key types or accepts private bytes.
- Signer callable is the sole private-key boundary; keys stay with the caller.
- Exceptions expose stable codes only (no payloads, keys, or signable bytes).
- No logging of private or signature-input material.
- No persistent key storage, PEM, seed fixtures, or env-based secrets.

## 5. Disposable-key testing method

- Tests call `Ed25519PrivateKey.generate()` in-process per case.
- Private keys remain in memory; never written to files, fixtures, docs, or
  assertions.
- Assertions use public keys, signatures, digests, and receipt IDs only.
- Temporary-directory probe confirms no key artifacts are created.

## 6. Implemented vs deferred

**Implemented:** PureEd25519 sign/verify, digest/receipt-ID integrity, §5.6
identity binding for the signing API, algorithm enforcement, fail-closed
tamper paths.

**Deferred:** approval execution, replay state, status transitions beyond
schema enums, spending/settlement, UAII operation wiring, adapters, persistent
signer selection, networking, runtime services.

## 7. Invariants

| Flag | Value |
|---|---|
| `execution_authorized` | `false` |
| `persistent_keys_created` | `false` |
| `private_material_exposed` | `false` |
| `spend_authorized` | `false` |
| `settlement_authorized` | `false` |
| `ledger_mutated` | `false` |
| `runtime_activated` | `false` |

## 8. Tests executed

Recorded at commit time by the Foundation 67 validation run (F67 signing suite,
full F66 receipt suite, UAII/canonicalization, protocol conformance /
protected economics).

## 9. Document history

| Version | Change |
|---|---|
| 0.1 | Isolated Ed25519 receipt signing/verification over Foundation 66 |
