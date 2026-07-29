# Foundation 65 Implementation Readiness & Conformance Specification v0.1

**Status:** Documentation only (readiness + conformance plan; non-activation;
non-implementation)

**Profile:** `l28-foundation64-implementation-readiness-conformance/v0.1`

**Parent normative contract:** Foundation 64 —
`docs/foundation64_isolated_local_signing_signed_receipt_contract.md`
(`l28-isolated-local-signing-signed-receipt/v0.1`)

**Related foundations:** Foundations 56–63 (UAII / reference core / resource
limits); Foundation 5 / M2M verify-only Ed25519 patterns (non-authority for
UAII signing payloads)

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Base commit:** `3f34ff202b5bd1afb6298b50d834c332982ae236`

**Branch:** `foundation65-implementation-readiness-conformance-spec`

**Normative subordination:** Protocol v1.0.0; then Foundation 56; then
Foundation 57; then Foundations 58/62/63 for UAII processing; then Foundation
64 for the signed-receipt contract; then this readiness/conformance plan. This
document MUST NOT amend Foundation 64 field tables, domains, transitions, or
error codes. On conflict, Foundation 64 prevails for signing/receipt rules.

## 1. Status and authority

1. Foundation 65 is **documentation-only**. It maps implementation readiness
   and defines a deterministic conformance plan for a **later, separately
   authorized** Foundation 64 implementation.
2. Foundation 64 remains the **sole normative** isolated-local-signing and
   signed-receipt contract.
3. UAII (`coin/uaii_reference_core.process_uaii_request`) remains the **sole
   protocol-processing interface** for AI/agent access operations defined by
   Foundations 56–63.
4. `coin.tx_validation.validate_transaction` remains the **sole
   transaction-validation authority**.
5. Foundation 65 MUST NOT create or imply an alternate processor, validator,
   canonicalizer, signer, receipt authority, wallet, ledger, accumulator, or
   persistent store.
6. M2M canonicalization (`coin.m2m_verifier.canonicalize` /
   `canonical_bytes`) MUST NOT be reused for Foundation 64 UAII signable
   objects (Foundation 64 §5.1). MCP adapters, if ever authorized later, MUST
   likewise not invent a third canonicalizer for those objects.

### 1.1 Mandatory invariants (this Foundation)

| Invariant | Required value |
|---|---|
| `execution_authorized` | `false` |
| `implementation_authorized` | `false` |
| `signing_authorized` | `false` |
| `spend_authorized` | `false` |
| `settlement_authorized` | `false` |
| `ledger_mutated` | `false` |
| `private_material_exposed` | `false` |

**Note (non-authority):** At baseline, `coin/uaii_reference_core.py` sets
`implementation_authorized = True` for the Foundation 63 UAII reference core.
That flag authorizes **UAII processing implementation already on main**, not
Foundation 64 signing/receipt implementation. Foundation 65 and any future F64
implementation milestone MUST keep the seven invariants above false until
explicit separate operator authorization flips only the specifically named
flags for that milestone.

## 2. Scope and non-goals

### 2.1 In scope

- Exact repository integration map for Foundation 64 responsibilities
- Data-contract and status-model conformance obligations (by reference to F64)
- Error/precedence matrix and numbered conformance-vector catalog
- Disposable-key **test design** (no key generation here)
- Future implementation allowlist and focused test plan
- Exit criteria before an implementation candidate may be proposed

### 2.2 Non-goals (unauthorized)

- Implementation of signer, verifier, approval engine, or F64 modules
- Real keys, signing, spending, settlement, ledger mutation, broadcast
- Adapters, testnets, networking, miners, wallets, services, deployment
- M2M/MCP canonicalizer reuse for F64 signable objects
- Production or historical data mutation
- Staging/commit/push of implementation code
- Persistent F64 replay/accumulator stores

## 3. Exact repository integration map

Capability status legend:

| Status | Meaning |
|---|---|
| **EXISTING** | Reusable as-is for the cited responsibility |
| **EXTEND** | Exists but requires separately authorized F64-specific wiring |
| **MISSING** | Not present; later greenfield under a new authorization |
| **FORBIDDEN** | Must not be used as the F64 authority/path |

### 3.1 Integration table

