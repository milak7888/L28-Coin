# Foundation 64 Isolated Local Signing and Signed-Receipt Contract v0.1

**Status:** Specification only (documentation; non-activation; non-implementation)

**Profile / `signing_receipt_profile`:**
`l28-isolated-local-signing-signed-receipt/v0.1`

**Parent contracts:**

- Foundation 56 — `l28-universal-ai-access-interface/v0.1`
  (`docs/foundation56_universal_ai_access_interface_specification_v0.1.md`)
- Foundation 57 — `l28-uaii-reference-core-contract/v0.1`
  (`docs/foundation57_uaii_reference_core_contract_specification_v0.1.md`)
- Foundation 58 / 62 / Foundation 63 — UAII reference-core implementation
  specifications and bounded reference core (authority and canonicalization
  only; this document does not modify them)

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Base commit:** `d76b621f101d233c38cdd5bbe333d6bf630b8f17`

**Branch:** `foundation64-isolated-signing-receipt-spec`

**Normative subordination:** This document is subordinate to
[L28 Protocol v1.0.0](../PROTOCOL.md), then Foundation 56, then Foundation 57,
then Foundations 58/62/63 for UAII processing rules. On conflict, Protocol
prevails; then F56; then F57; then this signing/receipt contract. This document
MUST NOT redefine settlement, issuance, supply, consensus height authority,
M2M envelope `message_id` derivation, UAII exact-order canonicalization, or
`validate_transaction`.

## 1. Purpose and scope

Foundation 64 defines a deterministic **isolated local signing** and
**signed-receipt** contract in which:

1. UAII (Foundations 56–63) creates an **unsigned** payment or service result.
2. Private-key operations occur **only** inside an isolated local signer.
3. Only public signing inputs and bounded public outputs cross the signer
   boundary.
4. A verifier validates a deterministic signed receipt.
5. No key, seed, secret, wallet credential, or signing capability enters
   prompts, model context, tool arguments, logs, hosted services, receipts, or
   network payloads.

This Foundation’s **only active signature purpose** is `signed_receipt`.
Other purpose tokens are reserved (§5.4) and unauthorized until a later
specification defines exact ordered schemas.

### 1.1 Explicitly out of scope (future separately authorized work)

The following MUST NOT be treated as authorized by this Foundation:

- Implementation of a signer, verifier, SDK, adapter, or test harness
- Key generation, key import, keystore creation, or hardware-token provisioning
- Any actual signature production or private-key use
- Settlement execution, broadcast, mining, networking, wallets, or testnets
- Persistent replay stores, hosted signing services, or remote signers
- Changes to Protocol, UAII reference core, M2M verifier, ledger, supply, or
  historical evidence
- Escrow, discretionary refunds that mint supply, multi-party settlement, or
  cross-chain bridges
- Active use of reserved signature purposes (§5.4)

### 1.2 Normative language

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted
as described in RFC 2119 / RFC 8174 when, and only when, they appear in
uppercase as shown here.

**Non-normative notes** are labeled as such and MUST NOT be treated as
requirements.

### 1.3 Security invariants (normative for this Foundation)

Every Foundation 64 artifact, process description, and future implementation
milestone governed by this contract MUST preserve:

| Invariant | Required value |
|---|---|
| `execution_authorized` | `false` |
| `implementation_authorized` | `false` |
| `signing_authorized` | `false` |
| `spend_authorized` | `false` |
| `settlement_authorized` | `false` |
| `ledger_mutated` | `false` |
| `private_material_exposed` | `false` |

Foundation 64 is **specification only**. These flags remain false for this
document and for any review of this document. A later foundation that
implements signing MUST obtain separate explicit authorization and MUST still
keep `spend_authorized`, `settlement_authorized`, `ledger_mutated`, and
`private_material_exposed` false unless a further foundation separately
authorizes those capabilities.

## 2. Authority and trust boundaries

### 2.1 Preserved authorities

1. **UAII remains the sole protocol-processing interface** established by
   Foundations 56–63 for AI/agent access operations defined there.
2. **Transaction validation** for L28 transfers remains delegated **only** to
   `coin.tx_validation.validate_transaction` under Protocol v1.0.0.
3. **UAII content digests and UAII signable objects** remain under Foundation
   56 §3.2 exact-order canonicalization (`CanonUaii` / `canon_uaii`):
   `sort_keys=false`; separators `(",", ":")`; `ensure_ascii=false`;
   `allow_nan=false`; UTF-8; integer-only numerics.
4. **M2M envelopes and M2M digests** remain under L28-M2M Canonical JSON v0.1
   and M2M domain prefixes. Foundation 64 MUST NOT reuse
   `coin.m2m_verifier.canonicalize` for UAII signing payloads.
5. Foundation 64 MUST NOT introduce an alternate protocol, canonicalizer,
   validation authority, wallet, ledger, replay store, accumulator, or
   persistent state.

### 2.2 Roles

| Role | Authority | MUST NOT |
|---|---|---|
| **Requester** | Requests quotes/payments/service results via UAII | Hold provider private keys; assert settlement |
| **Provider** | Supplies quotes/service results via UAII | Spend requester funds; mutate ledger; sign as payer |
| **UAII processor** | Processes UAII operations per F56–F63 | Sign; spend; settle; import private material |
| **Approval authority** | Human/operator (or separately authorized policy) that issues an `ApprovalDecision` (§8) and owns external cumulative/replay state | Perform private-key ops; alter amounts/parties; settle |
| **Isolated local signer** | Signs exact approved `signable_bytes` with a local private key | Authorize spending; select recipients; change amounts; alter quotes; validate transactions; mutate ledgers; execute settlement; accept silent approval; accept digest-only or arbitrary-byte signing |
| **Verifier** | Validates signed receipts and bindings using public material only | Sign; spend; settle; mutate canonical state |
| **Settlement adapter** (optional; future) | May act only after separate authorization using independently verified ledger evidence | Sign inside the adapter; claim settlement from signature alone |

### 2.3 Trust-boundary sequence (normative)

