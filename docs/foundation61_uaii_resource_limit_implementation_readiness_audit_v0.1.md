# Foundation 61 UAII Resource-Limit Implementation Readiness Audit v0.1

**Status:** Readiness audit only (documentation; non-activation; non-implementation)

**Audit profile:** `l28-uaii-resource-limit-implementation-readiness-audit/v0.1`

**Parent contracts:**

- Foundation 60 — finite resource-limit decision specification
  (`docs/foundation60_uaii_finite_resource_limit_decision_specification_v0.1.md`)
- Foundation 58 — UAII reference-core implementation specification
- Foundation 57 / 56 — reference-core contracts / UAII parent
- Foundation 59 — evidence audit (non-authority distinction)

**Protocol baseline:** L28 Protocol v1.0.0 (FROZEN)

**Base commit:** `6087d3237f0a67c88f3a320e62a67c5842cda714`

**Branch:** `foundation61-uaii-resource-limit-implementation-readiness-audit`

**Normative subordination:** Protocol v1.0.0; then F56; then F57; then F58; then
F60 for limits/codes; then F59’s authority/non-authority distinction; then this
audit. This document MUST NOT invent limits, authorize implementation, or amend
prior foundations.

## 1. Purpose and non-authorization

This audit determines whether the **accepted Foundation 60 inclusive limits**
can be implemented safely within the specified UAII architecture (Foundations
56–58/60).

**This audit is not implementation authorization.**

Mandatory flags remain:

| Flag | Value |
|---|---|
| `execution_authorized` | `false` |
| `implementation_authorized` | `false` |
| `spend_authorized` | `false` |
| `ledger_mutated` | `false` |

### 1.1 Final readiness verdict

**READY_FOR_SEPARATE_IMPLEMENTATION_AUTHORIZATION**

Rationale: Foundations 56–60 provide complete, non-conflicting contracts for
limits, pipeline placement, error mapping, and fallback. Repository evidence
shows reusable parse/size/duplicate-key **patterns**, but **no UAII reference-core
module exists yet** (expected greenfield under Foundation 58). Remaining items
are classified as **GAP** (implementation work / missing hooks), not
specification **BLOCKER**s. A later foundation must still set
`implementation_authorized` before code may be written.

## 2. Affected surface inventory (current repository)

### 2.1 UAII target surface (specified; not present as code)

| Logical component (F58 §3) | In-repo module today | Evidence |
|---|---|---|
| `process_uaii_request` | **Absent** | No `coin/uaii*.py`; grep finds only docs |
| Envelope parser / 16384 gate | **Absent** (UAII) | Specified F56/F58/F60 |
| Secret-material rejector | **Absent** (UAII) | Forbidden keys listed F56 §6.5 |
| `CanonUaii` (`sort_keys=false`) | **Absent** | Pseudocode F57/F58; must not use M2M canon |
| Operation schema registry | **Absent** | F56 §5 schemas |
| Ledger / time / replay / Protocol delegates | **Absent** (UAII wiring) | Interfaces in F58 §5; Protocol in `coin/tx_validation.py` |
| Stable result builder + F60-L6 | **Absent** | F56 §3.4 + F60 §7.3 |
| UAII conformance tests | **Absent** | No `tests/test_*uaii*` |

### 2.2 Reusable non-UAII patterns (non-authority; pattern evidence only)

| Pattern | Path / symbol | Relevance |
|---|---|---|
| Request size + UTF-8 + duplicate-key JSON parse | `coin/disposable_sandbox_lifecycle_integration.py` `_decode`, `_parse`, `MAX_REQUEST_BYTES=16384`, `object_pairs_hook=_pairs_no_duplicates` | Closest size=`16384` parse pattern |
| Duplicate-key pairs hook family | Multiple `coin/*.py` (`_pairs_no_duplicates` / `_unique_object`) | Outer 3 duplicate-key technique |
| M2M canonicalize (sorted keys) | `coin/m2m_verifier.canonicalize` / `canonical_bytes` | **Must not** be used for `CanonUaii` |
| Protocol validation | `coin/tx_validation.validate_transaction` | Outer 15 delegate target |
| Ledger accepted-id set | `coin/ledger.BlocklessLedger._seen_tx_ids` | F57 cardinality / no-tip |
| Opaque / optional L28+hex40 | `coin/peer_handshake_identity_binding.py` `ADDRESS_RE` | Address recognize-only (F57) |

