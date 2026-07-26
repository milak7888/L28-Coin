# Foundation 62 UAII Resource-Limit Implementation Specification v0.1

**Status:** Implementation specification only (documentation; non-activation;
non-implementation; non-authorization)

**Specification profile:** `l28-uaii-resource-limit-implementation/v0.1`

**Parent contracts:**

- Foundation 61 — resource-limit implementation readiness audit
  (`docs/foundation61_uaii_resource_limit_implementation_readiness_audit_v0.1.md`)
- Foundation 60 — finite resource-limit decision specification
  (`docs/foundation60_uaii_finite_resource_limit_decision_specification_v0.1.md`)
- Foundation 58 — UAII reference-core implementation specification
- Foundation 57 — UAII reference-core contracts
- Foundation 56 — Universal AI Access Interface
- Foundation 55 — disposable sandbox lifecycle integration (evidence lock)

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Base commit:** `f6ff9114f2891cdd8f2ff783e9ca3f3ca32983e8`

**Branch:** `foundation62-uaii-resource-limit-implementation-specification`

**Normative subordination:** On conflict, Protocol v1.0.0 prevails; then
Foundation 56; then Foundation 57; then Foundation 58; then Foundation 60 for
inclusive limits and codes; then Foundation 61’s readiness/GAP inventory; then
this implementation specification. This document MUST NOT invent new limit
values, amend Foundations 55–61, or authorize coding.

## 1. Authority and scope

### 1.1 Purpose

This document defines the **exact deterministic implementation contract** for
enforcing Foundation 60’s accepted inclusive limits inside the Foundation 58
reference-core pipeline, using Foundation 61’s accepted readiness audit as the
GAP inventory to close at specification level.

**This document specifies implementation. It does not authorize
implementation.**

### 1.2 Mandatory flags (unchanged)

| Flag | Value |
|---|---|
| `execution_authorized` | `false` |
| `implementation_authorized` | `false` |
| `spend_authorized` | `false` |
| `ledger_mutated` | `false` |

`READY_FOR_SEPARATE_IMPLEMENTATION_AUTHORIZATION` (§12) is **not** coding
permission. A later foundation MUST explicitly set
`implementation_authorized` before any listed implementation step begins.

### 1.3 Normative prerequisites

Foundations **55–61** are normative prerequisites and remain unchanged by this
foundation. In particular:

| Prerequisite | Preservation requirement |
|---|---|
| F56 | Exactly seven UAII operations; 16384 received-request envelope; exact-order serialization; response field order §3.4; `detail=""` |
| F57 | Ten-field `UaiiLedgerStateBinding`; domain/formula set; replay contract; `UAII_CLOCK_SKEW_TOLERANCE_SECONDS = 300`; UAII↔M2M correlation; no-tip / no `LEDGER-TIP` / no accepted-ID-set commitment |
| F58 | `process_uaii_request` pipeline; Outer 1–17; `validate_transaction` sole settlement-validation authority; `get_balance` success = `ok=true`, `operation="get_balance"`, `code=""` |
| F60 | Inclusive limits L1–L6; `resource_limit_exceeded`; L6 §7.3 fail-closed fallback |
| F61 | Greenfield GAPs only; zero BLOCKERs; verdict readiness for separate authorization |

### 1.4 Frozen economics and evidence (unchanged)

| Fact | Value | Evidence |
|---|---|---|
| Hard cap | `28_000_000` | `PROTOCOL.md`, `coin/tx_validation.py` |
| Emission ceiling | `11_130_000` | same |
| Historically mined | `2_824_584` | `tx_validation.L28_HISTORICAL_MINED` |
| Treasury locked | `500_000` | `docs/m2m/protocol_v0.1.md` §2 |
| Circulating snapshot | `2_324_584` | same |
| Ledger accepted-ID set | unordered `set[str]` cardinality only | `coin/ledger.py` `_seen_tx_ids` |

Historical evidence, Foundation 55 artifacts, addresses, hashes, and snapshots
remain frozen. This foundation MUST NOT alter them.

### 1.5 Explicit non-goals

- No code, tests, scaffolds, or dependencies are created by this foundation.
- No adapters, signers, wallets, settlement, replay mutation, networking,
  services, testnets, or runtime activation.