```text
Requester/Provider
    |  unsigned UAII objects (CanonUaii)
    v
UAII processor (F56–F63)
    |  unsigned payment / service result + public identifiers
    v
Approval authority
    |  ApprovalDecision (decision=approved) + external limit/replay facts
    |  displays signable_digest = SHA-256(signable_bytes)
    v
Isolated local signer  <--- approved_canonical_payload REQUIRED ---
    |  signs signable_bytes (not the digest)
    |  bounded public outputs (sig, digest, key id)
    v
Receipt constructor (insert digest+signature; then receipt_id)
    |
    v
Verifier (public verification; no private material)
    |
    v
[OPTIONAL later] Settlement adapter  --only if separately authorized--
    |  requires independent ledger evidence for settlement_confirmed
    v
Protocol validate_transaction / ledger (unchanged authorities)
```

### 2.4 Signing is not settlement

A successful signature or signed receipt MUST NOT be interpreted as:

- spending authorization beyond the signed purpose;
- settlement success;
- ledger mutation;
- broadcast;
- mining; or
- network transmission.

`settlement_status` values and immutable transition rules are defined in §6.
A genesis receipt (`prior_receipt_id` = `null`) MUST use exactly
`authorization_signed` or `service_result_signed` (§6.3). Only independently
verified ledger evidence MAY support `settlement_confirmed`.

## 3. Local signer boundary

### 3.1 Allowed signer inputs (exhaustive)

The isolated local signer MUST accept **only** the following public or
non-secret inputs:

| Input | Type / constraint |
|---|---|
| `signing_profile` | string; MUST equal `l28-isolated-local-signing-signed-receipt/v0.1` |
| `signing_profile_version` | string; MUST equal `0.1` |
| `public_key_id` or `local_key_handle` | non-secret identifier or OS/local handle that does **not** contain key material in the handle string exchanged across the boundary; UTF-8 length `1..256` |
| `signature_purpose` | MUST equal `signed_receipt` (§5.4); any other value → `purpose_unsupported` |
| `approved_canonical_payload` | **REQUIRED.** Exact UTF-8 bytes of `CanonUaii(UaiiSignedReceiptUnsignedFacts)` (§6.2.1). Maximum `16384` bytes (§3.6). |
| `approved_payload_digest` | **Optional display-and-match only.** MUST equal `lowercase_hex(SHA-256(signable_bytes))` when present. MUST NOT authorize signing by itself. |
| `expected_domain_separator` | exact domain prefix bytes for `signed_receipt` (§5.3) |
| `approval_decision` | `ApprovalDecision` object (§8) with `decision=approved` |
| `public_metadata` | optional bounded object (§3.3) |

### 3.2 Byte-kind distinctions (normative)

| Term | Definition |
|---|---|
| **Canonical object bytes** | `CanonUaii(UaiiSignedReceiptUnsignedFacts)` — exact UTF-8 JSON bytes; equal to `approved_canonical_payload` |
| **Domain-separated signable bytes** | `signable_bytes = domain_prefix \|\| approved_canonical_payload` |
| **Digest** | `signed_payload_digest = lowercase_hex(SHA-256(signable_bytes))` — display/match only; **not** the Ed25519 message |
| **Signature** | PureEd25519 signature over `signable_bytes` (RFC 8032); **not** over the digest |

### 3.3 Digest-only and arbitrary-byte signing forbidden

1. A digest alone MUST NOT authorize or permit signing.
2. If `approved_canonical_payload` is missing or empty → `signer_payload_mismatch`.
3. The signer MUST recompute
   `computed_digest = lowercase_hex(SHA-256(domain_prefix || approved_canonical_payload))`.
4. If `approved_payload_digest` is present and differs from `computed_digest` →
   `signer_payload_mismatch`.
5. The signer MUST sign `signable_bytes`, never the digest bytes and never
   arbitrary caller bytes outside `signable_bytes`.
6. Model-selected keys and silent approval remain forbidden (§3.7).

### 3.4 Allowed signer outputs (exhaustive)

| Output | Type / constraint |
|---|---|
| `signer_algorithm_profile` | string; MUST be `ed25519-pure/v0.1` on success |
| `public_key` or `public_key_id` | public material only |
| `signature` | 128 lowercase hex (§5.2) |
| `signed_payload_digest` | 64 lowercase hex; MUST equal recomputed digest |
| `signer_result_code` | stable code from §3.7 |

### 3.5 Optional public metadata bounds

If `public_metadata` is present it MUST:

1. Be a JSON object under Foundation 56 property-name grammar
   `^[a-z][a-z0-9_]*$`.
2. Contain only non-secret fields needed for verification.
3. Have total UTF-8 size `<= 1024` bytes when serialized with `CanonUaii`.
4. MUST NOT contain private keys, seeds, paths to secret files, environment
   names that imply secrets, credentials, or raw wallet material.

### 3.6 Size bounds (applied before signing or cryptographic verification)

| Object | Maximum UTF-8 bytes | Oversized code |
|---|---|---|
| Complete receipt envelope (serialized) | `16384` | `input_too_large` |
| `approved_canonical_payload` | `16384` | `input_too_large` |
| `signable_bytes` | `16512` | `input_too_large` |

`16512` allows a bounded domain prefix plus a maximum-sized canonical payload.
These limits MUST be enforced **before** signing or signature verification.
Smaller inherited Foundation 63 field limits (for example F60-L4 non-nonce
string `4096`, nonce `1..256`) MUST NOT be weakened.

### 3.7 Explicitly forbidden at the signer boundary

The signer, its callers, prompts, tools, logs, and receipts MUST NOT exchange
or emit:

- private keys, seed phrases, recovery phrases, mnemonics;
- raw wallet files or wallet credentials;
- environment secrets or secret-derived diagnostics;
- key export material;
- remote-signing requests or hosted KMS payloads containing private material;
- model-selected keys (the approval authority MUST bind the key handle before
  invoke);
- silent approval (approval MUST be an explicit `ApprovalDecision`);
- digest-only signing;
- arbitrary-byte signing;
- any content change inside the signer (bytes signed MUST equal
  `domain_prefix || approved_canonical_payload`).

### 3.8 Deterministic signer result codes

| Code | Meaning |
|---|---|
| `signer_ok` | Signature produced over exact `signable_bytes` |
| `signer_profile_unsupported` | Unknown/unsupported signing profile/version |
| `purpose_unsupported` | Purpose is not the active `signed_receipt` purpose |
| `signer_domain_mismatch` | Expected domain separator does not match purpose |
| `signer_payload_mismatch` | Missing payload, digest mismatch, or empty payload |
| `signer_key_handle_invalid` | Non-secret handle unusable / unknown locally |
| `signer_approval_missing` | Missing or non-approved `ApprovalDecision` |
| `input_too_large` | Size bound exceeded (§3.6) |
| `signer_refused` | Local policy refused signing |
| `signer_internal_error` | Fail-closed; `detail` MUST be empty |

