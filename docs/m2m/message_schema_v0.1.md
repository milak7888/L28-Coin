# L28 M2M Message Schema v0.1

**Document:** L28 M2M Protocol v0.1 message schema
**Status:** Specification (documentation only)
**Normative subordination:** This document is subordinate to [L28 Protocol v1.0.0](../../PROTOCOL.md) and to [protocol_v0.1.md](protocol_v0.1.md). L28 Protocol v1.0.0 prevails on conflict.

## 1. Purpose

This document defines the common signed envelope and the payloads for the six normative M2M message types.

Examples in this document are explanatory. Only uppercase RFC terms create requirements.

## 2. Common signed envelope

Every M2M message MUST be an object containing the fields in this section.

### 2.1 Field table

| Field | Type | Requirement | Purpose |
|---|---|---|---|
| `protocol` | string | MUST | Identifies the coordination protocol. Value MUST be exactly `L28-M2M`. |
| `protocol_version` | string | MUST | Identifies the M2M version. Value MUST be exactly `0.1`. |
| `message_type` | string | MUST | Selects the payload schema. MUST be one of the six normative types. |
| `message_id` | string | MUST | Unique identifier for this message instance within the sender's generation domain. |
| `transaction_id` | string | MUST | Stable identifier for the M2M transaction shared across the message chain. |
| `sender_public_key` | string | MUST unless `sender_identity` is present | Sender cryptographic public key material, encoded as a string. |
| `sender_identity` | string | MUST unless `sender_public_key` is present | Existing L28 identity reference for the sender, using the same opaque string form used by L28 transfer sender/receiver fields. |
| `recipient_public_key` | string | MUST unless `recipient_identity` is present | Recipient cryptographic public key material, encoded as a string. |
| `recipient_identity` | string | MUST unless `recipient_public_key` is present | Existing L28 identity reference for the recipient. |
| `created_at` | integer | MUST | Message creation time as an integer timestamp in the same integer timestamp representation used by L28 transactions. Unix-second interpretation is repository construction practice, not a PROTOCOL.md-named consensus rule. |
| `expires_at` | integer | MUST | Expiration time as an integer timestamp. MUST be greater than `created_at`. |
| `nonce` | string | MUST | Sender-generated anti-replay value unique for the sender within the relevant retention window. |
| `previous_message_id` | string or null | MUST | Prior message in the chain for this `transaction_id`, or `null` for the first message. |
| `payload_hash` | string | MUST | Hash of the canonical payload encoding. |
| `payload` | object | MUST | Message-type-specific body defined below. |
| `signature` | string | MUST | Signature over the domain-separated canonical envelope signing input. |

A conforming message MAY include both a public-key field and the corresponding L28 identity reference for the same party. If both are present, they MUST refer to the same party; mismatch MUST cause rejection.

### 2.2 Identity field validation

- At least one of `sender_public_key` or `sender_identity` MUST be present and non-empty.
- At least one of `recipient_public_key` or `recipient_identity` MUST be present and non-empty.
- Identity strings MUST NOT equal L28 reserved senders `COINBASE` or `__MINT__`.
- Public-key and signature encodings are defined by [interoperability_profile_v0.1.md](interoperability_profile_v0.1.md) (Ed25519 selected; operational verification deferred).

### 2.3 Timestamp validation

- `created_at` and `expires_at` MUST be integers.
- Floating-point timestamps MUST be rejected.
- `expires_at` MUST be strictly greater than `created_at`.
- A receiver SHOULD reject a message whose `created_at` is unreasonably far in the future relative to local clock, using a locally configured skew bound.
- A receiver MUST treat a message as expired when local time is greater than `expires_at` after applying the receiver's configured skew tolerance.
- Exact skew defaults are local policy. L28 Protocol v1.0.0 does not publish an M2M-specific skew constant.

### 2.4 Nonce and identifiers

- `message_id` MUST be non-empty.
- `transaction_id` MUST be non-empty and MUST remain constant for all messages in one M2M transaction.
- `nonce` MUST be non-empty.
- Identifier generation format is not fixed by L28 Protocol v1.0.0. Implementations MUST ensure collision resistance within their operational domain and MUST reject duplicates as defined in [state_machine.md](state_machine.md).