- No Leap28 / Nova.
- No alternate validation authority and no tip authority.

## 2. Exact module and symbol plan

### 2.1 Current repository evidence (must not invent hooks)

As audited by Foundation 61 §2:

| Target | In-repo today |
|---|---|
| `coin/uaii*.py` | **Absent** |
| `process_uaii_request` | **Absent** (docs only) |
| `CanonUaii` implementation | **Absent** (pseudocode in F57/F58 only) |
| Structural limit walker | **Absent** |
| UAII result builder / L6 | **Absent** |
| `tests/test_*uaii*` | **Absent** |

### 2.2 Reusable non-authoritative patterns (references only)

These existing symbols are **pattern evidence only**. They MUST NOT become UAII
authorities and MUST NOT be called as `CanonUaii`:

| Pattern | Path / symbol | Allowed use in a later impl |
|---|---|---|
| Size + UTF-8 + duplicate-key parse | `coin/disposable_sandbox_lifecycle_integration.py` (`_decode`, `_parse`, `MAX_REQUEST_BYTES=16384`, `object_pairs_hook=_pairs_no_duplicates`) | Technique reference for Outer 1–3 |
| Duplicate-key pairs hooks | Multiple `coin/*.py` (`_pairs_no_duplicates` / `_unique_object`) | Technique reference |
| M2M sorted canonicalize | `coin/m2m_verifier.canonicalize` / `canonical_bytes` | **Forbidden** for UAII objects |
| Protocol validation | `coin/tx_validation.validate_transaction` | Outer 15 delegate only |
| Ledger cardinality | `coin/ledger.BlocklessLedger._seen_tx_ids` | F57 binding input only |
| Opaque address recognize | `coin/peer_handshake_identity_binding.py` `ADDRESS_RE` | F57 recognize-only |

### 2.3 Planned cohesive UAII path (future; not created here)

One cohesive UAII implementation path. **No duplicate authorities.**

| Future path | Exact responsibility | Planned symbols |
|---|---|---|
| `coin/uaii_reference_core.py` | Sole public entry; Outer 1–17 orchestration; integrates limit stages; maps failures to stable codes | `process_uaii_request(request_bytes, context) -> dict` |
| `coin/uaii_json.py` | Duplicate-key-rejecting decode; UAII exact-order canonicalize; response serialization with identical compact rules | `decode_uaii_json`, `canon_uaii`, `serialize_uaii_response` |
| `coin/uaii_resource_limits.py` | Limit constants; iterative structural walker; L1–L4 / L5 / L6 checks; bounded fallback envelope builder | `F60_L1_MAX_DEPTH`, `F60_L2_MAX_OBJECT_MEMBERS`, `F60_L3_MAX_ARRAY_ELEMENTS`, `F60_L4_MAX_STRING_UTF8_BYTES`, `F60_L5_MAX_CANON_REQUEST_BYTES`, `F60_L6_MAX_SERIALIZED_RESPONSE_BYTES`, `MAX_RECEIVED_REQUEST_BYTES`, `walk_enforce_l1_l4`, `enforce_l5_canon_bytes`, `enforce_l6_response_bytes`, `build_l6_fallback_envelope` |
| `tests/test_uaii_resource_limits.py` | Focused boundary±1 and cross-cutting limit vectors (§10) | unittest module |
| `tests/test_uaii_reference_core.py` | Pipeline / seven-ops / F57 / `validate_transaction` regressions when core exists | unittest module |

Optional internal helpers MAY live as private functions inside those modules.
Additional packages, parallel entry points, or a second canonicalize path are
**forbidden**.

### 2.4 Authoritative entry point

```
process_uaii_request(request_bytes, context) -> result_envelope
```

| Item | Contract |
|---|---|
| Authority | Sole transport-neutral UAII request processor (F58 §4) |
| Inputs | `request_bytes`: `bytes` or `str` UTF-8 text; `context`: F58 §5 read-only interfaces |
| Output | Foundation 56 §3.4 response envelope object (dict), never a raised secret |
| Alternate APIs | **Forbidden** |

### 2.5 UAII canonicalization symbol (mandatory distinction)