All failure paths MUST return empty diagnostic detail and MUST NOT include
exception text, paths, key material, or payload snippets.

## 4. Authorization sequence

Processing MUST be fail-closed in this order. Later steps MUST NOT run after an
earlier failure.

1. **Size / type validation** of inputs (§3.6, §9.1).
2. **Validate UAII request context** under Foundations 56–63 as applicable.
3. **Verify quote / service-result binding** (identifiers, parties, amounts,
   purpose, expiry).
4. **Verify amount, asset, parties, purpose, expiry, nonce, per-transaction
   limit, and `CumulativeLimitEvaluation`** (§8.5).
5. **Construct `UaiiSignedReceiptUnsignedFacts`** (§6.2.1) and produce
   `approved_canonical_payload = CanonUaii(...)`.
6. **Compute `signable_bytes` and `signable_digest`** (§5.5 / §6.2.3) and
   display/return the digest to the approval authority.
7. **Obtain `ApprovalDecision`** (§8) with `decision=approved`, binding that
   digest, purpose `signed_receipt`, key handle, parties, amount, and limits.
   Absence or mismatch → reject.
8. **Replay-key check** via external authority using §10 material.
9. **Invoke the isolated signer** with §3.1 inputs (canonical payload
   required).
10. **Construct the receipt** per §6.2.3 construction order.
11. **Independently verify the receipt** (§9) before any reliance.
12. **Only a later separately authorized settlement adapter** MAY act on
    verified receipts plus independent ledger evidence.

**Normative rule:** Signing NEVER means settlement succeeded.

## 5. Canonical signing contract

### 5.1 Canonical JSON profile

Signable UAII-related objects MUST use **Foundation 56 §3.2 / `CanonUaii`**:

1. UTF-8 without BOM.
2. Top-level JSON object.
3. Duplicate keys rejected.
4. No floats, `NaN`, or `Infinity`.
5. Property names `^[a-z][a-z0-9_]*$`.
6. Unknown fields rejected for typed objects.
7. Exact declared field order; `sort_keys=false`.
8. Separators `(",", ":")`; `ensure_ascii=false`; `allow_nan=false`.
9. Amounts and timestamps MUST be exact JSON integers (not bool, string,
   float, or null).
10. No implicit numeric coercion; no ambiguous Unicode normalization beyond
    exact UTF-8 code-unit preservation of the canonical serialization.
11. Lone/non-scalar UTF-16 surrogates that cannot encode as strict UTF-8 MUST
    fail as `encoding_invalid` (consistent with Foundation 63 `canon_uaii`).

**M2M ban for UAII signing payloads:** Implementations MUST NOT call
`coin.m2m_verifier.canonicalize` / `canonical_bytes` for Foundation 64 UAII
signable objects. M2M signing remains under existing M2M domains and is out of
scope for this contract’s UAII receipt path.

### 5.2 Existing algorithm convention (preserved)

Repository evidence already makes **PureEd25519 (RFC 8032)** normative for M2M
envelope verification and creator-wallet authorization verification. Foundation
64 therefore defines its interoperable signing profile as **PureEd25519**
without adding a dependency or implementation in this Foundation.

| Constant | Value |
|---|---|
| `signer_algorithm_profile` | `ed25519-pure/v0.1` (sole supported value) |
| Mode | PureEd25519 / RFC 8032 |
| Public key size | 32 raw bytes |
| Signature size | 64 raw bytes |
| `signer_public_key` encoding | lowercase hex of 32 raw bytes; MUST match `^[0-9a-f]{64}$` |
| `signer_public_key_id` encoding | `ed25519:` + base64url-unpadded raw public key |
| `signature` encoding | lowercase hex of 64 raw bytes; MUST match `^[0-9a-f]{128}$` |

Unknown, omitted, or weaker `signer_algorithm_profile` values MUST fail closed
with `algorithm_unsupported` or `algorithm_downgrade_rejected`. This document
MUST NOT use `algorithm_profile` as a field name.

**Non-normative rationale:** Reusing PureEd25519 preserves interoperability
with existing L28 verify-only tooling concepts while **new domain separators**
prevent cross-protocol signature reuse. This Foundation does not activate
signing and does not import private-key APIs.

### 5.3 Versioned domain separation

Domain prefixes are ASCII/UTF-8 including trailing NUL `0x00`.

| Purpose token | Domain prefix bytes | Status in Foundation 64 |
|---|---|---|
| `signed_receipt` | `L28-UAII-SIGN-V0.1-RECEIPT\x00` | **Active** |
| `quote_authorization` | `L28-UAII-SIGN-V0.1-QUOTE\x00` | **Reserved** — unauthorized |
| `payment_authorization` | `L28-UAII-SIGN-V0.1-PAYMENT\x00` | **Reserved** — unauthorized |
| `service_result` | `L28-UAII-SIGN-V0.1-SERVICE-RESULT\x00` | **Reserved** — unauthorized |
| `refund_authorization` | `L28-UAII-SIGN-V0.1-REFUND\x00` | **Reserved** — unauthorized |
| `settlement_attestation` | `L28-UAII-SIGN-V0.1-SETTLEMENT-ATTEST\x00` | **Reserved** — unauthorized |

Reserved domains are locked to prevent future collisions. Invoking a reserved
purpose MUST fail closed with `purpose_unsupported`. This Foundation MUST NOT
define schemas for reserved purposes and MUST NOT imply those capabilities
exist.

These domains MUST NOT replace or equal M2M domains
(`L28-M2M-V0.1-PAYLOAD\x00`, `MESSAGE`, `SIGNATURE`, replay domains) or UAII
reference-core domains (`L28-UAII-V0.1-LEDGER-STATE\x00`,
`M2M-CORRELATION`, `REPLAY`).

### 5.4 Signature-purpose separation

