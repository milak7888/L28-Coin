# Foundation 59 UAII Finite Resource-Limit Evidence Audit v0.1

**Status:** Evidence audit only (documentation; non-activation; non-implementation)

**Audit profile:** `l28-uaii-finite-resource-limit-evidence-audit/v0.1`

**Parent contracts:**

- Foundation 58 — `l28-uaii-reference-core-implementation/v0.1`
  (`docs/foundation58_uaii_reference_core_implementation_specification_v0.1.md`)
- Foundation 57 — `l28-uaii-reference-core-contract/v0.1`
- Foundation 56 — `l28-universal-ai-access-interface/v0.1`

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Base commit:** `0c07668d978635412b11fa15c52991c0b7ee1ae6`

**Branch:** `foundation59-uaii-finite-resource-limit-evidence-audit`

**Normative subordination:** On conflict, Protocol v1.0.0 prevails; then
Foundation 56; then Foundation 57; then Foundation 58; then this audit.
This document MUST NOT invent UAII numeric limits, authorize implementation, or
amend prior foundations.

## 1. Purpose

Foundation 58 §10.3 deferred six finite parser/expansion/result limits and
gated UAII reference-core implementation on separate specification approval of
finite values with boundary tests.

This audit determines whether the **current repository** supplies
UAII-authoritative evidence for:

1. JSON nesting depth
2. Object-member count
3. Array length
4. Non-nonce string byte length
5. Canonicalized byte length
6. Diagnostic/result byte length

**Verdict summary:** Repository evidence does **not** support assigning a
specific finite UAII value to any of the six prerequisites. Each remains
**UNRESOLVED** pending an explicit operator/specification decision. Incidental
bounds from sandbox, M2M, node-role, or other non-UAII modules are catalogued
as **non-authority** only.

## 2. Authority hierarchy and non-authority sources

### 2.1 Authority (may support a UAII limit)

| Rank | Source | Role for resource limits |
|---|---|---|
| 1 | L28 Protocol v1.0.0 (`PROTOCOL.md`) | Settlement/supply/height authority; no UAII JSON parser limits |
| 2 | Foundation 56 | UAII parent; locks request size `16384`; integer safe range; schemas |
| 3 | Foundation 57 | Nonce UTF-8 `1..256`; skew `300`; ledger/replay/correlation formulas |
| 4 | Foundation 58 | Request-size-only policy; defers the six limits; no implementation auth |
| 5 | UAII-cited tests proving F56/F57 constants | Conformance evidence only |

### 2.2 Non-authority (MUST NOT be treated as UAII limits)

| Class | Examples | Why non-authority |
|---|---|---|
| Disposable sandbox / lifecycle | `MAX_REQUEST_BYTES` 8192/16384; `MAX_TREE_DEPTH=64`; `MAX_TREE_ENTRIES=4096` | Filesystem tree / sandbox envelopes, not UAII JSON |
| M2M modules | `MAX_TRANSCRIPT_MESSAGES=64`; `MAX_INPUT_BYTES=1048576`; registry file/exchange caps | M2M transcript/registry domains |
| Node-role / wallet evidence | `MAX_PROFILE_BYTES`, `MAX_TRANSCRIPT_BYTES`, `MAX_SCENARIO_BYTES`, etc. | Offline role/wallet artifacts |
| Python / CPython defaults | `sys.getrecursionlimit()`, `json` module practical limits | Incidental runtime behavior |
| Adapter / SDK defaults | None in-repo for UAII | Deferred adapters (F56 §7) |
| Undocumented magic numbers | Any constant not cited by F56/F57/F58 for UAII | Insufficient authority |

### 2.3 Fixed envelope that is **not** a substitute

Foundation 56 / 58 lock:

```
MAX_UAII_REQUEST_BYTES = 16384
```

Foundation 58 §10.2 explicitly states that this bounds received request
allocation but does **not** resolve parser nesting, expansion, or result-size
policy. This audit preserves that rule: `16384` remains exact and MUST NOT be
silently reused as the value for any of the six deferred limits without a
separate, explicit specification decision that cites this audit’s gap.

## 3. Cross-cutting evidence table