| Symbol | Module | Rules |
|---|---|---|
| `canon_uaii(obj) -> bytes` | `coin/uaii_json.py` | Foundation 56 §3.2 / F58 §7.2: exact retained field order; `sort_keys=false`; separators `(",", ":")`; `ensure_ascii=false`; `allow_nan=false`; UTF-8 bytes |

**Prohibition:** Implementations MUST NOT substitute
`coin.m2m_verifier.canonicalize`, `canonical_bytes`, or any
`sort_keys=True` / key-sorting codec for UAII request, binding, replay,
correlation, or response objects.

Documentation alias: `CanonUaii` (Foundations 56–60) ≡ planned `canon_uaii`.

### 2.6 Structural walker, serializer, error mapper, fallback

| Responsibility | Planned symbol / locus | Notes |
|---|---|---|
| Structural-limit walker | `walk_enforce_l1_l4(root) -> None | LimitFailure` | Iterative DFS; §4 |
| Response serializer | `serialize_uaii_response(envelope) -> bytes` | Same compact rules as `canon_uaii` |
| Error mapper | inside `process_uaii_request` / shared mapper | F60 §7 + F56/F57/F58 codes; no adapter substitution |
| Bounded fallback | `build_l6_fallback_envelope(...)` | F60 §7.3; §7 of this doc |

## 3. Exact inclusive limits (unmodified)

| ID | Constant name | Inclusive value | Reject at |
|---|---|---|---|
| F60-L1 | `F60_L1_MAX_DEPTH` | `32` | depth `33` |
| F60-L2 | `F60_L2_MAX_OBJECT_MEMBERS` | `256` | members `257` |
| F60-L3 | `F60_L3_MAX_ARRAY_ELEMENTS` | `256` | elements `257` |
| F60-L4 | `F60_L4_MAX_STRING_UTF8_BYTES` | `4096` | decoded UTF-8 bytes `4097` (non-nonce) |
| F60-L5 | `F60_L5_MAX_CANON_REQUEST_BYTES` | `16384` | `canon_uaii` length `16385` |
| F60-L6 | `F60_L6_MAX_SERIALIZED_RESPONSE_BYTES` | `16384` | serialized response `16385` |

Preserved alongside (not replaced by L1–L6):

| Lock | Value | Authority |
|---|---|---|
| Maximum received request | exactly `16384` UTF-8 bytes | F56 / F58 Outer 1 → `input_too_large` |
| Nonce UTF-8 bytes | `1` … `256`; NUL forbidden | F57 §8.2 → `nonce_invalid` |
| Hex64 identifiers | exactly 64 lowercase hex | F56 / F57 |
| `detail` | MUST be `""` | F56 §3.4 |
| JSON integer safe range | `-9007199254740991` … `9007199254740991` | F56 §3.1 |

**Narrower field grammars remain authoritative** and are never widened by
F60-L4.

## 4. Counting algorithms

All L1–L4 counting runs on the **decoded JSON value tree** after Outer 3
success (UTF-8 decode + JSON parse + duplicate-key rejection + top-level
object). Counting MUST be integer-safe, deterministic, and performed by an
**iterative** depth-first traversal (explicit stack). Unbounded call-stack
recursion is forbidden as the normative algorithm (depth cap `32` does not
license an ambiguous recursive design).

### 4.1 Root-depth convention (F60-L1)

1. The top-level JSON value (MUST be an object under F56) has depth **`1`**.
2. Entering a nested JSON **object** or **array** increases depth by **`1`**
   relative to its parent container.
3. Primitives (string, number, boolean, null) do **not** increase depth beyond
   their containing value’s depth.
4. **Empty containers contribute depth:** `{}` and `[]` are containers at their
   depth. Example: `{"a":{}}` — root depth `1`, inner object depth `2`.
5. Let `D` be the maximum depth among all containers in the tree. Require
   `D <= 32`. Depth `33` → `resource_limit_exceeded`.
6. Depth is independent of textual indentation and of key lexicographic order.

### 4.2 Object-member counting (F60-L2)

1. After duplicate-key rejection, each object’s `member_count` equals the number
   of distinct property names retained from parse order.
2. Duplicate keys never contribute two members: Outer 3 already failed with
   `duplicate_key`.
