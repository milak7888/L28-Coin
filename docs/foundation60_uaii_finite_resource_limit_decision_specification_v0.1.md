# Foundation 60 UAII Finite Resource-Limit Decision Specification v0.1

**Status:** Specification / decision only (documentation; non-activation;
non-implementation)

**Decision profile:** `l28-uaii-finite-resource-limit-decision/v0.1`

**Parent contracts:**

- Foundation 59 — finite resource-limit evidence audit
  (`docs/foundation59_uaii_finite_resource_limit_evidence_audit_v0.1.md`)
- Foundation 58 — UAII reference-core implementation specification
- Foundation 57 — UAII reference-core contracts
- Foundation 56 — Universal AI Access Interface

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Base commit:** `93ed7f742f93cfd82edadcd015f78ae14c4820c6`

**Branch:** `foundation60-uaii-finite-resource-limit-decision-specification`

**Normative subordination:** On conflict, Protocol v1.0.0 prevails; then
Foundation 56; then Foundation 57; then Foundation 58; then Foundation 59’s
authority/non-authority distinction; then this decision specification.

## 1. Purpose and non-inference statement

Foundation 59 established that repository evidence cannot support UAII values
for F59-D1…F59-D6 and left them **UNRESOLVED**. Foundation 58 gated
implementation on separate finite-limit approval with boundary tests.

This foundation proposes an explicit **candidate UAII policy profile** that
resolves F59-D1…F59-D6 as **new UAII policy selections**.

These numeric values are **not**:

- inferred from Foundation 59 (which found no UAII-supported values);
- borrowed from incidental sandbox, M2M, node-role, wallet, lifecycle, Python,
  or adapter constants;
- implied solely by the fixed `16384`-byte request envelope.

They are operator-facing security-bounded proposals requiring separate
acceptance, commit, main integration, and a later implementation authorization
before any UAII reference-core code may be written.

### 1.1 Authority flags (mandatory)

Every path described by this decision profile remains:

| Flag | Value |
|---|---|
| `execution_authorized` | `false` |
| `implementation_authorized` | `false` |
| `spend_authorized` | `false` |
| `ledger_mutated` | `false` |

Foundation 60 does **not** open Foundation 58’s implementation gate by itself.
`implementation_authorized=false` until a later foundation explicitly sets
implementation authorization after this decision profile is accepted and
integrated.

## 2. Candidate limit profile (inclusive)

| ID | Resolves | Limit name | Value | Inclusive? |
|---|---|---|---|---|
| F60-L1 | F59-D1 | Maximum JSON nesting depth | `32` | Yes — depth `<= 32` accepted; depth `33` rejected |
| F60-L2 | F59-D2 | Maximum members in any object | `256` | Yes — `<= 256` accepted; `257` rejected |
| F60-L3 | F59-D3 | Maximum elements in any array | `256` | Yes — `<= 256` accepted; `257` rejected |
| F60-L4 | F59-D4 | Maximum UTF-8 bytes in any non-nonce string | `4096` | Yes — `<= 4096` accepted; `4097` rejected |
| F60-L5 | F59-D5 | Maximum canonicalized **request** bytes | `16384` | Yes — `<= 16384` accepted; `16385` rejected |
| F60-L6 | F59-D6 | Maximum serialized result / diagnostic bytes | `16384` | Yes — `<= 16384` accepted; `16385` rejected |

### 2.1 Preserved narrower locks (unchanged)

| Lock | Value | Authority |
|---|---|---|
| Maximum received request size | exactly `16384` UTF-8 bytes | F56 / F58 |
| Nonce UTF-8 byte length | `1` … `256`; NUL forbidden | F57 §8.2 |
| Hex64 identifiers | exactly 64 lowercase hex | F56 / F57 |
| `detail` | MUST be `""` | F56 §3.4 |
| Integer safe range | `-9007199254740991` … `9007199254740991` | F56 §3.1 |

Nonce strings remain under F57 `1..256` and MUST NOT be widened to `4096`.
Hex64 and other exact grammars remain exact.

## 3. Rationale per limit

### 3.1 F60-L1 depth `32`

- **Security:** Bounds decoder stack / recursive walk cost; prevents
  deeply nested expansion attacks within a `16384`-byte wire envelope.
- **Interoperability:** Depth `32` is a conservative cross-language JSON
  walk budget that still admits legitimate nested `service_params` /
  `service_terms` objects under UAII schemas.
- **Determinism:** Fixed integer; first-failure depth check is order-stable
  under §5 traversal.
- **Compatibility:** Does not alter F56 field schemas; only rejects
  pathological nesting. Not derived from sandbox `MAX_TREE_DEPTH=64`.