| Topic | Path / symbol / section | Bound | Authority class for UAII parser limits |
|---|---|---|---|
| UAII max request bytes | F56 §3.1; F58 §10.1; `coin/disposable_sandbox_lifecycle_integration.py` `MAX_REQUEST_BYTES=16384` (lifecycle only) | `16384` | **Normative for request size only** |
| UAII integer safe range | F56 §3.1 | `-9007199254740991` … `9007199254740991` | Normative for integers; not string/depth |
| UAII nonce string bytes | F57 §8.2 | `1` … `256`; no NUL | Normative for **nonce** strings only |
| UAII hex digests | F56/F57 | exactly 64 lowercase hex | Exact field grammar; not general strings |
| UAII `detail` | F56 §3.4 | MUST be `""` | Emptiness; not max result size |
| Secret scan depth | F56 §6.5 | “any nesting depth” | Qualitative; **no numeric depth** |
| Sandbox request 8192 | F50/F51/F52/F53; `coin/disposable_sandbox_directory_*.py` | `8192` | Non-authority for UAII |
| Lifecycle request 16384 | F54/F55; `coin/disposable_sandbox_lifecycle_integration.py` | `16384` | Same numeric value as UAII request; **different profile** |
| Sandbox tree depth | F52/F53 `MAX_TREE_DEPTH=64` | `64` | Filesystem tree; non-authority for JSON |
| Sandbox tree entries | F52/F53 `MAX_TREE_ENTRIES=4096` | `4096` | Filesystem; non-authority |
| M2M transcript messages | `coin/m2m_transcript_validator.py` `MAX_TRANSCRIPT_MESSAGES=64` | `64` | M2M-only |
| M2M conformance input | `docs/m2m/conformance_cli_v0.1.md` `MAX_INPUT_BYTES=1048576` | `1048576` | M2M CLI; non-authority |
| M2M registry file | `coin/m2m_registry_audit.py` `MAX_REGISTRY_FILE_BYTES=8388608` | `8388608` | M2M-only |
| M2M registry exchanges | `MAX_REGISTRY_EXCHANGES=4096` | `4096` | M2M-only |
| Duplicate-key parsers | Multiple `object_pairs_hook` helpers across `coin/*.py` | Reject duplicates | Behavior pattern; **no depth/member caps** |
| Canonical JSON (M2M) | `coin/m2m_verifier.canonicalize` | Sorted-key canon | M2M authority; not UAII `CanonUaii` size cap |
| Protocol validation | `coin/tx_validation.py` `validate_transaction` | Amount/supply/height rules | Settlement; not JSON parser limits |
| Ledger tip | `coin/ledger.py` `_seen_tx_ids: set[str]` | Unordered set | Confirms F57 no-tip; no parser limits |

## 4. Limit 1 — JSON nesting depth

### 4.1 Supported UAII value

**UNRESOLVED** — no UAII-authoritative finite value.

### 4.2 Evidence

- Foundation 56 §6.5 requires secret-key rejection at **any** nesting depth but
  does not define a maximum depth.
- Foundation 56/57/58 do not declare `MAX_JSON_DEPTH` or equivalent.
- Protocol v1.0.0 does not define UAII JSON nesting.
- `MAX_TREE_DEPTH=64` (`docs/foundation52_*`, `docs/foundation53_*`, sandbox
  cleanup implementation) applies to disposable sandbox **directory trees**,
  not JSON parse depth.
- In-repo JSON parsers (`object_pairs_hook` patterns) enforce duplicate-key and
  non-finite rejection without a depth counter.

### 4.3 Rationale

Borrowing sandbox tree depth `64` would invent UAII authority from an unrelated
domain. CPython recursion limits are incidental and non-normative.

### 4.4 Affected operations

All seven Foundation 56 operations (parse path is shared).

### 4.5 Required boundary tests (after a future approved value `D`)

- Depth `D-1` accepted when otherwise valid
- Depth `D` accepted or rejected per the future lock’s inclusive/exclusive rule
- Depth `D+1` rejected with a stable code authorized by that future lock

### 4.6 Compatibility impact

Until locked, Foundation 58 authorizes **no** UAII reference-core
implementation (§10.3).

### 4.7 Operator / specification decision required

Choose and authorize one of:

1. A finite UAII `MAX_JSON_DEPTH` with rationale and stable reject code; or
2. An explicit policy that nesting is constrained only by request size `16384`
   **and** document how that policy satisfies Foundation 58’s requirement that
   nesting is not left silently unlimited (F58 §10.2 item 4).

## 5. Limit 2 — Object-member count

### 5.1 Supported UAII value

**UNRESOLVED** — no UAII-authoritative finite **parser** maximum for object
member count.

### 5.2 Evidence

- Foundation 56 schemas require **exact** field sets and order (unknown fields
  → `schema_invalid`). That constrains conforming objects to known arities
  (e.g. common request envelope: 8 fields in F56 §3.3) but is **not** a general
  max-members parser bound on arbitrary nested objects such as `service_params`
  / `service_terms` (typed as objects without member-count caps in F56 §5.4).
- No `MAX_OBJECT_MEMBERS` (or equivalent) exists in F56/F57/F58 or Protocol.
- Sandbox `MAX_TREE_ENTRIES=4096` is filesystem-only (non-authority).

### 5.3 Rationale

Exact schema arity ≠ maximum members. Nested free-form objects remain without a
UAII member ceiling in repository authority.

### 5.4 Affected operations

Primarily operations embedding open objects (`create_quote` /
`create_unsigned_payment_request` / `validate_payment` /
`get_payment_receipt` service/terms objects); parse path affects all seven.

### 5.5 Required boundary tests (after future approved value `M`)

`M-1` / `M` / `M+1` member counts on the object class the future lock covers.

### 5.6 Compatibility impact

Implementation remains unauthorized under Foundation 58 until resolved.

### 5.7 Operator / specification decision required

Lock a finite UAII max object-member count (global and/or per named object
types such as `service_params` / `service_terms`), or an explicit
request-size-only expansion policy that still forbids “silently unlimited”
member growth in decoded form, with tests and a stable reject code.

## 6. Limit 3 — Array length

### 6.1 Supported UAII value

**UNRESOLVED** — no UAII-authoritative finite **general** array-length maximum.

### 6.2 Evidence

- Foundation 56 §5.1 `operations` array MUST be the seven operation names in
  §4 order (exact content/length for that success field), not a general max.
- Capability / adapter-declaration arrays are ordered/content-constrained but
  have no numeric `MAX_ARRAY_LENGTH` in F56.
- M2M `MAX_TRANSCRIPT_MESSAGES=64` (`coin/m2m_transcript_validator.py`) is
  M2M-only (non-authority for UAII).
- No UAII `MAX_ARRAY_LENGTH` in F56/F57/F58 or Protocol.

### 6.3 Rationale

Schema-exact arrays are not a substitute for a parser/collection ceiling on
other arrays that may appear in nested objects.

### 6.4 Affected operations

`discover_capabilities` (capability/adapter arrays); any nested arrays in
service objects; shared parse path for all seven operations.

### 6.5 Required boundary tests (after future approved value `A`)

`A-1` / `A` / `A+1` for each array class covered by the future lock.

### 6.6 Compatibility impact

Implementation remains unauthorized under Foundation 58 until resolved.

### 6.7 Operator / specification decision required

Lock finite UAII array-length maxima (global and/or per field), or an explicit
non-silent request-size-only policy with reject semantics and boundary tests.

## 7. Limit 4 — Non-nonce string byte length

### 7.1 Supported UAII value

**UNRESOLVED** for general non-nonce strings.

**Related locked grammars (narrow; not a general string max):**

| String class | Bound | Evidence |
|---|---|---|
| Envelope / quote / payment / receipt **nonces** | UTF-8 bytes `1..256`; no NUL | F57 §8.2 |
| Hex64 ids (`request_id`, `report_id`, `quote_id`, …) | exactly 64 lowercase hex chars | F56/F57 |
| Opaque identities / addresses | non-empty string; optional recognize-only `^L28[0-9a-f]{40}$` | F56 §5.0; F57 §6 |
| `detail` | MUST be `""` | F56 §3.4 |

No UAII maximum UTF-8 byte length is locked for `purpose`, `service_id`,
free-form identity strings beyond non-empty, or other non-nonce text fields.

### 7.2 Evidence

- Foundation 58 §10.3 lists Deferred-string-bytes as deferred because only nonce
  `256` and request `16384` are evidenced.