| F64 responsibility | Current path / symbol | Status | Required future change | Prohibited alternative | Focused verification |
|---|---|---|---|---|---|
| UAII protocol processing | `coin/uaii_reference_core.py` `process_uaii_request` | **EXISTING** | Keep sole entry; do not fork | Second processor / parallel UAII | Process still sole; `uaii.signing` remains forbidden until separate auth |
| Unsigned F56 payment receipt (citation) | `coin/uaii_reference_core.py` `_op_get_payment_receipt` (`l28-uaii-payment-receipt/v0.1`) | **EXISTING** | Distinct from F64 signed receipt; optional later mapping only under fail-closed rules (F64 §6.5) | Treating F56 receipt as F64 signed receipt | Cross-profile rejection vector |
| CanonUaii / exact-order JSON | `coin/uaii_json.py` `canon_uaii`, `decode_uaii_json`, `serialize_uaii_response` | **EXISTING** | Reuse for F64 unsigned facts / approval / replay objects | `coin.m2m_verifier.canonicalize` | Golden exact-order vectors; prove M2M unused |
| Resource / size gates (inherited) | `coin/uaii_resource_limits.py` L1–L6; F64 §3.6 bounds `16384`/`16512` | **EXISTING** + **EXTEND** | Apply F64 envelope/payload/`signable_bytes` bounds before crypto | Weakening F63 limits | Size vectors at 16384/16512 |
| Transaction validation | `coin/tx_validation.py` `validate_transaction` | **EXISTING** | Sole delegate for settlement evidence / proposed transfers | Alternate validators | Failure vectors map to F64 binding codes |
| Economic constants | `coin/tx_validation.py` `L28_MAX_SUPPLY`, `L28_EMISSION_CEILING`, `L28_HISTORICAL_MINED`, `L28_HALVING_INTERVAL`, `L28_REWARD_SCHEDULE`, `L28_HISTORICAL_LAST_ENTRY`, `L28_NEXT_HEIGHT_AFTER_CHECKPOINT` | **EXISTING** | Cite only; no mutation | Reminting / supply edits | Economics vectors |
| Ledger no-tip / replay cardinality | `coin/ledger.py` `BlocklessLedger._seen_tx_ids` | **EXISTING** | Cardinality/evidence only; no tip field | Tip selector / `LEDGER-TIP` | No-tip vectors |
| Ed25519 verify-only precedent | `coin/m2m_verifier.py` `Ed25519PublicKey`, `verify_envelope`; `coin/creator_wallet_transfer_intent_authorization.py` `_verify_signature` | **EXISTING** (pattern) | Future F64 verifier MUST use PureEd25519 over F64 `signable_bytes` + F64 domains; hex encodings per F64 §5.2 | Reusing M2M `DOMAIN_SIGNATURE` / base64url suite as F64 receipt profile; private-key import in verifier | Wrong-domain / wrong-encoding vectors |
| M2M replay store | `coin/m2m_replay_registry.py` `ReplayRegistry` | **FORBIDDEN** for F64 ownership | F64 creates no store; external approval/replay authority only (F64 §10.4) | Wiring F64 keys into M2M SQLite registry as protocol store | Missing capability → exact `replay_detected` |
| UAII envelope replay (F57) | `coin/uaii_reference_core.py` `_replay_key`, `_envelope_replay_check` | **EXISTING** (UAII envelope) | Distinct from F64 `F64SigningReplayKeyMaterial` | Collapsing F64 replay into UAII envelope store as F64 authority | Separate vector classes |
| Skew / nonce grammar | `coin/uaii_reference_core.py` `UAII_CLOCK_SKEW_TOLERANCE_SECONDS=300`, `_check_nonce_string` | **EXISTING** | Reuse 300s skew + 1..256 nonce grammar for F64 | Alternate skew constants | Expiry / `nonce_invalid` vectors |
| Secret-material ban | `coin/uaii_reference_core.py` `SECRET_KEYS`, `_scan_secrets` | **EXISTING** | Extend scan list only if F64 adds forbidden names under separate auth | Logging secrets | `secret_material_forbidden` |
| F64 unsigned facts (24) | **Absent** | **MISSING** | New module(s) under later allowlist | Embedding into F56 receipt object | Schema exactness vectors |
| F64 signed facts (27) + construction order | **Absent** | **MISSING** | Implement F64 §6.2.3 order exactly | Signing object containing signature/digest | Circularity / ID vectors |
| F64 isolated signer | **Absent** | **MISSING** | Local signer boundary F64 §3; digest-only forbidden | Remote/hosted signer; model-selected keys | Digest-only / arbitrary-byte refusal |
| F64 `ApprovalDecision` (21) | **Absent** | **MISSING** | External approval object F64 §8.1 | Silent approval inside signer | Approval rejection vectors |
| Cumulative limit evaluation | **Absent** as F64 object | **MISSING** | External already-evaluated object F64 §8.5; no F64 accumulator | Implementing cumulative store in-repo as F64 authority | Limit rejection vectors |
| Status→signer identity map | **Absent** | **MISSING** | F64 §5.6 map | “payer or provider” discretion | Wrong-signer vectors |
| Settlement-status transitions | **Absent** (F64) | **MISSING** | Genesis two + five transitions F64 §6.3 | In-place status mutation | Transition vectors |
| F64 receipt verifier | **Absent** | **MISSING** | Public verify path F64 §9; empty `detail` | Verifier that signs or mutates ledger | Full precedence suite |
| F64 conformance tests | **Absent** | **MISSING** | New `tests/test_*` under later auth | Checking in private keys | Vector catalog §7 |
| Disposable-key harness | **Absent** for F64 | **MISSING** | Design §8 only here | Keys in fixtures/repo | Non-exposure vectors |