### 2.5 previous_message_id rules

- For the first message of a transaction (`service_request`), `previous_message_id` MUST be `null`.
- For every subsequent message, `previous_message_id` MUST equal the `message_id` of the immediately prior accepted message in the chain for that `transaction_id`.
- A message that breaks the chain MUST be rejected.

### 2.6 payload_hash rules

- `payload_hash` MUST be present and MUST equal the digest recomputed under [interoperability_profile_v0.1.md](interoperability_profile_v0.1.md):
  `SHA-256(L28-M2M-V0.1-PAYLOAD || 0x00 || Canon(payload))` as lowercase hex.
- If `payload_hash` does not equal the recomputed digest of `payload`, the message MUST be rejected.
- This digest profile is an M2M interoperability rule and MUST NOT be described as an L28 Protocol v1.0.0 consensus primitive.

### 2.7 signature rules

- `signature` MUST be a non-empty string for operational messages.
- The required future suite is `ed25519` (PureEd25519 / RFC 8032) as selected by the interoperability profile.
- The signing input MUST be the domain-separated signature preimage defined by the interoperability profile (unsigned envelope excludes exactly `message_id` and `signature`).
- `message_id` MUST equal the recomputed profile message digest; transmitted values MUST NOT be trusted without recomputation.
- Operational signature verification is deferred until an audited verifier exists. Until then, implementations MUST fail closed for operational acceptance of signed envelopes.
- Exact suite details, encodings, and deferred implementation boundaries are normative in [interoperability_profile_v0.1.md](interoperability_profile_v0.1.md) and [security_model.md](security_model.md).

### 2.8 Envelope failure behavior

If any envelope validation rule fails, the receiver MUST:

1. reject the message;
2. leave the M2M transaction state unchanged, except where [state_machine.md](state_machine.md) explicitly permits a transition to `failed` or `rejected` due to authenticated failure handling;
3. MUST NOT submit any L28 settlement as a side effect of the rejection path.

Invalid signatures, unknown `transaction_id` values where prior state is required, duplicate `message_id` values, and payload-hash mismatches are hard failures.

## 3. Message type payloads

Each `payload` MUST match the schema for its `message_type`. Unknown fields in payloads SHOULD be rejected in v0.1 to preserve determinism.

### 3.1 `service_request`

Sent by the requester to initiate an M2M transaction.

| Field | Type | Requirement | Purpose |
|---|---|---|---|
| `service_id` | string | MUST | Identifier of the requested service class or endpoint name. |
| `service_params` | object | MUST | Service-specific parameters. MAY be empty. |
| `max_amount` | integer | MUST | Maximum integer L28 amount the requester is willing to consider. MUST be > 0. |
| `currency` | string | MUST | MUST be exactly `L28`. |
| `request_constraints` | object | SHOULD | Optional constraints such as delivery deadline expressed as an integer timestamp. |
| `metadata` | object | MAY | Non-authoritative descriptive metadata. MUST NOT contain secrets. |

Validation and failure behavior:

- `max_amount` MUST be an integer and MUST NOT be a float.
- `service_params` contents are untrusted application data and MUST be handled per [security_model.md](security_model.md).
- On validation failure, the provider MUST NOT emit a quote for the invalid request.

### 3.2 `service_quote`

Sent by the provider in response to an accepted `service_request`.

| Field | Type | Requirement | Purpose |
|---|---|---|---|
| `request_message_id` | string | MUST | `message_id` of the `service_request` being quoted. |
| `service_id` | string | MUST | MUST match the request `service_id`. |
| `amount` | integer | MUST | Quoted integer L28 amount. MUST be > 0 and MUST be <= request `max_amount`. |
| `currency` | string | MUST | MUST be exactly `L28`. |
| `quote_expires_at` | integer | MUST | Quote expiration as an integer timestamp. MUST be <= envelope `expires_at`. |
| `service_terms_hash` | string | MUST | Digest of the service terms object under the peers' agreed M2M digest profile. |
| `service_terms` | object | MUST | Human-or-machine readable terms whose digest equals `service_terms_hash`. |
| `rejectable` | boolean | MUST | If `true`, requester may reject without authorization. MUST be `true` in v0.1. |