| `signature_purpose` | Status | Rule |
|---|---|---|
| `signed_receipt` | Active | Signs `UaiiSignedReceiptUnsignedFacts` only (§6.2.1) |
| `quote_authorization` | Reserved | `purpose_unsupported` |
| `payment_authorization` | Reserved | `purpose_unsupported` |
| `service_result` | Reserved | `purpose_unsupported` |
| `refund_authorization` | Reserved | `purpose_unsupported` |
| `settlement_attestation` | Reserved | `purpose_unsupported` |
| any other string | Forbidden | `purpose_unsupported` |

A signature created under one purpose/domain MUST be rejected under any other.

### 5.5 Deterministic byte construction and digest (active purpose)

For `signature_purpose = signed_receipt`:

```text
approved_canonical_payload = CanonUaii(UaiiSignedReceiptUnsignedFacts)
signable_bytes             = domain_prefix || approved_canonical_payload
                             where domain_prefix = L28-UAII-SIGN-V0.1-RECEIPT\x00
signed_payload_digest      = lowercase_hex(SHA-256(signable_bytes))
```

PureEd25519 MUST sign `signable_bytes`, **not** `signed_payload_digest`.

### 5.6 Key-identifier and public-key binding

1. `signer_public_key` and `signer_public_key_id` MUST both be present in signed
   facts and MUST refer to the same key material.
2. The required signer identity is determined **exactly** by
   `settlement_status` (no verifier discretion, fallback, “either party,” or
   multi-key acceptance):

   | `settlement_status` | Required signer identity field |
   |---|---|
   | `authorization_signed` | `payer_public_identity` |
   | `service_result_signed` | `provider_public_identity` |
   | `settlement_pending` | `payer_public_identity` |
   | `settlement_confirmed` | `payer_public_identity` |
   | `settlement_failed` | `payer_public_identity` |
   | `refunded` | `payer_public_identity` |

3. `signer_public_key` MUST bind to **exactly** the identity field assigned
   above for the receipt’s `settlement_status`. Construction, verification,
   approval binding, threat mitigations, and conformance vectors MUST use this
   same mapping.
4. Any mismatch MUST fail with `key_binding_invalid`.
5. This mapping MUST NOT authorize settlement, spending, or ledger mutation,
   and MUST NOT make the signer a transaction-validation authority.
   `validate_transaction` remains the sole transfer-validation authority.

### 5.7 Unknown versions, algorithms, purposes, or fields

| Condition | Code |
|---|---|
| Unknown `signing_profile` / receipt profile | `profile_unsupported` |
| Reserved or unknown `signature_purpose` | `purpose_unsupported` |
| Unknown / omitted / weaker `signer_algorithm_profile` | `algorithm_unsupported` / `algorithm_downgrade_rejected` |
| Unknown field on a typed object | `schema_invalid` |
| Reordered fields vs declared order | `schema_invalid` |
| Float / NaN / Infinity / non-integer amount | `json_invalid` or `amount_invalid` as applicable |

## 6. Signed-receipt envelope

### 6.1 Profile

| Constant | Value |
|---|---|
| `receipt_profile` | `l28-uaii-signed-receipt/v0.1` |
| Currency / asset where applicable | `"L28"` |
| Maximum complete receipt envelope UTF-8 bytes | `16384` |

### 6.2 Complete signed-facts object (`UaiiSignedReceiptFacts`)

Exact field order (**27 fields**). These are the final receipt facts after
construction (§6.2.3):

| # | Field | Type | Semantics |
|---|---|---|---|
| 1 | `receipt_profile` | string | MUST equal `l28-uaii-signed-receipt/v0.1` |
| 2 | `receipt_id` | string | 64 lowercase hex; derived per §6.2.4 |
| 3 | `prior_receipt_id` | string or `null` | `null` for first receipt; else exact preceding `receipt_id` (§6.3) |
| 4 | `correlation_id` | string | 64 lowercase hex |
| 5 | `request_id` | string | 64 lowercase hex |
| 6 | `quote_id` | string | 64 lowercase hex |
| 7 | `service_result_id` | string | 64 lowercase hex |
| 8 | `payer_public_identity` | string | non-empty; UTF-8 `1..256` bytes |
| 9 | `provider_public_identity` | string | non-empty; UTF-8 `1..256` bytes |
| 10 | `asset_id` | string | MUST equal `"L28"` |
| 11 | `amount` | integer | exact integer `> 0` within Protocol transfer bounds when a transfer is cited |
| 12 | `purpose` | string | MUST equal `signed_receipt` |
| 13 | `created_at` | integer | Unix seconds `>= 0` |
| 14 | `expires_at` | integer | Unix seconds; MUST be `> created_at` |
| 15 | `receipt_nonce` | string | F57/F64 nonce grammar `1..256` UTF-8 bytes; no U+0000 |
| 16 | `transaction_id` | string | 64 lowercase hex when independently available; otherwise `""` |
| 17 | `settlement_status` | string | enum §6.3; immutable for this `receipt_id` |
| 18 | `signer_algorithm_profile` | string | MUST equal `ed25519-pure/v0.1` |
| 19 | `signer_public_key_id` | string | §5.2 |
| 20 | `signer_public_key` | string | `^[0-9a-f]{64}$` |
| 21 | `signed_payload_digest` | string | `^[0-9a-f]{64}$` |
| 22 | `signature` | string | `^[0-9a-f]{128}$` |
| 23 | `signing_authorized` | boolean | MUST be `false` |
| 24 | `spend_authorized` | boolean | MUST be `false` |
| 25 | `settlement_authorized` | boolean | MUST be `false` |
| 26 | `ledger_mutated` | boolean | MUST be `false` |
| 27 | `execution_authorized` | boolean | MUST be `false` |

One canonical null representation for `prior_receipt_id`: JSON `null` only
(not `""`, not omitted). Omission or alternate null spellings →
`schema_invalid`.

### 6.2.1 Unsigned facts (`UaiiSignedReceiptUnsignedFacts`)

Exact ordered object used for signing. It MUST contain the §6.2 fields
**except exactly**:

- `receipt_id`
- `signed_payload_digest`
- `signature`

Exact unsigned field order (**24 fields**):