3. Empty objects have `member_count = 0` (accepted under L2).
4. Every object independently MUST satisfy `member_count <= 256`.

### 4.3 Array-element counting (F60-L3)

1. For every array, `element_count` is the number of elements.
2. Empty arrays have `element_count = 0` (accepted under L3).
3. Every array independently MUST satisfy `element_count <= 256`.

### 4.4 Decoded-string UTF-8 bytes (F60-L4)

1. For a JSON string value, let `S` be the **decoded** Unicode string after JSON
   escape processing (`\uXXXX`, `\\`, `\"`, etc. already applied by the
   decoder).
2. Let `B = len(UTF-8 bytes of S)` using strict UTF-8 encoding of `S`.
3. Multibyte characters count by UTF-8 byte length (e.g. one U+1F600 code point
   is 4 bytes).
4. Escapes affect wire size (Outer 1) but L4 measures **decoded** bytes only.
5. **Nonce carve-out (by property name at visit time):** if the string is the
   immediate value of a property named exactly `nonce`, `quote_nonce`,
   `payment_nonce`, or `receipt_nonce`, **do not apply F60-L4**. Instead apply
   F57: require `1 <= B <= 256` and forbid U+0000; violations → `nonce_invalid`
   (not `resource_limit_exceeded`). Narrower Outer 8 grammar checks remain.
6. For all other strings, require `B <= 4096`; else `resource_limit_exceeded`.
7. Hex64 and other exact grammars remain additional later constraints.

### 4.5 Surrogates, invalid Unicode, and non-JSON domain

| Condition | Behavior | Code |
|---|---|---|
| Malformed JSON / non-finite number / `NaN` / `Infinity` / float | Fail at Outer 3; L1–L4 not evaluated | Existing F56 (`json_invalid`, etc.) |
| Duplicate keys | Fail at Outer 3 | `duplicate_key` |
| Non-object top-level | Fail at Outer 3 | `invalid_top_level` |
| Invalid UTF-8 in `request_bytes` | Fail at Outer 2 | `encoding_invalid` |
| Decoded string cannot strict-UTF-8-encode (e.g. lone surrogates) | Fail closed before accepting L4 pass; treat as encoding/JSON domain failure | Existing F56 `encoding_invalid` or `json_invalid` — **not** `resource_limit_exceeded` |
| Values outside accepted JSON domain after parse | Fail under existing F56 codes | Unchanged |

### 4.6 Deterministic walk order (L1–L4)

Normative algorithm `walk_enforce_l1_l4(root)`:

1. Initialize an explicit stack with `(root, depth=1)`.
2. While stack non-empty, pop one node (DFS; push children so that **earlier
   parse-order members / lower indices are visited first** — UAII order; **no
   key sort**).
3. On entering a container at depth `d`: if `d > 32` → fail L1.
4. If object: let `n = member_count`; if `n > 256` → fail L2; then push each
   member value with depth `d+1` in retained parse order.
5. If array: let `n = element_count`; if `n > 256` → fail L3; then push each
   element with depth `d+1` in ascending index order.
6. If string: apply §4.4 (L4 or nonce rule).
7. Other primitives: no L1–L4 action beyond container depth already charged to
   the parent.
8. **First-failure:** stop at the first violation; do not continue the walk.

### 4.7 L5 measurement (canonical request bytes)

1. After Outer stages that establish a typed request envelope object eligible
   for identifier canonicalization (F58 Outer 9–10; F60 §4.5), compute
   `C = len(canon_uaii(request_envelope))`.
2. Require `C <= 16384`; else `resource_limit_exceeded` with `report_id=""`,
   `detail=""`.
3. L5 is independent of wire spacing; Outer 1 remains a separate received-size
   gate.

### 4.8 L6 measurement (serialized response bytes)

1. Let `R = len(serialize_uaii_response(response_envelope))` where serialization
   uses the same compact UAII rules as `canon_uaii`.
2. Measurement covers the **complete** Foundation 56 §3.4 envelope, success or
   failure.
3. Require `R <= 16384`; else apply §7 bounded fallback (never silent field
   omission).

## 5. Foundation 58 pipeline integration

### 5.1 Placement map

