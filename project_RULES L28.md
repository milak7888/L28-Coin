# L28 PROJECT_RULES

## Mission
Build L28 into a functional, executable, useful machine-to-machine currency for AI systems.

The primary real-world use case is AI-to-AI commerce: AI/agent A requests useful work from AI/agent B, receives a quote in L28, pays in L28, receives the result, verifies settlement, and receives a machine-readable receipt.

Target interoperability includes ChatGPT, Claude, Gemini, Grok, DeepSeek, trading bots, custom agents, open-source models, and future AI systems through provider-neutral interfaces such as HTTP/JSON, MCP, and SDKs.

Do not depend on any AI provider officially endorsing L28.

## Core Flow
DISCOVER → REQUEST → QUOTE → PAY → WORK → VERIFY → RECEIPT → REUSE

Product path:
1. disposable offline L28 transfer
2. two-agent service transaction
3. HTTP/JSON + MCP access
4. cross-AI interoperability
5. isolated local network
6. limited testnet
7. broader public testnet
8. production

## Delivery Over Completeness
Stop improving infrastructure when acceptance criteria pass.

Every task must state:
- Objective
- Deliverable
- Acceptance criteria
- Stop condition

Do not add extra abstractions, frameworks, validation layers, governance docs, agents, or speculative hardening unless they directly unblock the current frozen objective.

When frozen acceptance criteria pass: record evidence → commit when practical → update state → STOP.

## Execution-First Rule
Every milestone must do at least one of:
1. create a new runnable L28 capability
2. remove a concrete blocker to the next runnable capability
3. materially improve a capability required for real use

A milestone consisting only of readiness records, evidence inventories, policy, review packets, planning, or documentation does not count as progress unless it directly enables the next executable step.

Prefer:
IMPLEMENT → AUTOMATED TESTS → ACTUAL-PRODUCT VERIFICATION → EVIDENCE → ACCEPTANCE → STOP

Not:
DOCUMENT → GATE → REVIEW → DOCUMENT → GATE

Tests and security evidence support working software. They are not the product.

## Strategic Anti-Loop
If two consecutive milestones end with the same top-level blocker or leave the same user-visible capability unchanged: STOP.

Do not create another similar gate/evidence milestone.

Instead:
1. identify the exact blocker
2. identify the smallest executable step that crosses it
3. request one explicit operator authorization if required
4. execute after authorization

Repeated documentation of the same blocker is not progress.

Debug anti-loop:
OBSERVE → HYPOTHESIS → ONE DIAGNOSTIC → UPDATE STATE → DECIDE

- Same command/fix max 2 attempts
- Same error twice after fixes => LOOP_DETECTED
- Max 5 corrective actions/blocker
- No retry without new evidence
- Smallest reversible fix first

## Global Efficiency
Maximum signal, minimum tokens.

Use one primary model/thread. No subagents/multiple models unless explicitly authorized.

Default to ONE LARGE BOUNDED BATCH when work shares one baseline and one authority/security boundary.

In one branch:
inspect → implement safe work → focused tests once → affected regressions once → actual-product verification → evidence → one consolidated review → acceptance decision → one commit → local FF merge → pre-push verify → request push authorization.

Split only for dependency, conflict, materially higher risk, authority/security boundary, runtime/network/signing/deployment, or separate authorization.

## Owner Burden
The operator is not the engineering loop.

AI decides ordinary reversible technical matters:
- implementation details
- file layout
- helper functions
- tests
- debugging
- small refactors
- routine security checks

Do not repeatedly ask the operator to approve routine technical work.

Escalate only for:
- Protocol v1.0 normative change
- protected economics/history
- real key custody
- production secrets
- real signing authority
- broadcast
- networking/public testnet
- deployment
- irreversible production state
- real financial authority
- material security/legal decisions
- external spending

## Session Start Protocol
At the start of every new AI session:
1. Read `project_RULES L28.md`.
2. Read `SYSTEM_STATE L28.md`.
3. Read `FROZEN_SLICE L28.md`.
4. State PROJECT_STATE: ACTIVE / FINALIZE / COMPLETE.
5. If `FROZEN_SLICE L28.md` is missing, STOP and ask the operator to define one.
6. If requested work is not traceable to the frozen slice, add it to `DEFER L28.md` and do not build it.

No exceptions for quick/small/while-I’m-here work.