| # | Field |
|---|---|
| 1 | `receipt_profile` |
| 2 | `prior_receipt_id` |
| 3 | `correlation_id` |
| 4 | `request_id` |
| 5 | `quote_id` |
| 6 | `service_result_id` |
| 7 | `payer_public_identity` |
| 8 | `provider_public_identity` |
| 9 | `asset_id` |
| 10 | `amount` |
| 11 | `purpose` |
| 12 | `created_at` |
| 13 | `expires_at` |
| 14 | `receipt_nonce` |
| 15 | `transaction_id` |
| 16 | `settlement_status` |
| 17 | `signer_algorithm_profile` |
| 18 | `signer_public_key_id` |
| 19 | `signer_public_key` |
| 20 | `signing_authorized` |
| 21 | `spend_authorized` |
| 22 | `settlement_authorized` |
| 23 | `ledger_mutated` |
| 24 | `execution_authorized` |

Alternate exclusion sets, self-reference, or iterative derivation of these
bytes MUST NOT be used.

### 6.2.2 Signable bytes and digest

```text
signable_bytes = L28-UAII-SIGN-V0.1-RECEIPT\x00 || CanonUaii(UaiiSignedReceiptUnsignedFacts)
signed_payload_digest = lowercase_hex(SHA-256(signable_bytes))
```

PureEd25519 MUST sign `signable_bytes`.

### 6.2.3 Mandatory construction order

Implementations (when separately authorized) MUST follow this order exactly:

1. Populate `UaiiSignedReceiptUnsignedFacts` completely (§6.2.1).
2. Serialize `approved_canonical_payload = CanonUaii(UaiiSignedReceiptUnsignedFacts)`.
3. Enforce size bounds (§3.6).
4. Form `signable_bytes` and `signed_payload_digest` (§6.2.2).
5. Obtain approved `ApprovalDecision` binding that digest (§8).
6. Perform external replay check (§10).
7. Invoke isolated signer over `signable_bytes`; obtain `signature`.
8. Insert `signed_payload_digest` and `signature` into the complete facts
   object with `receipt_id` temporarily set to `""`.
9. Compute `receipt_id` per §6.2.4.
10. Write `receipt_id` into field 2. After this write, `receipt_id` MUST NOT be
    mutated.
11. Serialize the complete receipt envelope and enforce the `16384` bound.

**Prohibited:** signing an object that already contains `signature` or
`signed_payload_digest`; computing `receipt_id` before signature insertion;
mutating `receipt_id` after step 10; excluding any field other than the three
listed in §6.2.1 from unsigned facts.

### 6.2.4 Receipt identifier

Let `UaiiSignedReceiptFactsWithEmptyId` be the complete §6.2 object after step 8
(digest and signature present) with `receipt_id` equal to the empty string
`""` only.

```text
receipt_id = lowercase_hex(SHA-256(
  UTF8("L28-UAII-SIGN-V0.1-RECEIPT-ID") || CanonUaii(UaiiSignedReceiptFactsWithEmptyId)
))
```

Verification MUST reconstruct the same unsigned facts, the same
`signable_bytes`, the same digest, the same signature input, and the same
receipt-ID preimage. Mismatch → `digest_mismatch`, `signature_invalid`, or
`receipt_id_invalid` as applicable.

### 6.3 Settlement status enum and immutable transitions

| Value | Meaning | Allowed basis |
|---|---|---|
| `authorization_signed` | Authorization intent signed into a receipt | Signature + bindings; **not** ledger proof |
| `service_result_signed` | Service-result commitment reflected in a receipt | Signature + bindings; **not** ledger proof |
| `settlement_pending` | Settlement not yet confirmed | Absence of independent ledger evidence |
| `settlement_confirmed` | Settlement confirmed | **Only** independently verified ledger evidence |
| `settlement_failed` | Settlement failed | Independent failure evidence |
| `refunded` | Refund completed under linked confirmed receipt | Linked refund + independently validated refund transaction; **no** minting or supply change |

**Immutability:** `settlement_status` MUST be immutable for a given
`receipt_id`. Any status change MUST create a **new** independently signed
receipt with a **new** `receipt_id`.

**Linkage:** `prior_receipt_id` MUST be JSON `null` for the first receipt in a
flow. For a transition receipt, `prior_receipt_id` MUST equal the exact
preceding receipt’s `receipt_id`.

**Genesis status (when `prior_receipt_id` is `null`):**
`settlement_status` MUST be exactly one of:

- `authorization_signed`
- `service_result_signed`

Every other genesis status MUST fail with `settlement_transition_invalid`.

**Allowed transitions** (when `prior_receipt_id` is non-null; prior status →
new status). The prior receipt identified by `prior_receipt_id` MUST exist and
MUST carry the “From” status:

| From | To |
|---|---|
| `authorization_signed` | `settlement_pending` |
| `service_result_signed` | `settlement_pending` |
| `settlement_pending` | `settlement_confirmed` |
| `settlement_pending` | `settlement_failed` |
| `settlement_confirmed` | `refunded` |

Every other transition MUST be rejected (`settlement_transition_invalid`).

Additional rules:

1. `settlement_confirmed` still requires independently validated ledger
   evidence (`transaction_id` non-empty; facts match; Protocol /
   `validate_transaction` / ledger evidence under existing authorities).
2. `refunded` requires `prior_receipt_id` pointing to a
   `settlement_confirmed` receipt and a separately validated refund
   transaction. It MUST NOT mint or alter supply constants.
3. A receipt MUST NOT claim `settlement_confirmed` merely because it is
   signed (`settlement_claim_invalid`).
4. Signer-identity binding for each status MUST follow §5.6 exactly.

### 6.4 Verifier-only fields (MUST NOT be signed as authoritative facts)

A surrounding envelope MAY include:

| Field | Rule |
|---|---|
| `verification_status` | `verified` / `rejected` / `unchecked`; MUST NOT appear inside signed facts |
| `verifier_code` | Stable code from §9; empty detail |
| `verifier_checked_at` | Integer Unix seconds of verification |

Embedding `verification_status` inside signed facts MUST be rejected
(`schema_invalid`).

### 6.5 Relationship to Foundation 56 unsigned payment receipt

Foundation 56 `UaiiPaymentReceipt` remains the unsigned/citation receipt shape
for `get_payment_receipt`. Foundation 64 defines a **distinct** signed-receipt
profile. Adapters MUST NOT treat F56 unsigned receipts as F64 signed receipts.

## 7. Binding and invariants

### 7.1 Deterministic binding graph

The following MUST bind with exact equality where present:

