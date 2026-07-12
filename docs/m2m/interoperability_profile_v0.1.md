# L28 M2M Interoperability Profile v0.1

**Document:** L28 M2M Interoperability Profile v0.1
**Status:** Offline M2M coordination profile (non-operational until an audited signature verifier exists)
**Normative subordination:** This profile is subordinate to [L28 Protocol v1.0.0](../../PROTOCOL.md). L28 Protocol v1.0.0 prevails on conflict.
**Related:** [protocol_v0.1.md](protocol_v0.1.md), [message_schema_v0.1.md](message_schema_v0.1.md), [security_model.md](security_model.md), [test_vectors_v0.1.json](test_vectors_v0.1.json)

## 1. Purpose and status

This document defines the L28 M2M Interoperability Profile v0.1: the M2M-layer rules for canonical serialization, domain-separated digests, future Ed25519 signatures, machine-identity binding, and settlement evidence citation.

This profile:

- MUST be treated as an M2M coordination profile, not as L28 consensus;
- MUST NOT change L28 Protocol v1.0.0 economics, ledger behavior, transaction validation, mining, wallets, or networking;
- is offline and non-operational until a later audited signature verifier exists;
- MUST NOT enable autonomous spending by itself.

Normative language follows RFC 2119 / RFC 8174 uppercase usage.

References (external standards):

- RFC 8785 (JSON Canonicalization Scheme): https://www.rfc-editor.org/rfc/rfc8785.html
- RFC 8259 (JSON): https://www.rfc-editor.org/rfc/rfc8259.html
- RFC 7493 (I-JSON): https://www.rfc-editor.org/rfc/rfc7493.html
- RFC 8032 (Ed25519): https://www.rfc-editor.org/rfc/rfc8032.html
- RFC 4648 (Base64): https://www.rfc-editor.org/rfc/rfc4648.html

## 2. L28-M2M Canonical JSON v0.1

### 2.1 Definition

**L28-M2M Canonical JSON v0.1** is a restricted RFC 8785-compatible subset designed to remain implementable using the current repository dependency boundary.

This profile does NOT claim that Python `json.dumps` alone implements full RFC 8785. It defines a narrower allowed input subset whose conforming values MUST serialize to deterministic cross-language output under the rules below.

### 2.2 Output requirements

Canonical output MUST:

1. be UTF-8 encoded;
2. contain no byte-order mark;
3. contain no insignificant whitespace;
4. recursively sort object keys by Unicode code-point order (ASCII lexicographic order for the restricted property-name alphabet);
5. preserve array element order;
6. encode objects as `{` key/value pairs separated by `,` `}`;
7. encode arrays as `[` values separated by `,` `]`;
8. separate keys from values with `:`;
9. fail closed on invalid input.

### 2.3 Parsing requirements

When parsing JSON for this profile, implementations MUST:

- reject duplicate object keys;
- reject lone Unicode surrogates;
- reject floats, decimal-looking numbers, `NaN`, and `Infinity`;
- reject property names that are not lowercase ASCII snake_case matching `^[a-z][a-z0-9_]*$`;
- reject non-ASCII property names.

### 2.4 Value rules