## Project State
Only the operator changes PROJECT_STATE.

ACTIVE:
Implement approved frozen scope only.

FINALIZE:
No new features, architecture, abstractions, agents, or refactors.
Only:
completion blockers → fixes → focused tests → actual-product verification → evidence → one consolidated review → PASS/FAIL.

CRITICAL BLOCKER:
Prevents safe operation of the capability in the current frozen slice.
Everything else: DEFER.

COMPLETE:
Only the operator may set this state.
After COMPLETE, no new work until the operator reopens ACTIVE.

## Frozen Slice Control
Before coding, `FROZEN_SLICE L28.md` must define:
- objective
- deliverable
- acceptance criteria
- safety boundary
- stop condition
- date

Once frozen, the slice is locked. Changes require closing the build session and reopening as operator.

`DEFER L28.md` receives all non-slice ideas. Growth is not completion.

Before new work ask:
“Does this move L28 closer to one machine purchasing useful work from another using L28?”

If no → DEFER.

## System State
`SYSTEM_STATE L28.md` is authoritative for:
- stack
- architecture/schema
- built components
- runnable behavior
- known gaps
- latest verified commit/state

Update it after every completed slice.

Repository/files are authoritative. Do not use chat memory as implementation source of truth.

## Source-of-Truth Precedence
The L28 repository copies of these files are the live authoritative project controls:

- `project_RULES L28.md`
- `SYSTEM_STATE L28.md`
- `FROZEN_SLICE L28.md`
- `DEFER L28.md`

During active local work, the checked-out repository copies are authoritative.
After publication, remote `main` is the published authority.

ChatGPT Project Source copies are mirror/snapshot bootstrap context only.

If a ChatGPT Project Source copy and a repository copy disagree, the repository copy wins.

Routine repository updates do NOT require re-uploading Project Source copies.

At the start of a new session:
1. use Project Sources to identify the L28 repository and permanent safety rules
2. verify current repository/remote state
3. read the repository copies of the four project-control files
4. use those repository copies for implementation decisions

## First Functional Product Target
L28 Agent Payment Protocol / Agent Gateway v0.1

Minimum interface:
- discover_services
- request_service
- get_quote
- authorize_payment
- verify_payment
- get_result
- get_receipt

Reuse existing L28 M2M/UAII flow where applicable:
service_request → service_quote → payment_authorization → settlement_reference → useful work → service_receipt

Start with ONE useful service.
Do not build a marketplace before one end-to-end transaction works.

First major success state:
AI A → requests useful work → receives L28 quote → pays L28 → AI B performs useful work → result returned → payment verified → receipt produced

## Canonical Protocol — Immutable
L28 Protocol v1.0.0 is frozen.
Breaking normative change requires governed v2.0.0.

Preserve:
- coinbase-only issuance
- no admin/governance/manual/discretionary mint
- canonical height from consensus state only
- missing required state fails closed
- no subsystem/operator override of issuance, supply, validation, height, consensus, history, or settlement
- same public validation rules for all
- canonical validator: `coin.tx_validation.validate_transaction`

## Protected Economics — Immutable
- hard cap: 28,000,000 L28
- emission ceiling: 11,130,000
- historically mined: 2,824,584
- treasury locked: 500,000
- circulating snapshot: 2,324,584
- halving interval: 210,000
- rewards: 28→14→7→3→1→0
- historical mined-through: 100,877
- next canonical height: 100,878

Never rewrite, recalculate, round, migrate, remint, or substitute historical ledger/allocation/wallet/genesis/hash/snapshot/supply records.

Disposable test state is never canonical history.

## Bitcoin
Bitcoin is external evidence only.

Bitcoin has zero authority over L28 issuance, supply, height, validation, consensus, history, or settlement.

Observation ≠ settlement.

Do not invent unresolved production Bitcoin architecture merely to unblock isolated L28 execution.

## Security / Signer
Never request/read/expose/store/log/print/transmit/commit production:
- private keys
- seeds
- mnemonics
- xprv
- wallet/RPC credentials
- tokens
- server secrets
- private infrastructure

Do not scan:
- `.env`
- secret-bearing environment values
- keychain
- wallets
- browsers
- SSH
- Bitcoin Core configs

Disposable test-only material may be used only when the frozen slice explicitly authorizes that bounded experiment.

