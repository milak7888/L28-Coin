# L28 Protocol (v1.0.0)

**Status:** FROZEN (v1.0.0)  
**Audience:** machines, implementers, validators (not investors)  
**Scope:** protocol invariants, issuance, transaction validity rules

---

## Versioning & Compatibility

- This document defines **L28 Protocol v1.0.0**.
- **Protocol invariants** MUST NOT change within v1.x.
- Any breaking change MUST be released as **v2.0.0** and MUST NOT be backported.
- Implementations MUST be **fail-closed** when required consensus state is unavailable.

---

## Definitions

- **Coinbase**: the only issuance mechanism.
- **Canonical Height (`H`)**: consensus-defined height used for reward schedule (NOT user-provided).
- **IssuedSupply**: total units created via valid coinbase events.

---

## Issuance

### Principle
L28 has **no discretionary minting**. New units may be created ONLY by protocol-defined coinbase events produced by the consensus pipeline.

- No admin mint
- No governance mint
- No manual issuance
- No “special accounts” allowed to create value
- All issuance MUST be verifiable from the public transaction stream and consensus state

### Issuance Transaction Type: `coinbase`
A coinbase event is the ONLY issuance mechanism and MUST satisfy strict identity.

A transaction is coinbase iff all are true:
- `sender == "COINBASE"`
- `type == "coinbase"`
- `coinbase == true`

Any use of `sender == "COINBASE"` that does not satisfy strict identity MUST be rejected.

### Required Coinbase Fields
Coinbase transactions MUST explicitly include:
- `receiver` (string)
- `amount` (int)
- `timestamp` (int)
- `miner` (string)
- `nonce` (int)
- `height` (int)

Coinbase MUST satisfy:
- `receiver == miner`
- `nonce` is an integer
- `height` MUST match canonical consensus height (see below)

### Canonical Height (Deterministic)
Reward calculation MUST use canonical consensus height `H`:
- `H` is obtained from consensus state (NOT user-provided height).
- If canonical height is unavailable, coinbase MUST fail closed (rejected).

### Reward Schedule (Protocol Invariant)
Coinbase amount MUST equal `Reward(H)`:
- `Reward(H)` is deterministic and depends only on canonical height.
- Reward MUST be <= `L28_MAX_COINBASE_REWARD`.
- Any coinbase with amount != `Reward(H)` MUST be rejected.

### Supply Cap (Protocol Invariant)
Let `IssuedSupply` be total units ever created via valid coinbase events.

- `IssuedSupply` MUST never exceed `L28_MAX_SUPPLY` (28,000,000).
- Coinbase validation MUST consult `IssuedSupply` from consensus/ledger state.
- If `IssuedSupply` lookup is unavailable, coinbase MUST fail closed (rejected).

---

## Non-Coinbase Transfers

For non-coinbase transactions:
- sender MUST NOT be `"COINBASE"` or `"__MINT__"` (reserved identifiers)
- signatures MAY be required by policy
- balance checks apply normally

---

## Implementation Notes (Non-Normative)

- `mint()` style APIs MUST be disabled or routed through strict coinbase + consensus ingestion only.
- Validation MUST be fail-closed for missing canonical height or supply state.