### 3.2 Call-path sketch (future; unauthorized)

```text
UAII process_uaii_request  --unsigned objects-->
ApprovalDecision (external) + replay authority (external)
  -> construct UaiiSignedReceiptUnsignedFacts (24)
  -> CanonUaii via coin.uaii_json.canon_uaii
  -> isolated local signer (signable_bytes; ed25519-pure/v0.1)
  -> insert digest+signature; derive receipt_id (27-field facts)
  -> public verifier (F64 §9 precedence)
  -> optional later settlement adapter
       -> validate_transaction / ledger evidence only
```

No production call path invokes Foundation 64 signing today.

## 4. Data-contract conformance

Normative field tables, orders, types, nullability, encodings, and rejection
codes remain in Foundation 64. Foundation 65 requires future implementations
to preserve:

| Object | Exact count | Foundation 64 section |
|---|---|---|
| `UaiiSignedReceiptUnsignedFacts` | **24** ordered fields | §6.2.1 |
| `UaiiSignedReceiptFacts` | **27** ordered fields | §6.2 |
| `ApprovalDecision` | **21** ordered fields | §8.1 |
| `cumulative_limit_evaluation` | **10** ordered fields | §8.5 |
| `F64SigningReplayKeyMaterial` | **13** ordered fields | §10.1 |

Rules:

1. Unknown fields, reorders, wrong types, silent defaults, coercion, and field
   dropping MUST fail closed (`schema_invalid` / type-specific codes per F64).
2. `prior_receipt_id` MUST use JSON `null` only (not `""`, not omitted).
3. `approval_signature_reference` MUST be JSON `null` only in F64.
4. Active purpose MUST be exactly `signed_receipt`; reserved purposes →
   `purpose_unsupported`.
5. Canonicalization MUST use `canon_uaii` (`sort_keys=false`), never M2M
   sorted canonicalize.

### 4.1 Non-circular construction proof (test obligation)

Future tests MUST demonstrate, without private-key material in the repository:

1. Unsigned facts exclude exactly `receipt_id`, `signed_payload_digest`,
   `signature`.
2. `signable_bytes = domain_prefix || CanonUaii(unsigned_facts)`.
3. Digest = lowercase hex SHA-256 of `signable_bytes`.
4. PureEd25519 signs `signable_bytes`, not the digest.
5. Digest and signature are inserted before `receipt_id` derivation.
6. `receipt_id` is computed once from the 27-field object with
   `receipt_id=""`.
7. Mutating any unsigned field changes digest and invalidates the signature;
   recomputed `receipt_id` mismatches if post-signature fields change.

## 5. Deterministic status model

Preserved from Foundation 64 §6.3:

**Genesis** (`prior_receipt_id` is `null`): exactly

- `authorization_signed`
- `service_result_signed`

**Later transitions** (prior must exist and match From status):

| From | To |
|---|---|
| `authorization_signed` | `settlement_pending` |
| `service_result_signed` | `settlement_pending` |
| `settlement_pending` | `settlement_confirmed` |
| `settlement_pending` | `settlement_failed` |
| `settlement_confirmed` | `refunded` |