```text
UAII request
  ↔ quote / service identifiers, parties, amount, purpose, expiry, nonce
  ↔ ApprovalDecision (digest, purpose, key handle, limits, decision=approved)
  ↔ unsigned payment / service context (public identifiers)
  ↔ UaiiSignedReceiptUnsignedFacts / signed receipt (§6)
  ↔ optional validated transaction (transaction_id + validate_transaction facts)
  ↔ optional later settlement evidence (ledger acceptance)
  ↔ optional prior_receipt_id linkage for status transitions
```

Any mismatch of parties, L28 amount, purpose, quote, expiry, nonce,
correlation, service commitment, approval digest/key, or transaction facts
MUST fail closed (`binding_invalid` or a more specific code).

### 7.2 Protected economic and ledger facts (unchanged)

| Fact | Value |
|---|---|
| Hard cap | `28_000_000` L28 |
| Emission ceiling | `11_130_000` L28 |
| Historically mined | `2_824_584` L28 |
| Treasury locked | `500_000` L28 |
| Circulating snapshot | `2_324_584` L28 |

Additional frozen rules:

- **No-tip rule:** Receipts and signable objects MUST NOT introduce a Protocol
  ledger tip field, tip selector, or `LEDGER-TIP` authority.
- Issuance, validation, consensus, and historical evidence remain frozen under
  Protocol v1.0.0.
- Refunds MUST NOT discretionary-mint or alter supply constants.

## 8. Approval decision and limits

### 8.1 Ordered `ApprovalDecision` (exact 21 fields)

| # | Field | Type / constraint |
|---|---|---|
| 1 | `approval_profile` | string; MUST equal `l28-f64-approval-decision/v0.1` |
| 2 | `approval_id` | string; 64 lowercase hex |
| 3 | `request_id` | string; 64 lowercase hex |
| 4 | `correlation_id` | string; 64 lowercase hex |
| 5 | `quote_id` | string; 64 lowercase hex |
| 6 | `payer_identity` | string; UTF-8 `1..256` bytes |
| 7 | `provider_identity` | string; UTF-8 `1..256` bytes |
| 8 | `asset_id` | string; MUST equal `"L28"` |
| 9 | `amount` | integer; `>= 0` |
| 10 | `purpose` | string; MUST equal `signed_receipt` |
| 11 | `nonce` | string; F64 nonce grammar §10.2 |
| 12 | `expires_at` | integer; Unix seconds (Foundation 57 timestamp rules) |
| 13 | `signable_digest` | string; `^[0-9a-f]{64}$`; MUST equal `signed_payload_digest` |
| 14 | `signer_key_handle` | string; non-secret; UTF-8 `1..256` bytes |
| 15 | `policy_id` | string; UTF-8 `1..256` bytes |
| 16 | `per_transaction_limit` | integer; `>= 0` |
| 17 | `cumulative_limit_evaluation` | object; exact §8.5 order |
| 18 | `decision` | string; exact enum `approved` or `rejected` |
| 19 | `decided_at` | integer; Unix seconds |
| 20 | `approver_identity` | string; UTF-8 `1..256` bytes; public only |
| 21 | `approval_signature_reference` | MUST be JSON `null` only; reserved and unauthorized in Foundation 64 |

Rules:

1. Exact field order; unknown fields → `schema_invalid`.
2. Signing MUST NOT proceed unless an `ApprovalDecision` with
   `decision=approved` is present.
3. `signable_digest`, `purpose`, `signer_key_handle`, parties, `asset_id`,
   `amount`, `request_id`, `quote_id`, and `correlation_id` MUST exactly match
   the unsigned facts / signing invocation. The approval’s bound signer key
   MUST be consistent with the §5.6 status→identity mapping for the receipt’s
   `settlement_status`.
4. Approval MUST be unexpired under Foundation 57 skew rules relative to
   `expires_at` / `decided_at` as evaluated by the approval authority.
5. `amount` MUST be `<= per_transaction_limit`.
6. Any mismatch → fail closed (`approval_required`,
   `approval_digest_mismatch`, `approval_binding_invalid`,
   `authorization_expired`, or `approval_threshold_exceeded`).

### 8.5 Cumulative limit evaluation (external policy input; no F64 store)

`cumulative_limit_evaluation` is an **externally supplied, already-evaluated**
approval-policy object. Foundation 64 MUST NOT create or maintain an
accumulator, replay database, ledger, or persistent store. The external
approval authority owns state; Foundation 64 only validates this bounded
decision object.

Exact ordered fields:

| # | Field | Type / constraint |
|---|---|---|
| 1 | `policy_id` | string; UTF-8 `1..256`; MUST equal `ApprovalDecision.policy_id` |
| 2 | `subject_identity` | string; UTF-8 `1..256` |
| 3 | `asset_id` | string; MUST equal `"L28"` |
| 4 | `window_start` | integer; Unix seconds `>= 0` |
| 5 | `window_end` | integer; Unix seconds; MUST be `> window_start` |
| 6 | `prior_authorized_amount` | integer; `>= 0` |
| 7 | `proposed_amount` | integer; `>= 0`; MUST equal `ApprovalDecision.amount` |
| 8 | `cumulative_maximum` | integer; `>= 0` |
| 9 | `evaluation_timestamp` | integer; Unix seconds |
| 10 | `evaluation_result` | string; exact enum `pass` or `fail` |

Normative inequality when `evaluation_result=pass`:

```text
prior_authorized_amount + proposed_amount <= cumulative_maximum
```

Arithmetic MUST use exact integers without overflow wrapping. If the sum would
exceed the JSON safe integer range used by Foundation 56
(`9007199254740991`), evaluation MUST be `fail`.

Missing object, stale evaluation (outside the stated window relative to
`evaluation_timestamp` under F57 skew), inconsistent identities/amounts,
overflow, `evaluation_result=fail`, or failed inequality MUST fail closed with
`approval_threshold_exceeded` or `cumulative_limit_invalid`.

### 8.6 Human/operator approval boundary

1. Approval MUST occur **outside** the signer.
2. Approval MUST be an `ApprovalDecision` (§8.1).
3. Prompts and tools MUST NOT receive private material.
4. Model context MUST NOT be treated as an approval authority unless a later
   foundation explicitly defines a non-secret policy engine (still without
   keys).

### 8.7 Refund linkage

Refunded status transitions MUST reference the prior confirmed `receipt_id`
via `prior_receipt_id` and MUST NOT alter protected supply facts.
Discretionary minting is forbidden. A reserved `refund_authorization` purpose
MUST NOT be activated by this Foundation (`purpose_unsupported`).