Validation and failure behavior:

- Amount must satisfy integer and bound checks above.
- If `service_terms_hash` mismatches `service_terms`, reject.
- An expired quote MUST NOT be authorized.

### 3.3 `payment_authorization`

Sent by the requester to authorize payment against one quote.

| Field | Type | Requirement | Purpose |
|---|---|---|---|
| `quote_message_id` | string | MUST | `message_id` of the accepted `service_quote`. |
| `authorized_amount` | integer | MUST | MUST equal the quote `amount`. |
| `currency` | string | MUST | MUST be exactly `L28`. |
| `payer_identity` | string | MUST | L28 identity reference expected to appear as sender in the eventual L28 settlement. |
| `payee_identity` | string | MUST | L28 identity reference expected to appear as receiver in the eventual L28 settlement. |
| `authorization_expires_at` | integer | MUST | Authorization expiration as an integer timestamp. MUST be <= envelope `expires_at`. |
| `settlement_intent` | string | MUST | MUST be exactly `l28_transfer`. |

Normative clarifications:

- This message is NOT settlement.
- This message MUST NOT contain private keys, seed phrases, or signing secrets.
- This message does NOT by itself move L28 value.

Validation and failure behavior:

- If the referenced quote is unknown, expired, or not in `quoted` state, reject.
- If identities or amount disagree with the quote chain, reject.
- Authorization expiration MUST prevent transition toward settlement using that authorization.

### 3.4 `settlement_reference`

Sent by requester or provider to cite an existing L28 settlement record.

| Field | Type | Requirement | Purpose |
|---|---|---|---|
| `authorization_message_id` | string | MUST | `message_id` of the `payment_authorization` being settled. |
| `l28_tx_id` | string | MUST | Identifier of the existing L28 settlement record. |
| `l28_sender` | string | MUST | Sender identity in the L28 record. MUST match authorization `payer_identity`. |
| `l28_receiver` | string | MUST | Receiver identity in the L28 record. MUST match authorization `payee_identity`. |
| `amount` | integer | MUST | Integer amount in the L28 record. MUST equal authorized amount. |
| `l28_timestamp` | integer | MUST | Integer timestamp from the L28 record. |
| `verification_status` | string | MUST | Local assertion of verification outcome. MUST be `verified` for a state transition to `settled`. |

Normative clarifications:

- The cited L28 record is the settlement evidence. This M2M message is only a pointer plus attestation that the sender claims verification.
- Receivers MUST independently re-verify against the L28 source of truth and MUST NOT trust `verification_status` alone.
- Repeated use of the same `l28_tx_id` for a different M2M `transaction_id` MUST be rejected by parties that observe the collision.

Validation and failure behavior:

- If L28 lookup fails, is unavailable, or mismatches, reject and remain fail-closed.
- If authorization is expired, reject.
- Successful local verification is required before entering `settled`.

### 3.5 `service_receipt`

Sent by the provider after valid settlement.

| Field | Type | Requirement | Purpose |
|---|---|---|---|
| `settlement_message_id` | string | MUST | `message_id` of the accepted `settlement_reference`. |
| `l28_tx_id` | string | MUST | MUST match the settled L28 transaction id. |
| `service_id` | string | MUST | MUST match the quoted service. |
| `result_hash` | string | MUST | Digest of the service-result object or result reference under the peers' agreed M2M digest profile. |
| `completed_at` | integer | MUST | Provider completion assertion time as an integer timestamp. |
| `completion_assertion` | string | MUST | MUST be exactly `provider_asserted_complete`. |

Normative clarifications:

- This receipt is provider completion evidence, not objective correctness proof.
- Conflicting receipts for the same `transaction_id` with different `result_hash` values MUST cause transition to `disputed` as defined in the state machine.