**Signer identity map** (Foundation 64 §5.6):

| `settlement_status` | Required identity field |
|---|---|
| `authorization_signed` | `payer_public_identity` |
| `service_result_signed` | `provider_public_identity` |
| `settlement_pending` | `payer_public_identity` |
| `settlement_confirmed` | `payer_public_identity` |
| `settlement_failed` | `payer_public_identity` |
| `refunded` | `payer_public_identity` |

Illegal, skipped, duplicated, reordered, in-place, or ambiguous transitions
MUST fail with `settlement_transition_invalid`. Status is immutable per
`receipt_id`. Transition vectors MUST NOT execute settlement; they only
construct/verify receipt objects and cited evidence shapes.

## 6. Error and precedence matrix

Verification first-failure order (Foundation 64 §9.1) MUST be implemented as:

1. size → 2. structure/profile/purpose → 3. canonicalization → 4.
   **`nonce_invalid`** → 5. approval → 6. replay (`replay_detected`) → 7.
   digest → 8. key binding → 9. signature → 10. receipt ID → 11. bindings →
   12. expiry/skew → 13. settlement-status legality → 14. optional settlement
   evidence.

Exact requirements:

- Grammar-invalid nonces → **`nonce_invalid`** (sole nonce grammar code).
- Required replay capability absent/unavailable/indeterminate/non-proving →
  exactly **`replay_detected`** (no alternate refuse codes).
- Previously seen replay key → exactly **`replay_detected`**.
- All paths: empty diagnostic `detail`; no secret leakage.

Acceptance/rejection outcomes for vectors in §7 MUST use only the bounded
codes defined in Foundation 64 §§3.8, 8.8, and 9.2 (plus UAII/Protocol codes
when delegated). Implementation-specific exceptions MUST be mapped to
`internal_error` / `signer_internal_error` without changing protocol results.

## 7. Conformance-vector catalog

All vectors are **specified for a future separately authorized suite**. None
are executed by Foundation 65. Private keys MUST NOT appear in this document.

Fixture rule: deterministic JSON/byte fixtures use public placeholders only
(e.g. fixed public identities, hex zeros patterns labeled `TEST_PUBLIC_*`).
Where a disposable keypair is required later, mark
`disposable_keypair_required_later=true`.

