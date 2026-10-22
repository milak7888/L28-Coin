# L28 — FROZEN_SLICE.md

Date: 2026-10-22
PROJECT_STATE: ACTIVE
Slice: Protocol v1 Coinbase Validator Strictness v0.1

## OBJECTIVE

Correct the three confirmed fail-closed coinbase-validation defects without
changing Protocol v1.0.0, canonical history, or protected economics.

## BASELINE

`3ff8bbaff1055f406fcd3ae768c3a339df64e4d2`

Branch: `codex/protocol-v1-coinbase-validator-strictness-v0-1`

## OPERATOR SCOPE AMENDMENT

`AUTHORIZE_L28_COINBASE_STRICTNESS_LEDGER_SCOPE_AMENDMENT_V0_1`

The operator explicitly adds `coin/ledger.py` to this existing slice. Pass raw
issued-supply state through the ledger's canonical-validation callbacks without
`int(...)` coercion or a missing-state zero default. The canonical validator
remains the sole issuance authority. Preserve the existing uncommitted work.
No other completed slice is reopened.

## DELIVERABLE

- exact built-in string identity for `sender == "COINBASE"` and
  `type == "coinbase"`, plus exact Boolean `coinbase is True`;
- deterministic rejection of Boolean coercion, string/numeric substitutes, and
  reserved-sender impersonation;
- one explicit nonempty string `miner` field with existing
  receiver-to-miner equality preserved;
- fail-closed rejection of negative or otherwise invalid issued-supply state;
- focused adversarial regression coverage and actual disposable-ledger evidence;
- unchanged legitimate coinbase identity, reward schedule, transaction identity,
  emission ceiling, and hard cap.

Authorized paths:

- `FROZEN_SLICE L28.md`
- `coin/tx_validation.py`
- `coin/ledger.py`
- `tests/test_protocol_conformance.py`
- `SYSTEM_STATE L28.md`

## ACCEPTANCE CRITERIA

1. Boolean, string, numeric, and reserved-sender coinbase substitutes reject.
2. Missing, empty, non-string, and alias-only miner fields reject.
3. Negative, missing, null, Boolean, float, and string issued-supply state rejects
   through both the canonical validator and the real ledger entry point.
4. The existing valid coinbase builder remains accepted with unchanged identity
   and economics.
5. Rejected coinbase inputs leave disposable balances, supply (including its
   type or absence), height, transaction count, indexes, shards, and persisted
   bytes unchanged. Rejection occurs before persistence or memory mutation.
6. Focused protocol conformance and directly affected regressions pass once.
7. The actual disposable ledger path accepts one valid test coinbase and rejects
   malformed identity, missing miner, and negative issued supply without state
   mutation.
8. One consolidated security review finds no unresolved Critical/High
   implementation issue.
9. Protocol v1.0.0, protected economics, canonical history, custody, F171, and
   all production gates remain unchanged and blocked.

## SAFETY BOUNDARY

No real keys, mining, signing, broadcast, settlement, historical import, public
networking, deployment, or provider spending. No change to Protocol v1.0.0,
protected economics, historical records, F171, custody, or production gates.
The actual-product check is confined to a temporary disposable ledger and is
not canonical issuance or historical continuation. The separate historical
manifest correction is outside this slice and must not begin automatically.

## ROLLBACK

On failure, preserve the baseline and existing uncommitted work; do not commit.
Any rollback must be limited to this slice's five authorized paths and must not
discard pre-existing work without operator authorization.

## STOP

After implementation, focused and directly affected tests, actual-product
verification, consolidated security review, system-state update, exact-path
staging, and one local commit, stop. Do not merge, push, deploy, expose
networking, correct the historical manifest, or begin another milestone.