### 2.3 Call path a future implementation would introduce (greenfield)

```
adapter/transport
  -> process_uaii_request(request_bytes, context)   # F58 §4; DOES NOT EXIST YET
       Outer 1–3: type/size/UTF-8/JSON/duplicate-key
       F60 L1–L4 walk (post-parse)
       Outer 4: secret scan
       Outer 5–8: profile/operation/schema/nonce grammar
       Outer 9–10: CanonUaii + F60-L5 + report_id
       Outer 11–16: bindings / time / replay / validate_transaction / op-local
       Outer 17: result build + F60-L6
  -> F56 §3.4 response envelope
```

No existing production call path invokes UAII today.

## 3. Accepted limits (preserved)

| ID | Inclusive value | Preserved alongside |
|---|---|---|
| F60-L1 JSON depth | `32` | — |
| F60-L2 object members | `256` | — |
| F60-L3 array elements | `256` | — |
| F60-L4 non-nonce string UTF-8 bytes | `4096` | Nonce still `1..256` (F57); hex64 exact |
| F60-L5 `CanonUaii(request)` bytes | `16384` | Received request size still exactly `16384` (Outer 1) |
| F60-L6 serialized response bytes | `16384` | `detail=""` (F56) |

## 4. Pipeline insertion map

| Limit | F58/F60 insertion | Before/after decode | Before/after `CanonUaii` | Classification |
|---|---|---|---|---|
| Received size `16384` | Outer 1 | **Before** decode | Before | **READY** (contract); **GAP** (no UAII gate module) |
| F60-L1…L4 | Post-Outer-3 / pre-Outer-4 (F60 §6) | **After** successful decode + duplicate-key reject | Before | **READY** (contract); **GAP** (no walker) |
| F60-L5 | Outer 9–10 (F60 §6) | After decode | **After** `CanonUaii(request)` | **READY** (contract); **GAP** (no `CanonUaii`) |
| F60-L6 | Outer 17 (F60 §6) | N/A (response) | After response serialization | **READY** (contract + §7.3 fallback); **GAP** (no builder) |

Secret-material rejection remains Outer 4 and is **not** skipped on continuing
paths. L1–L4 first-failure may precede secret reporting (F60 §6); request still
fail-closes.

## 5. Parser / evidence sufficiency

### 5.1 What standard `json.loads` preserves

| Need | Sufficient with pairs-hook decode? | Notes |
|---|---|---|
| Duplicate-key detection | **Yes**, if `object_pairs_hook` rejects duplicates at raw boundary | Pattern: lifecycle `_parse`; also documented in `m2m_verifier` module docstring |
| Field order for UAII | **Yes** on CPython 3.7+ dict insertion order when pairs are appended in parse order | Future impl MUST retain order; MUST NOT `sort_keys=True` for UAII |
| Depth | **No during stock decode** | Requires post-decode walk or custom decoder; F60 §5 specifies DFS walk — **GAP** (algorithm ready, code absent) |
| Member / element counts | **Yes post-decode** | `len(obj)`, `len(arr)` per container |
| Decoded string UTF-8 bytes | **Yes post-decode** | `len(s.encode("utf-8"))`; escapes already applied by decoder |
| Canonical size | **Only after `CanonUaii`** | Distinct from wire length; M2M sorted canon is wrong tool |

### 5.2 Determinism risks (compatibility / DoS)

