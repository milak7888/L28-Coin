# L28 M2M Security Model v0.1

**Document:** L28 M2M Protocol v0.1 security model
**Status:** Specification (documentation only)
**Normative subordination:** This document is subordinate to [L28 Protocol v1.0.0](../../PROTOCOL.md) and to [protocol_v0.1.md](protocol_v0.1.md). L28 Protocol v1.0.0 prevails on conflict.

## 1. Purpose

This document defines security boundaries for L28 M2M Protocol v0.1.

It distinguishes:

1. M2M coordination evidence
2. L28 settlement evidence
3. Service-delivery evidence

Normative language follows RFC 2119 / RFC 8174 uppercase usage.

## 2. Machine identity

M2M identity is cryptographic machine identity.

- Machine identity is the Ed25519 public key as selected by [interoperability_profile_v0.1.md](interoperability_profile_v0.1.md).
- Key identifier format: `ed25519:<base64url-unpadded-raw-public-key>`.
- A sender is identified by `sender_public_key` and/or an existing L28 identity reference (`sender_identity`).
- The signed envelope binds machine identity to the claimed L28 settlement account string.
- Possession of the corresponding private key is what authorizes signatures.
- M2M identity MUST NOT be interpreted as proof of a human identity, legal personhood, jurisdiction, ownership, or accreditation.
- This profile does NOT create a new L28 address format.

Reserved L28 senders `COINBASE` and `__MINT__` MUST NOT be used as M2M party identities.

## 3. Evidence separation

### 3.1 M2M coordination evidence

Signed M2M envelopes prove that a machine asserted a coordination step. They do not move L28 value.

### 3.2 L28 settlement evidence

Only an existing L28 settlement record accepted under L28 Protocol v1.0.0 is settlement evidence. M2M `settlement_reference` messages are citations plus local verification claims, not substitutes for ledger truth.

### 3.3 Service-delivery evidence

A `service_receipt` proves a provider asserted completion. It does not independently prove objective correctness of the service result.

## 4. Signature verification

- Every operational M2M message MUST carry a non-empty `signature`.
- Receivers MUST verify the signature before accepting state effects.
- The required suite is `ed25519` (PureEd25519 / RFC 8032) per the interoperability profile.
- Foundation 5 implements offline verify-only validation in `coin/m2m_verifier.py` using PyCA `cryptography==49.0.0` (`Ed25519PublicKey` only).
- The verifier MUST NOT generate keys, sign messages, import `Ed25519PrivateKey`, or expose wallet/key-storage APIs.
- If the cryptographic backend is unavailable, verification MUST fail closed (`verification_backend_unavailable`).
- Unsigned Foundation 4 digest vectors MUST NOT be accepted as operational messages.
- Successful signature verification proves envelope authenticity under this profile. It does NOT prove service delivery, L28 transfer acceptance, irreversible finality, or settlement completion.
- Foundation 6 adds offline ordered-transcript validation in `coin/m2m_transcript_validator.py`. Transcript success is coordination consistency only: it MUST NOT create a persistent replay database, query a live ledger, or claim settlement finality. See [transcript_validation_v0.1.md](transcript_validation_v0.1.md).
- Foundation 7 adds an offline conformance CLI (`coin/m2m_conformance_cli.py`) that emits a deterministic stdout JSON report for one explicitly selected transcript. The CLI MUST NOT write report files, scan directories, sign messages, or claim settlement finality. See [conformance_cli_v0.1.md](conformance_cli_v0.1.md).
- Suite selection is an M2M profile decision and MUST NOT be presented as an L28 Protocol v1.0.0 consensus invariant.

## 5. Domain separation

Signing and verification MUST use the exact domain prefixes defined by [interoperability_profile_v0.1.md](interoperability_profile_v0.1.md):

- Payload: `L28-M2M-V0.1-PAYLOAD` + `0x00`
- Message ID: `L28-M2M-V0.1-MESSAGE` + `0x00`
- Signature: `L28-M2M-V0.1-SIGNATURE` + `0x00`

Requirements:

- M2M envelope signatures MUST NOT be valid input to L28 ledger signature checks merely by byte reuse without domain distinction.
- L28 ledger signatures MUST NOT be accepted as M2M envelope signatures.
- Verifiers MUST independently recompute `payload_hash` and `message_id`.

## 6. Canonical serialization

Protocol integers in JSON MUST be encoded without fractional parts. Floating-point encodings for those fields MUST be rejected.

M2M envelope canonicalization MUST follow L28-M2M Canonical JSON v0.1 in the interoperability profile (restricted RFC 8785-compatible subset). Digests use SHA-256 lowercase hex over domain-separated preimages.

This is an M2M interoperability rule and MUST NOT be claimed as an L28 Protocol v1.0.0 consensus primitive. L28 settlement transaction IDs remain those produced by Foundation 3 `compute_tx_id`.

## 7. Replay resistance

Implementations MUST reject or idempotently ignore replays using at least:

- accepted `message_id` set;
- accepted `nonce` values per sender within the retention window;
- `transaction_id` state;
- bound `l28_tx_id` values.

A replayed identical message MUST NOT apply side effects twice.

## 8. Nonce handling