| Stage | Enforcement | Short-circuit on failure |
|---|---|---|
| Outer 1 — type + received size | `len(utf8_bytes) > 16384` → `input_too_large` (**not** L5/L6) | Stop; no JSON decode |
| Outer 2 — UTF-8 | `encoding_invalid` | Stop |
| Outer 3 — JSON + duplicate-key + top-level object | Existing F56 codes | Stop; **L1–L4 not evaluated** |
| **Post-Outer-3 / pre-Outer-4** | `walk_enforce_l1_l4` → L1–L4 / nonce-at-walk | Stop; Outer 4–17 not required |
| Outer 4 — secret-material | `secret_material_forbidden` | Stop |
| Outer 5–8 | Profile / operation / schema / nonce grammar (F56/F57) | Stop |
| Outer 9–10 — `canon_uaii` + identifiers | **F60-L5** after `canon_uaii(request)`; before success `report_id` emission | Stop with `resource_limit_exceeded`, `report_id=""` |
| Outer 11–16 | Bindings / time / replay / `validate_transaction` / op-local | Unchanged |
| Outer 17 — stable result | Serialize → **F60-L6**; on overflow → §7 fallback | Return fallback envelope |

### 5.2 Precedence (preserved)

1. Malformed / type / size / UTF-8 / JSON / duplicate-key / non-object failures
   precede all resource-limit codes.
2. L1–L4 (and nonce-at-walk `nonce_invalid`) precede Outer 4 secrets when they
   fail first (F60 §6; F61 §4).
3. When L1–L4 pass, Outer 4 secret rejection precedes profile/operation
   acceptance (F58 Outer 4 / F57 §9).
4. Unsupported profile/operation, `execution_authorized != false`, schema,
   authorization, replay, and `validate_transaction` failures retain F56/F57/F58
   codes and relative order.
5. Received `16385` → `input_too_large` only.
6. Nonce `0` / `257` / NUL → `nonce_invalid`, never `resource_limit_exceeded`
   via L4.
7. No alternate processing path and no second validation authority.

### 5.3 Call path (future)

```
adapter/transport
  -> process_uaii_request(request_bytes, context)   # planned; absent today
       Outer 1–3
       walk_enforce_l1_l4                          # F60-L1…L4
       Outer 4–8
       canon_uaii + enforce_l5_canon_bytes         # F60-L5
       Outer 11–16
       build response + enforce_l6_response_bytes  # F60-L6 / fallback
  -> F56 §3.4 envelope
```

## 6. Error contract

### 6.1 Code mapping

| Violation | `ok` | `code` | Notes |
|---|---|---|---|
| Received size `> 16384` | `false` | `input_too_large` | Outer 1 |
| F60-L1 / L2 / L3 / L4 | `false` | `resource_limit_exceeded` | `detail=""` |
| F60-L5 | `false` | `resource_limit_exceeded` | `report_id=""`; `detail=""` |
| F60-L6 (after fallback selection) | `false` | `resource_limit_exceeded` | §7 |
| Nonce length/NUL (F57) | `false` | `nonce_invalid` | Not L4 |
| All other failures | `false` (or success path per F56) | Existing F56/F57/F58 codes | Unchanged |

`resource_limit_exceeded` is a **failure code only**. It MUST NOT invent
`get_balance` success tokens or alter F58 §8.2.1.

### 6.2 Response fields and exact order

Every response MUST use Foundation 56 §3.4 order:

1. `ok`
2. `code`
3. `interface_profile`
4. `operation`
5. `request_id`
6. `result`
7. `execution_authorized` (MUST be `false`)
8. `report_id`
9. `detail` (MUST be `""`)

### 6.3 Limit identifier policy

Accepted Foundations 56/60/61 **do not** authorize an additional response field
or non-empty `detail` carrying a limit identifier, received content, paths,
stack traces, keys, signatures, raw payloads, or environment data.

Therefore:

- Implementations MUST NOT add a `limit_id` (or similar) field to the UAII
  envelope.
- Implementations MUST NOT place limit names, counts, or excerpts of the
  request into `detail` or `result` on limit failures (`result` MUST be `{}`
  on these failures unless a later accepted profile says otherwise — F60 §7.3
  uses `result={}`).