| Risk | Assessment | Class |
|---|---|---|
| Using `m2m_verifier.canonicalize` for UAII | Would break F56 exact-order digests | **GAP** if misused; contract forbids — document as anti-pattern |
| Depth-first walk order vs key sort | F60 §5 requires parse order, not sorted keys | **READY** (specified) |
| Pathological nesting within 16384 wire bytes | Bounded by L1=32 + wire size | **READY** |
| Huge decoded strings via `\u` escapes | Wire still ≤16384; L4 caps decoded bytes at 4096 | **READY** |
| Result construction blowup | L6 + §7.3 fail-closed envelope | **READY** (spec); bounded under prior L4 (~4KB upper echo) |
| No streaming parser in-repo | Full decode then walk is acceptable under 16384 | **READY** with DoS note: allocate-then-walk is fine at this bound |

## 6. Per-limit readiness

### 6.1 F60-L1 depth `32`

| Item | Result |
|---|---|
| Contract clarity | **READY** — F60 §4.1 / §5 |
| Insertion point | **READY** — post-Outer-3 |
| Existing hook | **GAP** — no UAII depth walker; no stock `json` depth limit in-repo |
| Blocker? | **No** |

### 6.2 F60-L2 members `256`

| Item | Result |
|---|---|
| Contract clarity | **READY** — F60 §4.2 |
| Insertion point | **READY** — with L1–L4 walk |
| Existing hook | **GAP** — no UAII member counter |
| Blocker? | **No** |

### 6.3 F60-L3 elements `256`

| Item | Result |
|---|---|
| Contract clarity | **READY** — F60 §4.3 |
| Insertion point | **READY** |
| Existing hook | **GAP** — no UAII array counter |
| Blocker? | **No** |

### 6.4 F60-L4 non-nonce strings `4096`

| Item | Result |
|---|---|
| Contract clarity | **READY** — F60 §4.4; nonce carve-out F57 |
| Insertion point | **READY** |
| Existing hook | **GAP** — no UAII string-byte checker; nonce grammar also unimplemented in UAII module |
| Narrow grammars | **READY** to preserve (hex64 / nonce) once schema stage exists |
| Blocker? | **No** |

### 6.5 F60-L5 canonical request `16384`

| Item | Result |
|---|---|
| Contract clarity | **READY** — F60 §4.5; explicit equality to wire max is policy, not implication |
| Insertion point | **READY** — Outer 9–10 after typed envelope |
| Existing hook | **GAP** — no `CanonUaii`; must implement F56 §3.2 (`sort_keys=false`) |
| Dependency concern | MUST NOT call M2M `canonicalize` | **GAP** guidance |
| Blocker? | **No** |

### 6.6 F60-L6 response `16384`

| Item | Result |
|---|---|
| Contract clarity | **READY** — F60 §4.6 / §7.3 |
| Insertion point | **READY** — Outer 17 |
| Fallback | **READY** — fixed failure envelope; `detail=""`; no secret leakage; cannot represent success |
| Recursion / re-exceed | **READY** under profile: echoed fields bounded by prior L4/hex64; worst-case compact envelope ≪ 16384 |
| Existing hook | **GAP** — no UAII result builder |
| Blocker? | **No** |

## 7. Error code and fallback trace

| Element | Spec authority | In-repo code today | Class |
|---|---|---|---|
| `resource_limit_exceeded` | F60 §7.1–§7.2 | Absent from `STABLE_CODES` anywhere UAII | **READY** (to add in future UAII module only); **GAP** (no module) |
| Response field order | F56 §3.4 | Absent | **READY** / **GAP** |
| `detail=""` | F56 / F60 | Pattern in lifecycle results (`detail=""`) | **READY** (pattern) |
| Precedence vs F56/F57 codes | F60 §6–§7 | N/A | **READY** |
| L6 fallback shape | F60 §7.3 | Absent | **READY** / **GAP** |
| Must not alter `get_balance` success waiver | F58 §8.2.1 / F60 §7.1 | N/A | **READY** |

## 8. Required test matrix (future; not created here)

Future implementation authorization MUST require tests for:

### 8.1 Per-limit boundary±1