### 3.2 F60-L2 object members `256`

- **Security:** Caps per-object key cardinality to limit hash-map blowups and
  secret-scan work.
- **Interoperability:** Far above exact UAII envelope/params arities; leaves
  headroom for nested maps without matching incidental `4096` tree-entry caps.
- **Determinism:** Counted per object independently.
- **Compatibility:** Unknown fields remain `schema_invalid` under F56; this
  limit is an additional structural ceiling.

### 3.3 F60-L3 array elements `256`

- **Security:** Caps array walk and allocation fan-out.
- **Interoperability:** Above the seven-name `operations` array and typical
  capability lists; not borrowed from M2M transcript `64`.
- **Determinism:** Per-array count.
- **Compatibility:** Schema-exact arrays (e.g. seven operations) remain
  content-constrained by F56 in addition to this ceiling.

### 3.4 F60-L4 non-nonce strings `4096`

- **Security:** Bounds decoded string retention and Unicode handling cost;
  closes “single huge string inside 16384 wire bytes” expansion via escapes
  only insofar as decoded UTF-8 bytes are capped (escaped wire forms still
  limited by request size).
- **Interoperability:** Large enough for purpose/service text; must not weaken
  nonce `1..256` or hex64.
- **Determinism:** Measured as UTF-8 byte length of the JSON-decoded string
  value (§4.4).
- **Compatibility:** Opaque identities remain non-empty strings under F56/F57
  with this additional max.

### 3.5 F60-L5 canonicalized request bytes `16384`

- **Security:** Prevents accepting a wire-legal request whose exact-order
  canonical form grows beyond a fixed digest preimage budget.
- **Interoperability:** Explicitly **equal** to the received-request maximum as
  a **new policy lock**, not an implied identity (Foundation 59 forbade silent
  implication).
- **Determinism:** Uses Foundation 56 §3.2 `CanonUaii` of the accepted request
  envelope object.
- **Compatibility:** Compact requests that canonicalize within `16384` remain
  valid; pathological reorder/spacing differences are irrelevant because
  measurement is on `CanonUaii`, not wire spacing.

### 3.6 F60-L6 result / diagnostic bytes `16384`

- **Security:** Bounds response emission; prevents oversized capability dumps
  or error-construction blowups from becoming an output channel.
- **Interoperability:** Matches request budget for adapter framing symmetry as
  a new policy choice.
- **Determinism:** Measured on the full exact-order serialized response
  envelope (§4.6); `detail` remains `""`.
- **Compatibility:** Typical success envelopes fit; oversized success
  payloads fail closed rather than truncate fields silently.

## 4. Precise counting rules

### 4.1 JSON nesting depth (F60-L1)

1. The top-level JSON value (MUST be an object under F56) has depth `1`.
2. Entering a nested JSON object or array increases depth by `1` relative to
   its parent container.
3. Primitives (string, number, boolean, null) do not increase depth beyond
   their containing value’s depth.
4. Maximum depth among all containers in the request tree MUST be `<= 32`.
5. Depth is evaluated on the decoded JSON value tree after successful parse
   (and duplicate-key rejection), not on textual indentation.

### 4.2 Object members (F60-L2)

1. For every JSON object in the request tree, `member_count` is the number of
   property names in that object.
2. Each object is evaluated independently.
3. Every object MUST satisfy `member_count <= 256`.
4. Duplicate keys are still rejected first as `duplicate_key` (F56); they are
   not counted as two members.

### 4.3 Array elements (F60-L3)

1. For every JSON array in the request tree, `element_count` is the number of
   elements in that array.
2. Each array is evaluated independently.
3. Every array MUST satisfy `element_count <= 256`.

### 4.4 Non-nonce string UTF-8 bytes (F60-L4)

1. For every JSON string value in the request tree, let `B` be the UTF-8 byte
   length of the **decoded** string content (after JSON escape processing).
2. Multibyte UTF-8 characters count by their UTF-8 byte length (e.g. one
   U+1F600 code point may be 4 bytes).
3. If the string is an envelope/object **nonce** field governed by Foundation
   57 (`nonce`, `quote_nonce`, `payment_nonce`, `receipt_nonce` as applicable),
   apply F57 `1 <= B <= 256` and NUL prohibition — **not** F60-L4.
4. For all other strings, require `B <= 4096`.
5. Exact grammars (hex64, optional `l28_hex40` recognition) remain additional
   constraints and are not relaxed by F60-L4.

### 4.5 Canonicalized request bytes (F60-L5)