- Internal test harness counters OUTSIDE the UAII envelope MAY record which
  limit fired; they MUST NOT leak into the response object.

### 6.4 Secret-safe diagnostics

Diagnostics MUST NOT include: secret material, private keys, signatures, raw
sensitive payloads, stack traces, filesystem paths, environment variables, or
partial oversized body copies.

## 7. L6 bounded fallback

### 7.1 Trigger

After Outer 17 constructs a candidate success or failure envelope and
`serialize_uaii_response(candidate)` yields `R > 16384`, the core MUST NOT
return that candidate. It MUST replace it with exactly one fallback envelope.

### 7.2 Fallback envelope (single, non-recursive)

Exact Foundation 56 §3.4 field order:

1. `ok` = `false`
2. `code` = `resource_limit_exceeded`
3. `interface_profile` / `operation` / `request_id` = per F56 recovery when
   safely known; else `""`
4. `result` = `{}`
5. `execution_authorized` = `false`
6. `report_id` = `""`
7. `detail` = `""`

Fixed content. Fixed field order. No copied oversized diagnostic data.

### 7.3 Measurement and recursion ban

1. Serialize the fallback and require `len(bytes) <= 16384`.
2. Under this profile, the fallback is constant-bounded and MUST fit.
3. If a defective implementation produced a fallback that still exceeded
   16384, it MUST NOT recurse, truncate JSON mid-stream, or mutate semantic
   fields to “force fit.” That condition is an implementation defect → abort
   criteria (§11); not a second fallback policy.
4. **Oversized success:** replacement MUST remain `ok=false` with
   `resource_limit_exceeded`. Success MUST NOT be misrepresented as delivered.
5. **Oversized failure:** replacement remains `ok=false` with
   `resource_limit_exceeded` (may replace a different prior failure code when
   the prior failure envelope itself exceeded L6).

## 8. Implementation sequence (future; gated)

Separate implementation authorization is required **before step 1**. Between
steps, stop on any abort criterion (§11).

| Step | Work | Stop condition before next step |
|---|---|---|
| 0 | Explicit `implementation_authorized` foundation accepted | If still `false` → **do not begin** |
| 1 | Implement `canon_uaii` in `coin/uaii_json.py` | Golden exact-order vectors; prove M2M canonicalize is unused |
| 2 | Implement `decode_uaii_json` duplicate-key reject path | Outer 3 vectors green |
| 3 | Implement `walk_enforce_l1_l4` + constants | L1–L4 boundary±1 green |
| 4 | Implement `enforce_l5_canon_bytes` | L5 boundary±1 green |
| 5 | Implement response builder + `enforce_l6_response_bytes` | L6 boundary±1 green |
| 6 | Implement `build_l6_fallback_envelope` | Oversized success/failure → single fallback; no recursion |
| 7 | Integrate into `process_uaii_request` Outer sequence | Pipeline precedence vectors green |
| 8 | Focused tests + regressions (§10) | Full matrix + F55–61 preservation probes green |

No step MAY open adapters, signers, wallets, settlement, replay mutation,
networking, services, or testnets.

## 9. Foundation 61 GAP resolution (specification level)

| F61 GAP | Resolution in this specification | Residual |
|---|---|---|
| Greenfield UAII package | Exact paths/symbols in §2.3 | Code still absent until authorization |
| Structural limit walker | §4 iterative DFS algorithm | Code absent |
| `CanonUaii` | §2.5 `canon_uaii`; M2M ban | Code absent |
| Result builder + L6 + §7.3 | §2.6, §6, §7 | Code absent |
| Conformance suite | §10 exact matrix | Tests absent |
| Context interfaces (F58 §5) | Unchanged F58 contract; not required to invent hooks here | Remains F58 implementation work; **not** a limit-spec BLOCKER |

### 9.1 BLOCKER

**None.** Every Foundation 61 GAP is either specified here or classified as
deferred F58 wiring that does not block the resource-limit contract.

## 10. Exact test specification (future; not created here)

### 10.1 Boundary±1 (every limit)