- Each message MUST include a sender `nonce`.
- Nonces MUST be unique for the sender within the retention window used for replay defense.
- Nonce reuse with different message content MUST be rejected.
- Nonce generation quality is a local cryptographic responsibility; weak nonces increase replay risk and MUST be avoided.

## 9. Expiration and clock skew

- Envelope `expires_at`, quote expiration, and authorization expiration are mandatory controls.
- Receivers MUST enforce expiration before performing the corresponding state transition.
- Receivers SHOULD apply a configured clock-skew tolerance when comparing local clocks to `created_at` and expiration fields.
- Because L28 Protocol v1.0.0 does not publish an M2M skew constant, skew policy is local and MUST be fail-closed for clearly future `created_at` values outside tolerance.

## 10. Payload substitution protection

- `payload_hash` MUST equal the recomputed profile payload digest.
- Signature verification MUST cover the unsigned-envelope preimage that includes `payload_hash`.
- A mutated payload with a stale signature or stale `payload_hash` MUST fail validation.
- Transmitted `message_id` values MUST be recomputed; mismatches MUST reject.

## 11. Message-chain integrity

- `previous_message_id` MUST link each non-initial message to the prior accepted message for the same `transaction_id`.
- Broken chains MUST be rejected.
- Chain integrity protects against spliced quotes, authorizations, and receipts from unrelated conversations.

## 12. Duplicate and idempotent processing

- Duplicate `message_id` with identical canonical content MUST be handled idempotently.
- Duplicate `message_id` with divergent content MUST be rejected and SHOULD be treated as an attack signal.
- State transitions defined once MUST not be applied twice for the same triggering message.

## 13. Private-key isolation

- Private keys, seed phrases, and signing secrets MUST remain outside messages, payloads, and ordinary logs.
- Signing SHOULD occur in an isolated wallet or key module.
- M2M coordination services MUST NOT require export of seed phrases to peer machines.
- This specification does not enable autonomous spending by itself. Any spending path remains an L28 wallet/ledger concern under local policy.

## 14. Metadata minimization

- Parties SHOULD include only metadata necessary for the service and payment coordination.
- Service parameters, identifiers, timestamps, and amounts can reveal commercial relationships.
- Implementations SHOULD avoid placing unnecessary personal data in M2M payloads.

## 15. Denial-of-service boundaries

M2M v0.1 is a message schema and state machine, not a transport DoS control plane. Implementations SHOULD:

- bound payload size;
- bound outstanding transactions per peer;
- rate-limit unauthenticated or invalid traffic;
- fail closed on malformed input without expensive side effects.

These operational controls are local and outside L28 consensus.

## 16. Untrusted payload handling

- `service_params`, `service_terms`, and result objects are untrusted until validated by the receiving application.
- Receivers MUST NOT evaluate untrusted payloads as code.
- Receivers MUST NOT follow untrusted references in a way that bypasses settlement or signature checks.

## 17. Settlement verification against L28

Before `settled`:

1. Lookup the cited L28 record in the L28 source of truth.
2. Verify sender, receiver, amount, and transaction identity consistency with the authorization.
3. Recompute the cited L28 transaction ID from referenced transaction material using Foundation 3 `compute_tx_id` and reject on mismatch.
4. Reject if L28 state is unavailable.
5. Reject reuse of a settlement record already bound to another M2M transaction.

Settlement means verified acceptance in the consulted L28 source of truth. This model MUST NOT claim confirmations, irreversible finality, escrow, refund, or chargeback.

M2M MUST NEVER treat `payment_authorization` as proof of payment.

Canonical issuance-state readiness remains unrelated to M2M message signing.

## 18. Failure recovery without double payment

- Duplicate settlement citations for the same M2M transaction MUST be idempotent after the first verified acceptance.
- Implementations SHOULD ensure that local payment attempt logic does not submit multiple L28 transfers for one `transaction_id` unless an explicit new M2M transaction is created.
- `failure_notice` MUST NOT be interpreted as an L28 refund instruction.
- Double-spend prevention for L28 units remains an L28 ledger responsibility; M2M MUST not weaken it.

## 19. Logging and secret prohibition

Implementations MUST NOT write private keys, seed phrases, or signing secrets into:

- M2M messages;
- coordination logs;
- receipts;
- failure details;
- debugging artifacts retained by default.

## 20. Privacy boundary

- Existing optional L28 privacy mechanisms, if present in an implementation, MUST NOT have their claims expanded by M2M v0.1.
- M2M metadata can reveal relationships, timing, service identifiers, and amounts unless protected by an existing compatible mechanism.
- This specification establishes neither anonymity nor confidentiality by default.
- Optional privacy transport semantics remain unresolved.
- No statement in these documents promises unlinkability across counterparties.

## 21. Security non-goals for v0.1

M2M v0.1 does not provide:

- escrow;
- refunds;
- chargebacks;
- arbitration;
- trusted execution guarantees for service correctness;
- proof of human identity;
- a second consensus or finality system.

## 22. Vulnerability reporting

Security issues affecting L28 protocol software SHOULD be reported according to [SECURITY.md](../../SECURITY.md). M2M specification ambiguities SHOULD be treated as protocol-design defects and handled without publishing exploit details that expose keys or live funds.