| Vector ID | Purpose | Preconditions | Deterministic input (summary) | Expected outcome | Exact status/error | Invariant evidence | Disposable key later |
|---|---|---|---|---|---|---|---|
| V-01 | Valid unsigned construction | F64 unsigned schema | Minimal valid 24-field unsigned facts | accept construct | `ok` / construct success | flags false; CanonUaii stable | false |
| V-02 | Valid signed receipt | approval+payload | Full construction order §6.2.3 | verify ok | `ok` | flags false; no ledger mutate | true |
| V-03 | Missing required unsigned field | each of 24 | Omit one field | reject | `schema_invalid` | no partial accept | false |
| V-04 | Unexpected field | extra property | Add `extra_field` | reject | `schema_invalid` | — | false |
| V-05 | Wrong type | type flip | `amount` as string | reject | `amount_invalid` / `schema_invalid` | — | false |
| V-06 | Altered approved payload | after approval | Flip one unsigned byte | reject sign/verify | `signer_payload_mismatch` / `digest_mismatch` | — | true |
| V-07 | Digest mismatch | forged digest | Wrong `signed_payload_digest` | reject | `digest_mismatch` | — | true |
| V-08 | Receipt-ID mismatch | forged id | Wrong `receipt_id` | reject | `receipt_id_invalid` | — | true |
| V-09 | Malformed signature | bad hex/length | Truncated/`G` nibble | reject | `signature_invalid` | — | false |
| V-10 | Wrong signer | key≠map | Provider key on `authorization_signed` | reject | `key_binding_invalid` | — | true |
| V-11 | Wrong algorithm profile | suite swap | `signer_algorithm_profile≠ed25519-pure/v0.1` | reject | `algorithm_unsupported` / `algorithm_downgrade_rejected` | — | false |
| V-12 | Invalid genesis status | `prior_receipt_id=null` | `settlement_pending` genesis | reject | `settlement_transition_invalid` | — | false |
| V-13 | Invalid later transition | prior exists | `authorization_signed`→`refunded` | reject | `settlement_transition_invalid` | — | false |
| V-14 | Nonce invalidity | bad nonce | empty / 257 bytes / NUL | reject | `nonce_invalid` | precedence before approval/replay | false |
| V-15 | Replay detected | prior key seen | Same replay material | reject | `replay_detected` | — | false |
| V-16 | Replay capability unavailable | capability missing | Required check cannot run | reject | `replay_detected` | — | false |
| V-17 | Approval rejection | decision | `decision=rejected` | reject | `approval_required` / binding codes | — | false |
| V-18 | Spending-limit rejection | limits | amount > per-tx or cumulative fail | reject | `approval_threshold_exceeded` / `cumulative_limit_invalid` | — | false |
| V-19 | Expired quote/request | skew 300 | `expires_at` past | reject | `expired` / `quote_expired` / `authorization_expired` | — | false |
| V-20 | Transaction-validation failure | bad transfer | `validate_transaction` would fail | reject | `binding_invalid` / payment validation codes via delegate | sole authority | false |
| V-21 | Canonicalization edge | floats/dups/reorder | float amount; duplicate key; reorder | reject | `json_invalid` / `duplicate_key` / `schema_invalid` | CanonUaii only | false |
| V-22 | Protected-economic violation | constants | Assert drifted supply constants | reject/fail test | test assertion fail | economics frozen | false |
| V-23 | No-tip violation | tip field | Introduce tip selector field | reject | `schema_invalid` / authority fail | no-tip | false |
| V-24 | Authority-boundary violation | alternate validator | Call non-`validate_transaction` path | reject/fail test | authority fail | sole validator | false |
| V-25 | Digest-only signing | no payload | Only `approved_payload_digest` | reject | `signer_payload_mismatch` | — | false |
| V-26 | Reserved purpose | purpose | `payment_authorization` | reject | `purpose_unsupported` | — | false |
| V-27 | Forged settlement_confirmed | no ledger evidence | Status confirmed without evidence | reject | `settlement_claim_invalid` | no settlement auth | false |
| V-28 | Private-material non-exposure | signer/verifier I/O | Scan outputs/logs/fixtures | accept hygiene | no secret bytes | `private_material_exposed=false` | true |
| V-29 | Deterministic repeatability | dual run | Same inputs twice | byte-equal digests/IDs | `ok` | — | true |
| V-30 | M2M canonicalize ban | misuse attempt | Feed object through M2M canonicalize for F64 facts | reject/fail test | anti-pattern fail | distinct digests | false |

## 8. Disposable-key test design (design only)

1. Later authorized tests MAY generate **ephemeral** Ed25519 keypairs in
   process memory or a process-scoped temporary directory created for that
   test.
2. Private keys MUST NEVER enter prompts, source control, committed fixtures,
   logs, tool arguments, environment files, hosted services, or durable
   storage outside the disposable temp scope.
3. Public keys/signatures MAY appear in ephemeral test state only.
4. Tests MUST use disposable temporary ledgers/contexts (patterns already used
   by focused UAII/M2M suites: in-memory context objects; no production ledger
   paths).
5. Cleanup MUST delete temp directories and drop in-memory keys at test end
   (deterministic teardown even on failure).
6. Tests MUST NOT move real balances, spend, settle, broadcast, or mutate
   historical ledgers.
7. **Foundation 65 generates no keys and executes no signing.**

## 9. Future implementation allowlist

A later implementation candidate requires **new operator authorization** and a
**fresh synchronized baseline**. Foundation 65 modifies none of these paths.

### 9.1 Confirmed anticipated paths

| Path | Why necessary |
|---|---|
| `docs/foundation64_isolated_local_signing_signed_receipt_contract.md` | Normative reference only (no edit required for impl) |
| `coin/uaii_json.py` | Reuse `canon_uaii` / decode; likely no change if API sufficient |
| `coin/uaii_reference_core.py` | Sole UAII processor; possible later thin hooks to F64 verify **only under separate auth** |
| `coin/tx_validation.py` | Sole `validate_transaction` delegate; **no economic edits** |
| `coin/ledger.py` | Read-only evidence / no-tip; **no tip introduction** |
| **Proposed future:** `coin/uaii_signed_receipt.py` (name illustrative) | F64 unsigned/signed facts, construction, verify |
| **Proposed future:** `coin/uaii_isolated_signer.py` (name illustrative) | Signer boundary; local key handle only |
| **Proposed future:** `coin/uaii_approval_decision.py` (name illustrative) | ApprovalDecision validation |
| **Proposed future:** `tests/test_uaii_signed_receipt.py` | Conformance vectors V-01+ |
| **Proposed future:** `tests/test_uaii_isolated_signer.py` | Signer boundary / disposable keys |