1. After the request envelope object is fully accepted through Outer steps
   that establish typed structure for canonicalization, compute
   `CanonUaii(request_envelope)` per Foundation 56 §3.2
   (`sort_keys=false`; separators `(",", ":")`; `ensure_ascii=false`;
   `allow_nan=false`; UTF-8).
2. Let `C = len(CanonUaii(request_envelope))` in UTF-8 bytes.
3. Require `C <= 16384`.
4. This measurement is independent of wire spacing; it is not a substitute for
   received-size enforcement at Outer 1.

### 4.6 Serialized result / diagnostic bytes (F60-L6)

1. Let `R` be the UTF-8 bytes of the exact-order Foundation 56 §3.4 response
   envelope object serialized with the same UAII compact rules as `CanonUaii`
   (`sort_keys=false`; separators `(",", ":")`; `ensure_ascii=false`;
   `allow_nan=false`).
2. Require `R <= 16384` for every returned response, success or failure.
3. `detail` MUST remain `""`. Implementations MUST NOT enlarge `detail` to
   carry truncation reasons, stack traces, paths, secrets, or environment data.
4. If constructing a conforming success envelope would exceed `16384`, the
   core MUST fail closed with §6 mapping rather than silently omitting fields.

## 5. Deterministic structural walk (for L1–L4)

When applying F60-L1…F60-L4 after Outer 3 parse success:

1. Walk the decoded JSON tree depth-first, visiting object members in the
   **exact serialized field order** retained from parse (UAII order; no key
   sort).
2. Array elements are visited in ascending index order.
3. At each container entry, enforce F60-L1 (depth).
4. When an object’s full member set is known, enforce F60-L2.
5. When an array’s full element set is known, enforce F60-L3.
6. When a string value is visited, enforce F60-L4 or F57 nonce rules as
   applicable.
7. Stop at the **first** violation (first-failure).

Duplicate-key rejection remains part of Outer 3 and precedes this walk.

## 6. Enforcement placement in Foundation 58’s 17-step pipeline

Foundation 58 §6.1 outer sequence is preserved. Limit checks insert as follows
without reordering existing F56/F57/F58 precedence among non-limit failures:

| Pipeline stage | Limit checks |
|---|---|
| Outer 1 — type + received size `16384` | Unchanged (`input_too_large`) |
| Outer 2 — UTF-8 | Unchanged |
| Outer 3 — JSON parse + duplicate-key + top-level object | Unchanged; must succeed before L1–L4 |
| **Post-Outer-3 / pre-Outer-4 structural limits** | **F60-L1, F60-L2, F60-L3, F60-L4** via §5 walk |
| Outer 4 — secret-material rejection | Unchanged (still earliest secret point) |
| Outer 5–8 | Unchanged |
| Outer 9–10 — canonicalization / identifier readiness | **F60-L5** on `CanonUaii(request_envelope)` before success `report_id` emission |
| Outer 11–16 | Unchanged (operation-local lists retain relative order) |
| Outer 17 — stable result construction | **F60-L6** on serialized response envelope |

If Outer 3 fails, L1–L4 are not evaluated. If L1–L4 fail, later stages including
secrets are not required to run (first-failure). Secret rejection remains before
profile/operation acceptance when L1–L4 pass.

## 7. Error mapping (failure codes only)

### 7.1 New stable failure code (this decision profile)

| Code | Meaning |
|---|---|
| `resource_limit_exceeded` | A Foundation 60 inclusive resource limit was violated |

This is a **failure** code only. It is not a success code. It MUST NOT be used
to invent `get_balance` success tokens or alter Foundation 58 §8.2.1.

### 7.2 Mapping

| Violation | Code | Notes |
|---|---|---|
| Received request `> 16384` | `input_too_large` | Existing F56 (not F60-L5/L6) |
| Invalid UTF-8 / malformed JSON / non-finite / duplicate key / non-object top-level | Existing F56 codes | Unchanged |
| F60-L1 / L2 / L3 / L4 | `resource_limit_exceeded` | After Outer 3; `detail=""` |
| F60-L5 | `resource_limit_exceeded` | After canon bytes computed; `detail=""`; `report_id=""` |
| F60-L6 | `resource_limit_exceeded` | Fail-closed minimal envelope (§7.3) |
| All other failures | Existing F56/F57/F58 codes | Precedence unchanged |

Adapters MUST NOT substitute codes.

### 7.3 Oversized result fail-closed envelope

When F60-L6 would be exceeded, return exactly the Foundation 56 §3.4 field
order with:

1. `ok` = `false`
2. `code` = `resource_limit_exceeded`
3. `interface_profile` / `operation` / `request_id` per F56 recovery rules when
   safely known; else `""`
