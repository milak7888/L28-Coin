# AGENTS.md — L28-Coin

## Scope

Work only in:
- Repository: milak7888/L28-Coin
- Local path: /Users/pjaydondup/Projects/L28-Coin
- Remote: https://github.com/milak7888/L28-Coin.git

Do not modify Leap28, Nova, BimBumiWorld, or other repositories.
Cross-repo work requires separate authorization and an explicit interface specification.

## Identity

L28 Coin is the public M2M settlement protocol.

Keep separate from:
- Leap28 — private AI orchestration
- Nova — local-business AI platform
- BimBumiWorld — children's media/IP

Never mix code, authority, data, secrets, identity, or implementation across projects.

## Canonical Protocol

L28 Protocol v1.0.0 is frozen.
Breaking changes require governed v2.0.0.

Mandatory invariants:
- coinbase-only issuance
- no admin/governance/manual/discretionary minting
- canonical height comes from consensus state, never user input
- missing required consensus/ledger/supply state fails closed
- same public validation rules for all
- external subsystems cannot override L28 consensus authority

Bitcoin, Leap28, Harness/Evals, adapters, SDKs, or other subsystems cannot override:
- issuance
- supply
- validation
- canonical height
- consensus
- history
- settlement authority

## Protected Economic Facts

Never rewrite, recalculate, round, migrate, substitute, or silently replace:
- hard cap: 28,000,000 L28
- emission ceiling: 11,130,000 L28
- historically mined: 2,824,584 L28
- treasury locked: 500,000 L28
- circulating snapshot: 2,324,584 L28
- halving interval: 210,000
- reward schedule: 28 → 14 → 7 → 3 → 1 → 0
- historical mined-through entry: 100,877
- next canonical height after bootstrap: 100,878

Historical ledger, allocation, wallet-address, genesis, hash, snapshot, and supply records are immutable evidence.

Tests must never mint the historical amount again or treat disposable data as canonical.

## Bitcoin Interoperability

Bitcoin interoperability is external to L28 consensus and has zero authority over L28 issuance, supply, height, validation, consensus, history, or settlement.

Bitcoin work remains deterministic OFFLINE CONFORMANCE unless explicitly authorized.

These remain:
BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION

- production proof architecture
- Bitcoin confirmation count
- observer quorum

Never invent these values.

Observation is not settlement.

Passing fixtures does not activate RPC, SPV, P2P, wallets, signing, broadcast, mining, bridges, settlement, or production policy.

## Harness / Evals

Harness/Evals may exist only as an optional isolated commerce/trust subsystem.

It may provide:
- model/agent/tool evaluation
- capability evidence
- evidence reports
- versioned evaluation history
- advisory reputation or decision support

It is not L28 consensus or protocol authority.

Harness/Evals must not:
- mint
- change supply
- change canonical height
- alter consensus/history
- authorize settlement
- bypass validate_transaction
- sign
- broadcast
- submit transactions
- hold private keys, seeds, mnemonics, xprv, wallet secrets, or production credentials

Outputs are advisory only.

L28 core must work identically if Harness/Evals is removed.
Core protocol/consensus must not import or depend on Harness/Evals.

Do not introduce proprietary Leap28 internals.

## Signing / Economic Controls

Signing is a future isolated authority boundary.

Authorization is not validation.

A signer cannot:
- become consensus authority
- bypass validate_transaction
- change issuance/supply/history/height
- authorize settlement outside normal L28 rules

Do not generate/import keys or wallets.
Do not implement signer runtime without explicit authorization.

## Security

Never request, expose, store, log, print, transmit, or commit:
- private keys
- seed phrases
- mnemonics
- xprv
- wallet credentials
- RPC credentials
- production credentials
- server secrets
- tokens
- private infrastructure details

Security fixtures may use only documented disposable markers.

Never scan environment variables, .env, keychain, wallets, browser storage, SSH material, or Bitcoin Core configuration for secrets.

## Runtime Authorization

Do not start or activate without explicit operator authorization:
- server
- node
- miner
- wallet
- network
- transaction submission
- signing
- broadcast
- bridge
- deployment
- publication
- public testnet
- settlement
- production process

Read-only inspection, fetches, GitHub verification, and isolated deterministic tests are allowed.

## Repository Isolation

Before commit, merge, or push verify:

git rev-parse --show-toplevel
git remote get-url origin
git branch --show-current
git rev-parse HEAD
git status --short --branch

Expected:
- /Users/pjaydondup/Projects/L28-Coin
- https://github.com/milak7888/L28-Coin.git

Abort on repo, remote, branch, parent, or scope mismatch.
Do not trust the shell prompt alone.

## Git Rules

- use feature branches
- preserve unrelated work
- stage exact paths only
- never use git add -A
- no force-push to main
- no push without explicit operator authorization
- use --ff-only for local main integration
- independently verify remote main after authorized push

Workflow:
1. verify repo/branch/parent/remote/clean
2. lock scope
3. implement once
4. focused tests
5. one structural/security review
6. git diff --check
7. exact-path staging
8. commit
9. verify fast-forward
10. local merge --ff-only
11. final pre-push verification
12. request push authorization
13. push
14. independently verify remote main
15. stop

## Anti-Loop Policy

OBSERVE → HYPOTHESIS → ONE DIAGNOSTIC → UPDATE STATE → DECIDE

Rules:
- same command/fix max 2 attempts
- same error twice after fixes => LOOP_DETECTED
- max 5 corrective actions per blocker
- require new evidence before retry
- prefer smallest reversible change
- preserve last known-good state

When blocked report:
- objective
- state
- exact error
- attempts
- files affected
- likely root cause
- one recommended next diagnostic

## Testing

Python:
$HOME/.pyenv/versions/3.11.9/envs/l28-env/bin/python

Pytest baseline:
8.4.1

Bitcoin baseline:
- 57 fixtures
- 10 isolated Bitcoin test modules
- 224 passed

Tests must remain:
- deterministic
- offline
- disposable
- non-production
- non-networked
- non-signing
- non-broadcasting
- non-mining
- non-settling

Prefer structural JSON and AST-aware checks.
Avoid naive grep where negative/security fixtures intentionally contain forbidden strings.

## Current Published Checkpoint

Remote main:
d1a472fb53b3546d5f0922b8a9e170a9375563fb

Foundation111 completed:
docs/local_signing_economic_control_architecture_review_v0.1.md

Do not begin Foundation112 or another milestone unless explicitly requested.

## License

Apache-2.0.

Preserve:
- LICENSE
- NOTICE

Do not introduce proprietary Leap28 code or dependencies.