Proposed future path names are **labels for allowlist planning**, not created
by Foundation 65. Final names MUST be fixed in the implementation
authorization.

### 9.2 Conditional paths

| Path | Condition |
|---|---|
| `coin/uaii_resource_limits.py` | Only if F64 size enforcement is wired through existing walkers |
| `coin/m2m_verifier.py` | **Pattern reference only**; MUST NOT become F64 canonicalize/sign authority |
| `coin/creator_wallet_transfer_intent_authorization.py` | PureEd25519 verify pattern reference only |
| `coin/m2m_replay_registry.py` | MUST NOT own F64 replay state |
| `tests/test_uaii_reference_core.py` / `tests/test_uaii_resource_limits.py` | Regression only; extend only if UAII hooks change under separate auth |

## 10. Focused future test plan

| Group | Covers vectors / obligations |
|---|---|
| Schema exactness | V-01, V-03–V-05, field counts 24/27/21/13 |
| Canonicalization | V-21, V-30, CanonUaii vs M2M |
| Digest and ID construction | V-06–V-08, §4.1 proofs |
| Signature verification | V-02, V-09–V-11 |
| Signer selection | V-10, §5 map |
| Transitions | V-12, V-13, V-27 |
| Approval | V-17, V-18 |
| Replay and nonce | V-14–V-16 |
| Precedence | Ordered first-failure suite across §6 |
| Transaction validation | V-20 |
| Economics | V-22 |
| Authority boundaries | V-23, V-24, V-26 |
| Private-material non-exposure | V-28, §8 |
| Deterministic repeatability | V-29 |

Existing focused regression suites (e.g. UAII 45 tests; M2M/protocol focused
sets) MUST remain green; F64 suites are additive under later authorization.

## 11. Exit criteria

Before an implementation candidate may be proposed, operators MUST confirm:

1. All F64 responsibilities mapped to real baseline paths/symbols or explicitly
   labeled **MISSING** / proposed future paths (this document §3).
2. No unresolved authority collision (UAII sole processor;
   `validate_transaction` sole transfer validator; no M2M canon for F64).
3. No new persistent F64 store introduced by the plan.
4. Vector catalog §7 complete with exact codes and fixture rules.
5. Disposable-key design §8 accepted.
6. Protected facts §12 unchanged vs Protocol/`tx_validation`.
7. Implementation allowlist §9 accepted.
8. Explicit operator authorization obtained for a subsequent implementation
   foundation (not granted by Foundation 65).

**Blocking questions** (must be answered in the implementation authorization,
not by inventing answers here):

| ID | Question | Exit criterion |
|---|---|---|
| Q-65-1 | Final module filenames for signer/receipt/approval | Named in impl auth |
| Q-65-2 | Whether UAII gains a new operation vs external-only F64 API | Chosen without dual processors |
| Q-65-3 | External replay/approval transport binding (local IPC vs library call) | No F64-owned durable store |

## 12. Protected economics

Preserved exactly (evidence: `coin/tx_validation.py`, Foundation 56/57/64,
`docs/m2m/protocol_v0.1.md` for treasury/circulating):

| Fact | Value |
|---|---|
| Hard cap | `28_000_000` L28 |
| Emission ceiling | `11_130_000` L28 |
| Historically mined | `2_824_584` L28 |
| Treasury locked | `500_000` L28 |
| Circulating snapshot | `2_324_584` L28 |
| Halving interval | `210_000` |
| Reward sequence | `28 → 14 → 7 → 3 → 1 → 0` |
| Historical mined-through entry | `100_877` |
| Next canonical height after bootstrap | `100_878` |

Additional frozen rules:

- **No-tip rule** (no Protocol tip field / tip selector / `LEDGER-TIP`)
- Coinbase-only issuance under Protocol rules
- No supply modification, reminting, validation bypass, or authority escalation

## 13. Document history

| Version | Change |
|---|---|
| v0.1 | Initial Foundation 65 implementation readiness and conformance specification (documentation only) |