| Limit | Accept | Accept (inclusive) | Reject |
|---|---|---|---|
| L1 depth | `31` | `32` | `33` → `resource_limit_exceeded` |
| L2 members | `255` | `256` | `257` → `resource_limit_exceeded` |
| L3 elements | `255` | `256` | `257` → `resource_limit_exceeded` |
| L4 string UTF-8 bytes | `4095` | `4096` | `4097` → `resource_limit_exceeded` |
| L5 canon request bytes | `16383` | `16384` | `16385` → `resource_limit_exceeded` |
| L6 serialized response | `16383` | `16384` | `16385` → §7 fallback |

### 10.2 Required cross-cutting vectors

- Empty and mixed object/array nesting to the depth convention
- Wide versus deep structures within wire `16384`
- Duplicate keys at multiple depths → `duplicate_key` before L1–L4
- ASCII, multibyte UTF-8, escaped characters, Unicode-equivalent representations
  (decoded L4 vs wire Outer 1)
- Invalid Unicode / lone-surrogate cases → existing F56 codes, not L4
- Nonce `0` / `1` / `256` / `257` byte cases → F57 (`nonce_invalid` on `0`/`257`);
  never L4 `4096`
- Wire-size versus canonical-size differences; canonical contraction/expansion
- Oversized received request `16385` → `input_too_large`
- Oversized success and diagnostic envelopes → §7; `ok=false`
- Deterministic bounded fallback; no recursion; fallback itself `<= 16384`
- Error precedence and `detail=""` on all limit paths
- Stable response field order; repeated-run byte equality
- No-secret diagnostics
- All seven UAII operations exercise the integrated pipeline
- Foundation 57 replay, skew `300`, correlation, no-tip, and binding regressions
- `validate_transaction` authority regression
- Frozen-economics and historical-evidence regressions

### 10.3 Environment note

Treat only `m2m_verifier._CRYPTO_AVAILABLE is False` as the known environment
limitation for unrelated M2M replay crypto. It MUST NOT be “fixed” by weakening
UAII limits or Protocol validation.

## 11. Acceptance and abort criteria

### 11.1 Files a later implementation milestone MAY modify (only after authorization)

| Path | Role |
|---|---|
| `coin/uaii_reference_core.py` | create/implement |
| `coin/uaii_json.py` | create/implement |
| `coin/uaii_resource_limits.py` | create/implement |
| `tests/test_uaii_resource_limits.py` | create |
| `tests/test_uaii_reference_core.py` | create |

Any additional path requires a separate explicit authorization. Staging MUST use
exact full paths and focused review.

### 11.2 Dependency policy

No new third-party dependencies unless separately justified and authorized.
Stdlib `json` + pairs hook + iterative walk is sufficient at bound `16384`.

### 11.3 Abort conditions

Abort implementation work on:

- Ambiguity in counting, placement, or codes
- Conflicting canonicalization (M2M used for UAII)
- Altered error precedence
- Unbounded / recursive-risk traversal design
- Fallback recursion or JSON-truncating “fixes”
- Protected-path changes (Protocol, ledger, validation, supply, M2M, F55–61,
  historical evidence)
- Economic constant changes
- New authority (tip, settlement, replay mutation, adapters, network)

### 11.4 Final specification verdict

**READY_FOR_SEPARATE_IMPLEMENTATION_AUTHORIZATION**

This verdict means the resource-limit implementation contract is complete and
unambiguous. It does **not** mean coding may begin.

Alternate verdict `NOT_READY` is unused: no residual BLOCKERs remain after §9.

## 12. Verdict statement

| Question | Answer |
|---|---|
| Are F60 limits specified for deterministic implementation? | **Yes** |
| Are F61 GAPs resolved at specification level? | **Yes** |
| Are BLOCKERs present? | **No** |
| May implementation begin from this document alone? | **No** |
| Final verdict | **READY_FOR_SEPARATE_IMPLEMENTATION_AUTHORIZATION** |

## 13. Explicit exclusions

- No code, tests, scaffolds, or dependency edits in this foundation
- No staging, commit, push, merge, or branch deletion by this document’s
  creation alone
- No modification of Foundations 55–61
- No activation of adapters, signers, wallets, miners, networks, testnets,
  settlement, services, or runtimes

---

**End of Foundation 62 UAII Resource-Limit Implementation Specification v0.1**