- Request size `16384` bounds wire allocation but is not authorized as the
  per-string maximum (F58 §10.2).

### 7.3 Rationale

Using `16384` as every string’s max would be a new policy decision, not an
existing lock. Using `256` outside nonce fields would incorrectly extend F57.

### 7.4 Affected operations

All seven (identities, purpose, service fields, capability descriptions, etc.).

### 7.5 Required boundary tests (after future approved value `S`)

For each covered string class: `S-1` / `S` / `S+1` UTF-8 byte lengths (and
preserve nonce `1..256` / hex64 exactness unchanged).

### 7.6 Compatibility impact

Implementation remains unauthorized under Foundation 58 until resolved.

### 7.7 Operator / specification decision required

Lock finite non-nonce string byte maxima by field class (or a single global
cap), without weakening F57 nonce/`hex64` rules, with stable codes and boundary
tests.

## 8. Limit 5 — Canonicalized byte length

### 8.1 Supported UAII value

**UNRESOLVED** — no UAII-authoritative maximum for `CanonUaii(...)` output size.

### 8.2 Evidence

- Foundation 56 §3.2 defines `CanonUaii` rules (`sort_keys=false`, compact
  separators, UTF-8) but no max canonical byte length.
- Foundation 58 §10.2–§10.3 explicitly defer canonicalized bytes and forbid
  treating request size as a substitute for that policy.
- M2M canonicalize (`coin/m2m_verifier.py`) has no UAII canon size cap and is a
  different canonicalization authority.
- Success `report_id` digests canonical request bytes; that does not define a
  maximum length for those bytes beyond what an accepted request implies, and
  F58 forbids silently equating that implication to a locked canon limit.

### 8.3 Rationale

Even if many accepted requests yield `len(CanonUaii(request)) <= 16384`, locking
that equivalence is a **new** specification act. Nested object digests and
future result canonicalization are not covered by request size alone.

### 8.4 Affected operations

All identifier derivation paths (`report_id`, `quote_id`, payment/receipt
digests, F57 `ledger_state_id` / correlation / replay preimages).

### 8.5 Required boundary tests (after future approved value `C`)

`C-1` / `C` / `C+1` canonical UTF-8 byte lengths for each covered object class.

### 8.6 Compatibility impact

Implementation remains unauthorized under Foundation 58 until resolved.

### 8.7 Operator / specification decision required

Lock a finite UAII max canonicalized byte length (and whether it equals,
differs from, or is independent of `16384`), with reject semantics if
canonicalization would exceed the cap.

## 9. Limit 6 — Diagnostic / result byte length

### 9.1 Supported UAII value

**UNRESOLVED** — no UAII-authoritative maximum encoded size for the response
envelope or operation `result` object.

### 9.2 Evidence

- Foundation 56 §3.4: `detail` MUST be `""` on every path (eliminates diagnostic
  text, not result-size bounding).
- Foundation 56 does not lock max response bytes.
- Foundation 58 §10.3 Deferred-result-bytes: deferred; no evidenced max.
- No UAII response size constant exists in Protocol or `coin/` UAII modules
  (none exist).

### 9.3 Rationale

Empty `detail` is not a result-size policy. Success payloads
(`discover_capabilities` capability arrays, quotes, receipts) can grow with
context and nested objects.

### 9.4 Affected operations

All seven (response envelope always); largest risk on
`discover_capabilities` and receipt/quote-bearing successes.

### 9.5 Required boundary tests (after future approved value `R`)

`R-1` / `R` / `R+1` encoded response sizes under the future lock’s measurement
rule (UTF-8 bytes of the exact-order response object).

### 9.6 Compatibility impact

Implementation remains unauthorized under Foundation 58 until resolved.

### 9.7 Operator / specification decision required

Lock a finite max diagnostic/result encoded size (and measurement definition),
preserving `detail=""` and forbidding stack traces / path / secret leakage
(F56/F58).

## 10. Interaction with the fixed 16384-byte request envelope