4. `result` = `{}`
5. `execution_authorized` = `false`
6. `report_id` = `""`
7. `detail` = `""`

That failure envelope itself MUST satisfy F60-L6 (`<= 16384`). It MUST NOT
embed secrets, paths, stack traces, or partial oversized payloads.

## 8. Edge cases

| Case | Rule |
|---|---|
| Multibyte UTF-8 in strings | Count decoded UTF-8 bytes (F60-L4) |
| JSON escaped sequences (`\uXXXX`, `\\`, `\"`) | Decoded length counts; wire escapes still bounded by received `16384` |
| Duplicate keys | `duplicate_key` before L1–L4 |
| Deeply mixed objects/arrays | Depth counts every nested object/array; members/elements counted per container |
| Canonical expansion vs wire | F60-L5 measures `CanonUaii` only; Outer 1 still enforces received size |
| Oversized error/detail temptation | Forbidden; `detail` stays `""`; use §7.3 |
| Nonce strings | F57 `1..256` only; never F60-L4 `4096` |
| Empty `detail` on all paths | Preserved |

## 9. Mandatory boundary tests (future implementation foundations)

For each of F60-L1…F60-L6, future tests MUST prove:

1. **boundary-minus-one** accepted when otherwise valid;
2. **boundary** accepted (inclusive);
3. **boundary-plus-one** rejected with `resource_limit_exceeded` (or
   `input_too_large` only for received-size Outer 1, which remains distinct).

Additional required vectors:

- Multibyte string at `4095` / `4096` / `4097` decoded UTF-8 bytes
- Nested object/array mix reaching depth `31` / `32` / `33`
- Object with `255` / `256` / `257` members
- Array with `255` / `256` / `257` elements
- Canonical request size `16383` / `16384` / `16385`
- Result envelope size `16383` / `16384` / `16385` (synthetic oversized success
  construction must fail closed per §7.3)
- Nonce still rejects `0` and `257` bytes under F57 (`nonce_invalid`), not
  `resource_limit_exceeded`
- Received request `16385` still `input_too_large` (unchanged)

## 10. Preservation

This decision profile MUST preserve:

- Exactly seven Foundation 56 operations and names
- Exact-order UAII JSON; M2M Canonical JSON v0.1 for M2M only
- Field order and operation-local precedence contracts
- Foundation 57 ten-field `UaiiLedgerStateBinding`, domain/formula set, replay
  contract, `UAII_CLOCK_SKEW_TOLERANCE_SECONDS = 300`, UAII↔M2M correlation,
  and no-tip / no `LEDGER-TIP` / no accepted-ID-set commitment
- `validate_transaction` as sole settlement-validation authority
- Foundation 58 `get_balance` success treatment (`ok=true`,
  `operation="get_balance"`, `code=""`)
- Protected economics: `28_000_000` / `11_130_000` / `2_824_584` / treasury
  `500_000` / circulating `2_324_584`
- Historical and Foundation 55 evidence artifacts

## 11. Separate authorization requirements

Publication of this document is **not** permission to implement. Required later
authorizations (each separate):

1. Acceptance review of this decision profile
2. Commit on the feature branch
3. Fast-forward integration to `main` and push
4. Explicit implementation authorization foundation (may set
   `implementation_authorized` for coding only under these locked limits)

Until step 4, `implementation_authorized=false` and Foundation 58’s “no UAII
reference-core implementation” gate remains closed.

## 12. Explicit exclusions

Out of scope:

- Core implementation, tests that execute a UAII core, scaffolds
- MCP / REST / Python / TypeScript adapters
- Signing, wallets, settlement execution, replay mutation
- Networking, services, testnets, production activation
- Leap28 / Nova
- Amending Foundations 55–59 or Protocol text in this change set

## 13. Decision summary

| F59 ID | F60 ID | Proposed inclusive value | Status in this draft |
|---|---|---|---|
| F59-D1 | F60-L1 | Depth `32` | Proposed policy selection |
| F59-D2 | F60-L2 | Object members `256` | Proposed policy selection |
| F59-D3 | F60-L3 | Array elements `256` | Proposed policy selection |
| F59-D4 | F60-L4 | Non-nonce string UTF-8 bytes `4096` | Proposed policy selection |
| F59-D5 | F60-L5 | `CanonUaii(request)` bytes `16384` | Proposed policy selection |
| F59-D6 | F60-L6 | Serialized response bytes `16384` | Proposed policy selection |

Failure code for F60-L1…L6 violations: `resource_limit_exceeded` (with
`detail=""`).

---

**End of Foundation 60 UAII Finite Resource-Limit Decision Specification v0.1**