| Type | Rule |
|---|---|
| Object | Keys sorted; each key MUST match `^[a-z][a-z0-9_]*$` |
| Array | Order preserved |
| String | Unicode preserved without normalization; `"`, `\`, and U+0000–U+001F escaped deterministically; solidus `/` MUST NOT be escaped |
| Integer | Exact JSON integers only, within `-9007199254740991` … `9007199254740991` |
| Boolean | JSON literals `true` / `false`; MUST NOT satisfy integer-typed protocol fields |
| Null | Allowed only where the message schema explicitly permits null |

Amounts and timestamps MUST be exact integers. Boolean, float, string, and null values are invalid as amounts. No fractional subunit is introduced. Amount interpretation remains subordinate to L28 Protocol v1.0.0.

Timestamps used in test vectors are protocol fixtures, not claims of live network activity.

## 3. Domain separation and digests

### 3.1 Digest algorithm

M2M digests use SHA-256 with lowercase hexadecimal output. This is an M2M profile choice and MUST NOT be described as an L28 Protocol v1.0.0 consensus primitive.

### 3.2 Domain prefixes

Exact ASCII/UTF-8 domain prefixes (including the trailing NUL):

| Purpose | Prefix bytes |
|---|---|
| Payload | `L28-M2M-V0.1-PAYLOAD` + `0x00` |
| Message ID | `L28-M2M-V0.1-MESSAGE` + `0x00` |
| Signature | `L28-M2M-V0.1-SIGNATURE` + `0x00` |

### 3.3 Derived values

Let `Canon(x)` be the L28-M2M Canonical JSON v0.1 UTF-8 byte encoding of value `x`.

1. `payload_hash` = lowercase hex of
   `SHA-256(payload-domain bytes || Canon(payload))`

2. The **unsigned envelope** is the envelope object excluding exactly:
   - `message_id`
   - `signature`
   It MUST include `payload` and `payload_hash`.

3. `message_id` = lowercase hex of
   `SHA-256(message-domain bytes || Canon(unsigned-envelope))`

4. Signature preimage =
   `signature-domain bytes || Canon(unsigned-envelope)`

### 3.4 Recomputation rules

- Signature verification MUST independently recompute `payload_hash` and `message_id`.
- No implementation MAY trust transmitted derived values without recomputation.
- Modifying any signed field, payload value, or chain reference MUST invalidate verification.

## 4. Signature suite (selected, not implemented here)

### 4.1 Suite selection

The required future M2M signature suite is **Ed25519** as defined by RFC 8032.

| Item | Value |
|---|---|
| Suite identifier | `ed25519` |
| Mode | PureEd25519 (not Ed25519ph, not Ed25519ctx) |
| Public key | exactly 32 raw bytes |
| Signature | exactly 64 raw bytes |
| Transport encoding | RFC 4648 base64url **without** `=` padding |
| Signed bytes | the signature preimage defined in Section 3.3 |

### 4.2 Verification requirements (future milestone)

- Malformed sizes, encodings, noncanonical points, or failed verification MUST reject.
- Signature verification MUST use a maintained cryptographic implementation in a later milestone.
- Handwritten production cryptography MUST NOT be used.
- SHA-256 message IDs do NOT replace Ed25519’s internally defined RFC 8032 hashing behavior.

### 4.3 Implementation boundary for this milestone

This Foundation 4 milestone:

- MUST NOT implement Ed25519;
- MUST NOT add a cryptographic dependency;
- MUST NOT generate or commit a private key or seed;
- MUST NOT fabricate an Ed25519 signature vector that has not been independently verified;
- MUST treat unsigned digests as non-operational.

Operational signed-envelope validation is deferred until an audited verifier exists.

## 5. Machine identity binding

- Machine identity is the Ed25519 public key.
- Key identifier format: `ed25519:<base64url-unpadded-raw-public-key>`
- Envelope field `sender_public_key` / `recipient_public_key` MUST carry the base64url-unpadded raw public key when used.
- L28 settlement account remains an explicit opaque existing L28 account string (`sender_identity` / `recipient_identity` / payload payer/payee fields).
- The signed envelope binds machine identity to the claimed L28 settlement account.
- This does NOT create a new L28 address format.
- This does NOT prove human identity, ownership, authorization, or legal identity.
- Key rotation and revocation remain outside v0.1.

## 6. Settlement evidence

M2M message identity and L28 transaction identity remain separate:

| Identity | Rule |
|---|---|
| M2M `message_id` | This profile (Section 3) |
| L28 transaction ID | Stable `compute_tx_id` from `coin/tx_validation.py` (Foundation 3) |

A `settlement_reference` MUST cite:

- the canonical L28 transaction ID;
- the relevant sender;
- the relevant receiver;
- the integer amount.

A verifier MUST recompute the cited L28 transaction ID from the referenced transaction material using `compute_tx_id`.

Settlement means verified acceptance in the consulted L28 source of truth. This profile MUST NOT claim confirmations, irreversible finality, escrow, refund, or chargeback.

Canonical issuance-state readiness (Foundation 3) remains unrelated to M2M message signing.

## 7. Envelope field compatibility

This profile reuses existing M2M envelope field names from [message_schema_v0.1.md](message_schema_v0.1.md). It does not rename them.

For digest and signature construction, the unsigned envelope excludes only `message_id` and `signature`. All other present envelope fields participate in canonicalization.

## 8. Remaining unresolved items

Resolved by this profile (M2M-layer only):

- M2M canonical JSON subset
- M2M SHA-256 domain-separated digests
- Ed25519 suite selection and encodings
- Machine identity / L28 account binding
- Settlement citation using Foundation 3 `compute_tx_id`

Still unresolved / deferred:

- Operational Ed25519 verification implementation and dependency choice
- Optional privacy transport semantics
- Irreversible finality / confirmation vocabulary beyond L28 acceptance
- L28 Protocol v1.0.0 address grammar (unchanged; still opaque strings)

## 9. Test vectors

Deterministic offline vectors are published in [test_vectors_v0.1.json](test_vectors_v0.1.json). They contain no private keys, seeds, live settlement claims, or verified Ed25519 signatures.
