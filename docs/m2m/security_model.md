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

- A sender is identified by `sender_public_key` and/or an existing L28 identity reference.
- Possession of the corresponding private key is what authorizes signatures.
- M2M identity MUST NOT be interpreted as proof of a human identity, legal personhood, jurisdiction, or accreditation.

Reserved L28 senders `COINBASE` and `__MINT__` MUST NOT be used as M2M party identities.

## 3. Evidence separation

### 3.1 M2M coordination evidence

Signed M2M envelopes prove that a machine asserted a coordination step. They do not move L28 value.

### 3.2 L28 settlement evidence

Only an existing L28 settlement record accepted under L28 Protocol v1.0.0 is settlement evidence. M2M `settlement_reference` messages are citations plus local verification claims, not substitutes for ledger truth.

### 3.3 Service-delivery evidence

A `service_receipt` proves a provider asserted completion. It does not independently prove objective correctness of the service result.

## 4. Signature verification

- Every M2M message MUST carry a non-empty `signature`.
- Receivers MUST verify the signature before accepting state effects.
- If no cryptographic verifier is configured, implementations MUST fail closed and reject the message.
- L28 Protocol v1.0.0 allows signatures to be required by policy for ledger transfers but does not name a mandatory signature algorithm. M2M therefore treats algorithm selection as an unresolved dependency outside L28 consensus. Local choices MUST be explicit and MUST NOT be presented as L28 Protocol v1.0.0 invariants.

## 5. Domain separation

Signing and verification MUST use a domain-separated context for L28 M2M v0.1 envelopes.

Requirements:

- M2M envelope signatures MUST NOT be valid input to L28 ledger signature checks merely by byte reuse without domain distinction.
- L28 ledger signatures MUST NOT be accepted as M2M envelope signatures.
- The domain context MUST identify protocol `L28-M2M` and version `0.1`.

## 6. Canonical serialization

Protocol integers in JSON MUST be encoded without fractional parts. Floating-point encodings for those fields MUST be rejected.

Any broader JSON canonicalization or hash algorithm used for M2M digests and signing inputs is an unresolved M2M dependency. L28 Protocol v1.0.0 does not name SHA-256 or a canonical JSON encoding as consensus primitives.

The public repository's transaction-identity helper uses SHA-256 over sorted-key compact JSON. That repository-supported practice MAY be adopted as an explicit peer agreement for M2M digests. It MUST NOT be claimed as an L28 Protocol v1.0.0 consensus rule. See [protocol_v0.1.md](protocol_v0.1.md) Section 10.

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

- `payload_hash` MUST equal the digest recomputed from the payload under the peers' agreed M2M digest profile.
- Signature verification MUST cover `payload_hash` under the domain-separated envelope signing input.
- A mutated payload with a stale signature MUST fail validation.

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
3. Reject if L28 state is unavailable.
4. Reject reuse of a settlement record already bound to another M2M transaction.

M2M MUST NEVER treat `payment_authorization` as proof of payment.

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