| Limit | Cases |
|---|---|
| L1 | Depth `31` / `32` / `33` |
| L2 | Members `255` / `256` / `257` |
| L3 | Elements `255` / `256` / `257` |
| L4 | Decoded UTF-8 bytes `4095` / `4096` / `4097` (multibyte) |
| L5 | `CanonUaii` length `16383` / `16384` / `16385` |
| L6 | Serialized response `16383` / `16384` / `16385` → §7.3 on overflow |

### 8.2 Cross-cutting vectors

- Escaped strings (`\uXXXX`, `\\`, `\"`) vs decoded L4
- Duplicate keys → `duplicate_key` before L1–L4
- Mixed object/array nesting to depth boundary
- Canonical expansion vs wire spacing (L5 vs Outer 1)
- Received `16385` → `input_too_large` (not `resource_limit_exceeded`)
- Nonce `0` / `257` → `nonce_invalid` (not L4)
- Oversized diagnostics temptation → `detail` remains `""`
- Secret key present with legal structure → `secret_material_forbidden` after L1–L4 pass
- Byte-equivalent repeated results; concurrent determinism (F58 §11/§13)
- No ledger/replay mutation; authority flags false

### 8.3 Test gap status

| Gap | Class |
|---|---|
| No UAII unit/integration tests in `tests/` | **GAP** |
| No golden vectors for F60 limits | **GAP** |
| Replay-registry Ed25519 env (`_CRYPTO_AVAILABLE is False`) | Environment limitation only; unrelated to UAII limits |

## 9. Gaps and blockers summary

### 9.1 BLOCKER

**None.** Limit contracts, counting, placement, codes, and fallback are locked
by Foundation 60 without residual F59-style unresolved IDs.

### 9.2 GAP (must be addressed by a later implementation foundation)

1. **Greenfield UAII package** — create modules only after
   `implementation_authorized` flips true (still false here).
2. **Structural limit walker** — implement F60 §5 DFS for L1–L4.
3. **`CanonUaii`** — exact-order serializer; forbid M2M sorted canon.
4. **Result builder + L6 check + §7.3 fallback**.
5. **Conformance suite** covering §8 matrix.
6. **Context interfaces** (ledger/time/replay/Protocol) wiring per F58 §5 —
   subordinate to limits but required for full core.

### 9.3 Dependency concerns

| Concern | Verdict |
|---|---|
| New third-party JSON libraries | Not required; stdlib `json` + pairs hook + walk sufficient at 16384 |
| `cryptography` for UAII limits | Not required for L1–L6 |
| Leap28 / Nova | Forbidden |

## 10. Preservation checklist

Future implementation MUST preserve:

- Exactly seven UAII operations; exact-order serialization; field order
- Foundation 57 ten-field `UaiiLedgerStateBinding`, formulas, replay,
  `UAII_CLOCK_SKEW_TOLERANCE_SECONDS = 300`, correlation, no-tip policy
- `validate_transaction` sole settlement-validation authority
- Frozen economics: `28_000_000` / `11_130_000` / `2_824_584` / treasury
  `500_000` / circulating `2_324_584`
- Historical + Foundation 55 evidence
- Flags: `execution_authorized=false`, `implementation_authorized=false` until
  explicit later authorization, `spend_authorized=false`,
  `ledger_mutated=false`

## 11. Verdict statement

| Question | Answer |
|---|---|
| Are F60 limits implementable without inventing new policy? | **Yes** |
| Are insertion points unambiguous in the F58 pipeline? | **Yes** |
| Does current code already enforce them? | **No** (UAII core absent) |
| Are missing hooks specification blockers? | **No** — expected greenfield GAPs |
| May implementation begin from this audit alone? | **No** |
| Final verdict | **READY_FOR_SEPARATE_IMPLEMENTATION_AUTHORIZATION** |

Separate operator authorization remains required before any UAII reference-core
code, tests that execute such a core, scaffolds, or runtime activation.

## 12. Explicit exclusions

- No code or test modifications in this foundation
- No adapters, signers, wallets, settlement, replay mutation, networking,
  services, testnets
- No Leap28 / Nova
- No staging/commit/push performed by this audit document’s creation alone

---

**End of Foundation 61 UAII Resource-Limit Implementation Readiness Audit v0.1**