### 8.8 Deterministic rejection codes (authorization path)

| Code | Condition |
|---|---|
| `approval_required` | Missing approval decision |
| `approval_digest_mismatch` | Approval bound to different digest |
| `approval_binding_invalid` | Party/amount/purpose/key mismatch |
| `approval_threshold_exceeded` | Per-tx or cumulative limit failed |
| `cumulative_limit_invalid` | Malformed/stale/inconsistent cumulative object |
| `quote_expired` | Quote past expiry (+ skew rules as applicable) |
| `authorization_expired` | Authorization/approval past expiry |
| `replay_detected` | Duplicate replay key (§10) |
| `binding_invalid` | Cross-object mismatch |
| `amount_invalid` | Non-integer / out-of-bounds amount |
| `asset_invalid` | Asset not `"L28"` |
| `purpose_unsupported` | Reserved or unknown purpose |
| `settlement_transition_invalid` | Disallowed status transition |
| `secret_material_forbidden` | Forbidden secret field names (F56 list + signing secrets) |
| `input_too_large` | Size bound exceeded |

## 9. Verification contract

Verification MUST use public material only, MUST NOT mutate canonical ledger
state, and MUST emit empty `detail` on all paths.

### 9.1 First-failure precedence

1. Envelope / type / **size** validation (`16384` complete envelope)
2. Structure / profile / purpose validation (`signed_receipt` only)
3. Canonicalization / field-order / unknown-field validation
4. Nonce grammar validation for `receipt_nonce` and any supplied approval/replay
   nonce fields (`nonce_invalid` for malformed, empty, oversized,
   noncanonical, NUL-containing, or otherwise grammar-invalid nonce input)
5. Approval presence and binding checks when approval evidence is supplied to
   the verifier path that requires it
6. Replay checks when an external replay capability is required or provided
   (§10); absent/unavailable/indeterminate capability → exactly
   `replay_detected`
7. Reconstruct `UaiiSignedReceiptUnsignedFacts`; recompute `signable_bytes` and
   digest; compare to `signed_payload_digest` (`digest_mismatch`)
8. Public-key identity binding per §5.6 status→identity map
   (`key_binding_invalid`)
9. Signature verification over `signable_bytes` (PureEd25519)
10. Receipt-ID recomputation (`receipt_id_invalid`)
11. Quote / request / result / transaction / `prior_receipt_id` binding
12. Expiry / skew checks (Foundation 57 `300` seconds)
13. Settlement-status legality: genesis allow-list when `prior_receipt_id` is
    `null`; otherwise exact preceding receipt + allowed transitions only
    (`settlement_transition_invalid`)
14. Optional settlement-evidence verification when
    `settlement_status == settlement_confirmed`

Stop at the first failure.

### 9.2 Bounded leak-safe error codes

| Code | Meaning |
|---|---|
| `ok` | Verification succeeded |
| `input_type_invalid` | Wrong input type |
| `input_too_large` | Exceeds bound |
| `encoding_invalid` | Invalid UTF-8 |
| `json_invalid` | JSON / float / NaN rules |
| `duplicate_key` | Duplicate JSON key |
| `schema_invalid` | Field order/type/unknown field |
| `profile_unsupported` | Unknown receipt/signing profile |
| `purpose_unsupported` | Reserved/unknown purpose |
| `nonce_invalid` | Malformed, empty, oversized, noncanonical, NUL-containing, or otherwise grammar-invalid nonce |
| `algorithm_unsupported` | Unknown `signer_algorithm_profile` |
| `algorithm_downgrade_rejected` | Weaker/foreign suite offered |
| `digest_mismatch` | Recomputed digest ≠ claimed |
| `receipt_id_invalid` | Recomputed receipt id ≠ claimed |
| `key_binding_invalid` | Key ≠ §5.6 required identity for `settlement_status` |
| `signature_invalid` | Signature fails |
| `binding_invalid` | Cross-object mismatch |
| `expired` | Past expiry under skew rules |
| `replay_detected` | Duplicate replay key, or required replay capability absent/unavailable/indeterminate |
| `settlement_claim_invalid` | `settlement_confirmed` without evidence |
| `settlement_transition_invalid` | Illegal genesis status or disallowed transition |
| `secret_material_forbidden` | Secret fields present |
| `internal_error` | Fail-closed |

### 9.3 Settlement-evidence rule

When `settlement_status` is `settlement_confirmed`, verification MUST require
independent evidence such that:

1. `transaction_id` is non-empty 64-hex;
2. cited transfer facts match receipt parties/amount/asset;
3. acceptance is demonstrated by Protocol/`validate_transaction`/ledger
   evidence under existing authorities;
4. signature alone is insufficient.

## 10. Replay, expiry, and uniqueness

### 10.1 Ordered `F64SigningReplayKeyMaterial` (exact 13 fields)

| # | Field | Type / constraint |
|---|---|---|
| 1 | `replay_profile` | string; MUST equal `l28-f64-signing-replay/v0.1` |
| 2 | `signer_key_handle` | string; non-secret; UTF-8 `1..256` |
| 3 | `signature_purpose` | string; MUST equal `signed_receipt` |
| 4 | `payer_identity` | string; UTF-8 `1..256` |
| 5 | `provider_identity` | string; UTF-8 `1..256` |
| 6 | `asset_id` | string; MUST equal `"L28"` |
| 7 | `amount` | integer; `>= 0` |
| 8 | `request_id` | string; 64 lowercase hex |
| 9 | `quote_id` | string; 64 lowercase hex |
| 10 | `correlation_id` | string; 64 lowercase hex |
| 11 | `nonce` | string; §10.2 |
| 12 | `expires_at` | integer; Unix seconds |
| 13 | `signed_payload_digest` | string; `^[0-9a-f]{64}$` |

### 10.2 Nonce grammar

Aligned with Foundation 57:

- Nonce strings (`receipt_nonce`, `ApprovalDecision.nonce`, replay `nonce`)
  MUST have UTF-8 byte length `1..256` and MUST NOT contain U+0000.
- Violations → `nonce_invalid`.

### 10.3 Replay key

```text
replay_key = lowercase_hex(SHA-256(
  UTF8("L28-F64-SIGNING-REPLAY-V0.1") || CanonUaii(F64SigningReplayKeyMaterial)
))
```