| Statement | Status |
|---|---|
| Request UTF-8 byte length `> 16384` → `input_too_large` | Locked (F56/F58) |
| Request UTF-8 byte length `<= 16384` may still be invalid | Locked (schema/secret/time/…) |
| `16384` bounds received allocation | Locked (F58 §10.2) |
| `16384` resolves JSON depth | **No** |
| `16384` resolves object-member count | **No** |
| `16384` resolves array length | **No** |
| `16384` resolves non-nonce string maxima | **No** |
| `16384` resolves canonicalized-byte maxima | **No** |
| `16384` resolves result/diagnostic maxima | **No** |

Any future proposal that sets one of the six limits equal to `16384` MUST state
that equality as an explicit new lock with rationale—not as “already implied.”

## 11. Preservation requirements (unchanged)

Future limit-locking foundations MUST preserve:

- L28 Protocol v1.0.0 and `validate_transaction` as sole settlement-validation
  authority
- UAII profile `l28-universal-ai-access-interface/v0.1`
- Maximum request size exactly `16384` bytes
- Exactly seven operations and seven operation-local precedence contracts
- Foundation 56 §3.2 exact-order UAII JSON; M2M Canonical JSON v0.1 for M2M only
- Foundation 57 ten-field `UaiiLedgerStateBinding`, domain/formula set, replay
  contract, `UAII_CLOCK_SKEW_TOLERANCE_SECONDS = 300`, UAII↔M2M correlation,
  and no-tip / no `LEDGER-TIP` / no accepted-ID-set commitment
- `execution_authorized=false`, `spend_authorized=false`,
  `ledger_mutated=false`
- Foundation 58 `get_balance` success treatment (`ok=true`,
  `operation="get_balance"`, `code=""`; no invented success code)
- Protected economics: hard cap `28_000_000`; emission ceiling `11_130_000`;
  historically mined `2_824_584`; treasury locked `500_000`; circulating
  snapshot `2_324_584`
- Foundation 55 disposable sandbox lifecycle evidence and historical continuity
  artifacts

## 12. Boundary-test mandate for later approved values

For **every** numeric value later approved for any of the six limits, future
implementation foundations MUST prove:

1. boundary-minus-one behavior;
2. boundary behavior;
3. boundary-plus-one rejection (or acceptance, if the lock’s inclusivity so
   states—must be explicit);

using stable codes only, with no adapter-specific substitution.

## 13. Non-authorization statement

**Foundation 59 does not authorize implementation** of a UAII reference core,
adapters, signers, wallets, replay stores, settlement, networks, services, or
runtime activation.

Foundation 58’s gate remains in force: no UAII reference-core implementation is
authorized until the six deferred finite limits receive separate specification
approval with evidenced justifications and boundary tests.

This audit invents **no** unsupported numeric values.

## 14. Unresolved decisions checklist (operator)

| ID | Limit | Required decision |
|---|---|---|
| F59-D1 | JSON nesting depth | Finite UAII depth **or** explicit non-silent size-only nesting policy |
| F59-D2 | Object-member count | Finite UAII member max (global/per-object) **or** explicit non-silent policy |
| F59-D3 | Array length | Finite UAII array max (global/per-field) **or** explicit non-silent policy |
| F59-D4 | Non-nonce string bytes | Finite maxima by string class; preserve nonce `256` and hex64 |
| F59-D5 | Canonicalized bytes | Finite `CanonUaii` output max; define relation to `16384` explicitly |
| F59-D6 | Result / diagnostic bytes | Finite encoded response max; keep `detail=""` |

All six: **UNRESOLVED** under current repository evidence.

## 15. Audit conclusion

| Deferred prerequisite (F58) | UAII-supported finite value | Status |
|---|---|---|
| Deferred-JSON-depth | None | UNRESOLVED |
| Deferred-object-members | None | UNRESOLVED |
| Deferred-array-length | None | UNRESOLVED |
| Deferred-string-bytes | None (nonce/`hex64` only as narrow grammars) | UNRESOLVED |
| Deferred-canon-bytes | None | UNRESOLVED |
| Deferred-result-bytes | None | UNRESOLVED |

**Recommended next step:** A separately authorized specification foundation that
locks finite values (or explicit non-silent policies) for F59-D1…F59-D6, citing
this audit, without amending Protocol or Foundations 55–58 text in-place.

---

**End of Foundation 59 UAII Finite Resource-Limit Evidence Audit v0.1**
