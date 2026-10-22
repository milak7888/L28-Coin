# L28 — FROZEN_SLICE.md

Date: 2026-10-22
PROJECT_STATE: ACTIVE
Slice: Offline Historical PoW Verifier v0.1

## AUTHORIZATION

AUTHORIZE_FROZEN_SLICE_L28_OFFLINE_HISTORICAL_POW_VERIFIER_V0_1
Explicitly replaces the completed coinbase-strictness slice.
Repository: /Users/pjaydondup/Projects/L28-Coin
Base: 64d8d3fa52536ce2d0ff4c72bc3e6e2c49eb0442
Branch: codex/offline-historical-pow-verifier-v0-1

## OBJECTIVE AND DELIVERABLE

Extend the existing historical continuity verifier/CLI with offline historical
PoW evidence verification, preserving manifest-only behavior. No second
framework or consensus authority.

Authorized paths:
- FROZEN_SLICE L28.md
- SYSTEM_STATE L28.md
- coin/historical_continuity_verifier.py
- coin/historical_continuity_cli.py
- tests/test_historical_continuity_verifier.py
- tests/test_historical_continuity_cli.py
- docs/historical_continuity_verifier_v0.1.md

## INPUTS AND CONTRACT

Read-only raw: /Users/pjaydondup/Documents/L28-Coin/l28_genesis_ledger_old.jsonl
SHA256: 1ba544052cee098cea265add04c8fb0ff0562897803ba829b201293745aad669
Read-only snapshot: /Users/pjaydondup/Documents/L28-Coin/l28_ledger_20251225_201521.jsonl
SHA256: 6580333e4dba688f242d82a9ea7253369b7723273b3392dc6d8ae9b78d9b2d11

Verify fingerprints before parsing the same bytes. Require 102263 raw records,
72098 snapshot records, 2202 raw PoW records and 817 selected PoW records.

P = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
preimage = UTF8(decimal(entry_height) + prev + P + decimal(payload.nonce))
identifier = SHA256(preimage).hexdigest()

No added separators/newline. This is a hash preimage, not a signature.
Verify required types, nonnegative integer nonce, hash encoding, resolving parent
and parent-height relationship. Reject duplicate/conflicting records.
Selected PoW records must exactly match raw records. Verify declared difficulty
4 and disclose recovered-source difficulty 12 mismatch without policy approval.

## ACCEPTANCE

- 2202/2202 raw and 817/817 selected identifiers independently reproduce.
- Bounded parsing rejects malformed UTF-8/JSON, duplicate keys, nonfinite values,
  invalid types, missing fields, oversized inputs and tampering.
- Stable codes and nonzero CLI status for artifact or verification failures.
- Independently test record checks without relying only on pinned fingerprints.
- Separate HASH_VALID, RECORDED_DIFFICULTY_VALID,
  HISTORICAL_POLICY_AUTHENTICATED and CANONICAL_ACCEPTANCE.
  Last two remain false with UNPROVEN/BLOCKED explanations.
- Exit zero denotes evidence-only success; known policy mismatch stays visible.
- Focused tests once and directly affected regressions once; actual CLI against
  authentic artifacts and adversarial fixtures; original hashes unchanged.
- One consolidated security review: no unresolved Critical/High findings.
- Exact-path review and git diff --check pass.

## SAFETY

No mining/nonce search, signing, keys/secrets, custody, network, historical import,
reminting, ledger mutation, broadcast, settlement or deployment.
No Leap28 modification/dependency. No historical datasets in Git.
No historical-manifest, Protocol v1.0.0, economics, canonical-validator/history,
F171 or production-gate changes. No policy authentication, spendability or
independent-approval claims.

## STOP

If required evidence fails, preserve work and report without committing.
On full PASS, update SYSTEM_STATE and create one local exact-path commit.
No merge, push, production activation or subsequent milestone.