Eligibility ≠ signer invocation.
Authorization ≠ Protocol validation.

Do not silently convert test fixtures into production authority.

## Assurance Model
ASSURANCE_MODEL=OPEN_SOURCE_PUBLIC_REVIEW

No paid independent audit is required as a universal release gate.

Still require deterministic tests, affected regressions, adversarial/security tests where applicable, reproducible evidence, and disclosure of unresolved failures.

When accurate:
NOT_INDEPENDENTLY_AUDITED=true

Never claim independent review unless it actually occurred.

Known Critical/High findings involving secret exposure, unauthorized signing, Protocol bypass, arbitrary minting, supply/history mutation, validation bypass, or unauthorized settlement must block the affected capability.

## Repo Isolation
Only repo:
Local: `/Users/pjaydondup/Projects/L28-Coin`
Remote: `https://github.com/milak7888/L28-Coin.git`
Public: `milak7888/L28-Coin`

L28 is independent from Leap28, Nova, and BimBumiWorld.

Never mix code, authority, identity, secrets, data, dependencies, or repos.

Before commit/merge/push verify:
- `git rev-parse --show-toplevel`
- `git remote get-url origin`
- `git branch --show-current`
- `git rev-parse HEAD`
- `git status --short --branch`

Exact-path staging only.
Never `git add -A`.
Never force-push main.
Never push without explicit authorization.

Without explicit operator authorization never:
start/restart server/node/miner/wallet/network; sign production material; broadcast; submit transactions to a public/production system; bridge; deploy; publish public testnet; settle production value; or activate production/runtime.

Read-only inspection and deterministic non-networked tests are allowed unless a stricter frozen boundary says otherwise.

## Testing
Python:
`$HOME/.pyenv/versions/3.11.9/envs/l28-env/bin/python`

pytest:
`8.4.1`

Prefer deterministic disposable tests and structural JSON/AST security checks.
Avoid rerunning unchanged suites unnecessarily.

Tests remain offline/non-production/non-networked/non-broadcasting/non-mining/non-production-settling unless a frozen slice explicitly authorizes a bounded experiment.

## Mandatory Completion Gate
Every implementation slice must pass this sequence in order:

IMPLEMENTATION
      ↓
AUTOMATED TESTS
      ↓
ACTUAL-PRODUCT VERIFICATION
      ↓
EVIDENCE
      ↓
ACCEPTANCE CRITERIA
      ↓
STOP

Tests passing is not completion.

The agent must verify the implemented behavior against the actual runnable product and produce observable evidence before acceptance criteria may PASS.

Rules:
- Automated tests may prove code-level correctness, but they do not by themselves prove the product works.
- After tests pass, run the actual user/AI-facing workflow defined by the frozen slice.
- Verify observable behavior end to end using the real runnable local product at the authority level permitted by the slice.
- Evidence must come from actual-product verification: command output, API/MCP response, state transition, receipt/result, or other directly observable behavior required by the slice.
- Mock-only, fixture-only, structural-only, documentation-only, or unit-test-only evidence cannot satisfy actual-product verification.
- If actual-product verification cannot be performed because of a missing dependency or authorization, the acceptance criterion remains NOT PASS and the exact blocker must be reported.
- Do not replace failed product verification with more tests, reviews, or documents. Fix the product or report the blocker.
- Acceptance criteria may PASS only after implementation, automated tests, actual-product verification, and evidence all pass.
- Once acceptance criteria pass, STOP. Do not add more work to the slice.

## Definition of Done
L28 is not successful because tests, documents, gates, or Foundations exist.

A phase is successful when a user or AI can actually use a new L28 capability end to end.

Completion overrides perfection.

Build the shortest safe path to a runnable L28 machine-to-machine use case.
Do not let governance, evidence, tests, or repeated gates replace actual execution.

## Progress Report Format
After each meaningful batch report only:
- OBJECTIVE
- WHAT NOW WORKS
- WHAT A USER/AI CAN NOW DO
- REAL-WORLD UTILITY CREATED
- TEST RESULTS
- ACTUAL-PRODUCT VERIFICATION
- EVIDENCE
- ACCEPTANCE CRITERIA
- REMAINING BLOCKER
- NEXT SHORTEST EXECUTION STEP
- AUTHORIZATION NEEDED, IF ANY
- STOP CONDITION

Do not measure progress primarily by Foundation number.