Validation and failure behavior:

- Receipt without prior valid settlement MUST be rejected.
- Receipt that cites a mismatched `l28_tx_id` MUST be rejected.

### 3.6 `failure_notice`

Sent by requester or provider to report a coordination failure or rejection condition.

| Field | Type | Requirement | Purpose |
|---|---|---|---|
| `related_message_id` | string | MUST | Message that precipitated the failure notice. |
| `failure_code` | string | MUST | Machine-readable code from the v0.1 code set below. |
| `failure_detail` | string | SHOULD | Short non-secret explanation. |
| `terminal` | boolean | MUST | If `true`, the sender asserts the M2M transaction should enter a terminal failure-class state. |

v0.1 `failure_code` values:

| Code | Meaning |
|---|---|
| `quote_rejected` | Requester declines the quote |
| `quote_expired` | Quote expired before authorization |
| `authorization_expired` | Authorization expired before settlement |
| `invalid_signature` | Authenticated processing detected an unusable signature context for a related message already retained |
| `payload_invalid` | Payload schema or hash validation failed |
| `settlement_unverified` | Cited L28 settlement could not be verified |
| `service_incomplete` | Provider cannot complete after settlement citation handling |
| `duplicate_message` | Duplicate message detected |
| `chain_break` | `previous_message_id` chain invalid |
| `cancelled_by_sender` | Sender cancels before settlement where permitted |
| `internal_error` | Local processing failure without settlement implication |

Normative clarifications:

- `failure_notice` does NOT reverse an L28 settlement.
- `failure_notice` MUST NOT include private keys, seed phrases, or signing secrets.

## 4. Canonical serialization requirements

Amounts and timestamps that are protocol integers MUST be encoded as JSON numbers without fractional parts. Floating-point encodings for those fields MUST be rejected before hashing or signing.

Canonicalization and digest construction for M2M envelopes MUST follow [interoperability_profile_v0.1.md](interoperability_profile_v0.1.md) (L28-M2M Canonical JSON v0.1 and domain-separated SHA-256 digests). That profile is an M2M interoperability rule and MUST NOT be described as an L28 Protocol v1.0.0 consensus primitive.

`service_terms_hash` and `result_hash` SHOULD use the same payload-domain digest construction over their respective canonical objects unless a later profile revision defines distinct domains.

## 5. Secrets prohibition

No M2M message field, payload, log line, or retained coordination artifact MUST include:

- private keys;
- seed phrases;
- wallet credentials;
- raw signing secrets;
- password material.

## 6. Non-normative envelope shape

The following field list is explanatory only. It is not a transaction, not network evidence, and not a filled-in message:

- `protocol`: `L28-M2M`
- `protocol_version`: `0.1`
- `message_type`: one normative message type name
- `message_id`: recomputed profile message digest (hex)
- `transaction_id`: shared M2M transaction identifier
- `sender_identity` or `sender_public_key`: sender identity material
- `recipient_identity` or `recipient_public_key`: recipient identity material
- `created_at`: integer timestamp
- `expires_at`: later integer timestamp
- `nonce`: sender anti-replay value
- `previous_message_id`: `null` for the first message, otherwise prior `message_id`
- `payload_hash`: profile payload digest
- `payload`: message-type-specific object
- `signature`: Ed25519 signature transport (operational verification deferred)

Conforming runtime messages MUST satisfy `expires_at > created_at` and all envelope validation rules in Section 2.

## 7. Unresolved schema dependencies

The following remain unresolved or deferred and outside L28 consensus:

- operational Ed25519 verifier implementation and dependency choice;
- L28 address grammar (accounts remain opaque strings; no new address format);
- optional privacy transport semantics;
- irreversible finality beyond L28 acceptance;
- timestamp epoch interpretation beyond the L28 Protocol v1.0.0 requirement that timestamps are integers;
- transport framing for delivery of envelopes.

M2M canonical JSON, domain-separated digests, Ed25519 suite/encoding selection, and machine-identity binding are defined by the interoperability profile and MUST NOT be treated as L28 consensus rules.