Uniqueness scope: the `replay_key` MUST be unique through
`expires_at + UAII_CLOCK_SKEW_TOLERANCE_SECONDS` where
`UAII_CLOCK_SKEW_TOLERANCE_SECONDS = 300` (Foundation 57).

### 10.4 Store ownership and duplicate behavior

1. Foundation 64 **creates no store** and MUST NOT introduce a replay database
   or other persistent replay state. The external approval/replay authority
   owns replay state.
2. If required external replay capability is absent, unavailable,
   indeterminate, or cannot prove uniqueness → the result MUST be exactly
   `replay_detected`.
3. If the replay key was previously seen within the uniqueness scope → the
   result MUST be exactly `replay_detected`.
4. Duplicate receipts MAY return the byte-identical prior receipt **only** when
   an external authority proves both the same `replay_key` **and** complete
   receipt bytes match; otherwise reject with exactly `replay_detected`.

### 10.5 Quote and authorization expiration

- Quote and authorization/approval `expires_at` MUST be enforced.
- Clock skew MUST use Foundation 57
  `UAII_CLOCK_SKEW_TOLERANCE_SECONDS = 300` for envelope-style wall-clock
  comparisons where this contract performs skew-sensitive checks.
- Expired quote reuse MUST fail (`quote_expired` / `authorization_expired`).

## 11. Security and threat model

| Threat | Mitigation |
|---|---|
| Prompt injection requesting keys or arbitrary signatures | Keys never enter prompts/tools; required `ApprovalDecision`; digest-only and arbitrary-byte signing forbidden |
| Confused-deputy signing | Explicit approval over `signable_digest`; signer refuses silent approval; only active purpose `signed_receipt` |
| Key substitution | `signer_public_key` / `signer_public_key_id` binding to the exact §5.6 status→identity field only |
| Algorithm downgrade | Strict `signer_algorithm_profile` allow-list (`ed25519-pure/v0.1` only) |
| Purpose/domain confusion | Active vs reserved domains; reserved → `purpose_unsupported` |
| Receipt forgery / field substitution | Unsigned-facts exclusion set; exact construction order; digest+sig+receipt_id recomputation |
| Replay / duplicate submission | Exact `replay_key` preimage; external uniqueness scope through expiry+skew |
| Expired authorization reuse | Expiry + F57 skew `300` |
| Amount/recipient mutation | Exact binding equalities; signer MUST NOT alter bytes |
| False settlement claims | Immutable status per `receipt_id`; `settlement_confirmed` requires ledger evidence |
| Malicious provider delivery claims | Status/evidence-class distinction; reserved service-result purpose not activated |
| Secret leakage | Empty diagnostics; forbidden secret I/O; `private_material_exposed=false` |
| Compromised adapters vs signer containment | Private keys only in isolated signer; adapters verify public receipts only |

## 12. Conformance requirements (future; currently unauthorized)

The following vectors are **specified for a future separately authorized
conformance suite** for the **active** purpose `signed_receipt` only. They
MUST NOT be executed, implemented, or treated as activated by Foundation 64:

1. Deterministic `CanonUaii(UaiiSignedReceiptUnsignedFacts)`, `signable_bytes`,
   and `signed_payload_digest` equality.
2. Valid PureEd25519 verification over `signable_bytes` under
   `ed25519-pure/v0.1` with public test keys generated only in a future
   authorized harness (no secrets in this document).
3. One-field mutation failures for every unsigned-facts field and every
   complete signed-facts field.
4. Wrong domain / reserved-purpose / wrong-version / wrong-key /
   wrong-`signer_algorithm_profile` failures (`purpose_unsupported`,
   `algorithm_unsupported`, `algorithm_downgrade_rejected`).
5. Wrong signer identity for each `settlement_status` under §5.6
   (`key_binding_invalid`).
6. Digest-only signing refusal (`signer_payload_mismatch`).
7. Expired and replayed requests (`expired`, `replay_detected`); missing
   required replay capability (`replay_detected`).
8. Quote / amount / party / result / approval mismatch failures.
9. Illegal genesis statuses, illegal settlement-status transitions, and forged
   `settlement_confirmed` rejection.
10. `receipt_id` recomputation and immutability checks.
11. Repeated-run byte equality of canonical objects and digests.
12. No-secret-output verification.
13. Size-bound failures at `16384` / `16512`.
14. `nonce_invalid` for grammar-invalid nonce inputs.

Reserved purposes MUST appear only as negative vectors that expect
`purpose_unsupported`. They MUST NOT appear as positive deterministic-byte
vectors until a later specification defines their schemas.

**Still unauthorized:** implementation, signer processes, key creation,
adapters, SDKs, settlement, testnet execution, staging of implementation
code, and any runtime activation.

## 13. Relationship to Foundations 55–63

| Foundation | Relationship |
|---|---|
| F55 | Disposable sandbox lifecycle; unaffected |
| F56 | Parent UAII ops, CanonUaii, secret ban, unsigned receipt shape |
| F57 | Skew `300`, nonce grammar, no-tip ledger binding |
| F58 / F62 / Foundation 63 | UAII reference-core processing and resource limits; UAII remains sole processing interface; `validate_transaction` sole transfer validation authority |
| F59–F61 | Resource-limit evidence/decision/readiness; unchanged |
| M2M / F5 | Ed25519 verify-only precedent; distinct domains; no M2M canonicalize for UAII signing payloads |

## 14. Non-normative examples

**Non-normative.** Illustrative flow labels only — not executable, not real
keys, not real signatures:

1. UAII returns an unsigned payment object.
2. Constructor builds `UaiiSignedReceiptUnsignedFacts` and displays
   `signed_payload_digest`.
3. Operator issues `ApprovalDecision` with `decision=approved`.
4. Isolated signer receives `approved_canonical_payload` (required) and signs
   `signable_bytes`.
5. Receipt is completed with digest, signature, then `receipt_id`;
   `settlement_status=authorization_signed`; `prior_receipt_id=null`.
6. Verifier accepts signature and bindings; settlement remains unconfirmed.
7. A later status change uses a new receipt with a new `receipt_id` and
   `prior_receipt_id` set to the previous id.

## 15. Document history

| Version | Change |
|---|---|
| v0.1 | Initial Foundation 64 contract; revised to resolve audit findings B1, H1, H2, M1–M6 (specification only) |
