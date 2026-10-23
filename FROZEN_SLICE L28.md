# L28 — FROZEN_SLICE.md

Date: 2026-10-22
PROJECT_STATE: ACTIVE
Slice: Historical Manifest Integrity v0.1

## AUTHORIZATION AND BASE

AUTHORIZE_FROZEN_SLICE_L28_HISTORICAL_MANIFEST_INTEGRITY_V0_1
Explicit replacement of the completed offline historical PoW slice.
Repository: /Users/pjaydondup/Projects/L28-Coin
Base: d7b6270fcb21b4b719f10973f5e70c86744d14e5
Branch: codex/historical-manifest-integrity-v0-1

## OBJECTIVE

Fix reproduced false-PASS acceptance of altered historical supply metadata and
artifact identities in the existing continuity verifier/CLI. No new framework.

## AUTHORIZED PATHS

- FROZEN_SLICE L28.md
- SYSTEM_STATE L28.md
- coin/historical_continuity_verifier.py
- coin/historical_continuity_cli.py
- tests/test_historical_continuity_verifier.py
- tests/test_historical_continuity_cli.py
- docs/historical_continuity_verifier_v0.1.md

## DELIVERABLE

Enforce immutable code-owned historical references independently of caller
metadata: cap 28000000, emission ceiling 11130000, declared supply 2824584,
treasury commitment 500000, circulating snapshot 2324584, last issuance height
100877 and reference next canonical height 100878, plus artifact identities,
sizes and counts. Preserve original records and the historical manifest.

Reject correlated tampering, missing fields, invalid types and altered artifact
identities. Clearly distinguish metadata matching pinned historical claims from
actual artifact-byte verification. Neither grants consensus, issuance,
ownership or spendability authority. Reuse existing PoW verification unchanged
except directly relevant integrity checks.

## READ-ONLY INPUTS

Raw: /Users/pjaydondup/Documents/L28-Coin/l28_genesis_ledger_old.jsonl
SHA256: 1ba544052cee098cea265add04c8fb0ff0562897803ba829b201293745aad669
Snapshot: /Users/pjaydondup/Documents/L28-Coin/l28_ledger_20251225_201521.jsonl
SHA256: 6580333e4dba688f242d82a9ea7253369b7723273b3392dc6d8ae9b78d9b2d11

## ACCEPTANCE

- Reproduce and record the manifest false-PASS cases before correction.
- Authentic metadata and artifact-byte checks pass.
- Every reproduced mutation fails deterministically, including correlated
  supply/treasury/count changes and altered heights/hashes.
- 2202/2202 raw and 817/817 selected historical PoW checks still pass.
- Focused positive/adversarial tests and directly affected regressions once.
- Actual CLI verification against authentic inputs and tampered metadata passes.
- Original historical artifact hashes remain unchanged.
- One consolidated security review: no unresolved Critical/High findings.
- Exact-path diff review, protected-path preservation and git diff --check pass.

## SAFETY

No historical data mutation/import, reminting, new consensus, private keys,
signing, mining/nonce search, networking, broadcast, custody or settlement.
No Leap28 changes. No Protocol v1.0.0, economics, canonical history, custody or
F171 changes; production gates remain BLOCKED. No unrelated architecture or
governance. Do not copy historical datasets into Git.

## STOP

On PASS update SYSTEM_STATE and make one local exact-path commit.
If evidence conflicts, stop and report without inventing replacement history.
No merge, push, deployment or subsequent milestone.
