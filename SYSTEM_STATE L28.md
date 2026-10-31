# L28 — SYSTEM_STATE.md

Last updated: 2026-10-31

## PROJECT STATE
PROJECT_STATE: ACTIVE

Only the operator may change PROJECT_STATE.

## CURRENT — FIRST PAID TEXT SUMMARY — 2026-10-31

Final operator authority:
AUTHORIZE_L28_PAID_TEXT_SUMMARY_V0_1_ACCEPTANCE_AND_LOCAL_COMMIT.
Final acceptance: PASS. Slice status: COMPLETE_PENDING_OPERATOR.
The operator accepted the recorded results conditional on final verification;
all frozen criteria reconciled against the unchanged source/test hashes, existing
HTTP/payment/receipt/REUSE/adversarial/cleanup evidence and release inventory.
The COMPLETE checkpoint a6a93c922ece5f40579dbefedccd61b996c7b287 is preserved.
No additional tests, runtime execution or source changes were required.
Exactly one local ten-path implementation commit is authorized after staged
review; earlier UNCOMMITTED/no-commit statements below are historical to the
build phase. The resulting Git commit records its own identity; no self-referential
hash is inserted here. PROJECT_STATE remains ACTIVE. STOP after commit verification;
no merge, push, deployment, runtime or new milestone. Production gates remain BLOCKED.

### Accepted build evidence — preserved

Operator authorization: AUTHORIZE_FROZEN_SLICE_L28_FIRST_PAID_TEXT_SUMMARY_V0_1
reopens ACTIVE for the ten-path bounded HTTP/JSON summary purchase. The three
COMPLETE records were preserved verbatim in local checkpoint
a6a93c922ece5f40579dbefedccd61b996c7b287 (parent a85c653fcb5241b635d16628ba207337355fae93).
Branch: codex/paid-text-summary-v0-1. ACCEPTANCE: PASS for the bounded summary
slice, with implementation UNCOMMITTED. PROJECT_STATE remains ACTIVE; only the
operator may transition it. No implementation commit, merge/push, installation,
public/physical session or deployment is authorized. STOP; no next milestone.

The actual HTTP requester can discover and buy l28.service.text_summary/v0.1
for 28 disposable L28, receive a deterministic extractive summary and the full
signed public artifact bundle, and independently verify source/service/payment/
result/receipt bindings. The existing structured-analysis default is preserved.
No model/API dependency, second ledger/payment engine, new route or framework.
Input is nonblank UTF-8, <=4096 characters; up to three source sentences, rational
term-frequency scoring, stable ties, source-order restoration, indices/input hash.

Verification: 54 distinct focused cases covered by passing results; initial run
52 passed/1 failed, diagnosed order-preserving CLI serialization and reran only
the failed case (1 PASS). One confirmed slow-response deadline issue was then
corrected; the new case and three affected CLI/startup cases passed (4 PASS).
Directly affected regressions: 112 PASS once. No repeated full passing suite.
Actual final-code CLI: two fresh requester/provider processes per invocation,
PIDs 9797/9807 and 9816/9826, both exit 0. Each independently verified payment,
summary and receipt; balances 100/0 -> 72/28, issued supply/mint height zero,
replay rejected, provider stopped, listener closed. REUSE used different input,
fresh payer/provider identities and transaction IDs. No historical supply used.
Payment IDs:
f1135cf2bbbf73798d89e6f6484a7a3c06f82161b60aefc3e82f686b124be714
255377ab2445fe6b1301666af8062d5527e28ada6ed2a879b2082da39402c920
Receipt IDs:
5aba849c83a6c65553431492166085354e0d5dfb5c3c91131eadea5abf3b9083
3125445d5e302cf8a6afdc61ec4ec8f27b6444cdd0efe53fbcb7dc7b810c9d45
HTTP/CLI SHA-256: 02708016547d308fee6e67568386f6d0a29119396848372aa44627286f9a6323
Core SHA-256: 9f49301f0cf43e483ba5adffa20b0508dc800797b434b92240060ca8dc033de8

Five actual loopback HTTP adversarial cases reject with status 400: forged
signature/wrong network -> canonical_validation_failed; wrong amount/recipient/
quote -> payment_binding_invalid. All providers/listeners cleaned up. Public
reverification of the final CLI bundle PASS; result, receipt, service, input and
payment tampering reject. Tests prove rejected payments create no ledger/work;
partial startup, slow HTTP and invalid input fail closed with process cleanup.
One consolidated local review: no unresolved Critical/High implementation issue;
NOT_INDEPENDENTLY_AUDITED=true. Public evidence, commands, exact algorithm and
residual limits are in docs/paid_text_summary_v0.1.md. Existing RC byte inventory
is refreshed, with explicit local revision metadata and no exposure claim.

Protocol v1.0.0, protected economics/history, validator/ledger, custody/F171 and
all production gates remain unchanged/BLOCKED. No real custody, production
signing, mining, issuance, canonical broadcast/settlement or deployment. Receipts
prove signed disposable artifacts, not canonical finality. Prior acceptance and
immutable evidence below remain historical and preserved in the checkpoint.

## HISTORICAL — OPERATOR-AUTHORIZED SLICE COMPLETION — 2026-10-30

Operator authorization: L28 — FINAL PROJECT COMPLETION RECORD. The operator
explicitly authorized PROJECT_STATE: COMPLETE for the accepted physical two-host
frozen slice at commit a85c653fcb5241b635d16628ba207337355fae93.
Frozen acceptance remains PASS; the accepted evidence, runtime digest and
qualification of physical/Surface attestations below are unchanged. This records
completion of that bounded slice, not production/mainnet or custody readiness.
Production custody/F171 remain BLOCKED; Protocol v1.0.0, economics/history, source
and all security restrictions are unchanged. Earlier ACTIVE/finalization statements
are historical. No new frozen slice is opened. No further work until the operator
explicitly reopens ACTIVE and authorizes scope. This authorization permits only
these completion-record edits, not staging, commit, merge, push, tests, sessions,
activation or deployment. STOP after record verification.

## HISTORICAL — PHYSICAL SLICE ACCEPTED / LOCAL FINALIZATION — 2026-10-30

Authorization: AUTHORIZE_L28_PHYSICAL_SLICE_FINALIZATION. The operator accepted
the final review as COMPLETE_PENDING_OPERATOR and authorized necessary completion
records plus one exact-path local milestone commit, then STOP. PROJECT_STATE
remains ACTIVE. This closes the existing two-host slice, not the L28 project;
it grants no new runtime session, implementation, merge, push or deployment.
Branch: codex/two-host-disposable-sync-v0-1.
Parent/base: 530a307f56e7eb79007fb0309fc93a6e0b9f2c0b.

ACCEPTANCE: PASS for one physical, disposable, private-LAN two-host experiment.
Session: a649173ab9cdf2a4e432cdb284027e90.
Runtime digest: 6578a9d9b6ba975ef3d94b7cfa50e9f8e875d29e2c05648e8a34df1dd828dbf1.
Node SHA-256: 71e4a37e9edffe78130997f2d2806dfa58e72f6742587ff73b494b48abc23413.
Mac writer: 192.168.68.50; Surface follower: 192.168.68.54:42828; trusted uma
is operator-attested. Surface native source/dependency preparation at this digest
is operator-reported PASS (Python 3.11.6, cryptography 49.0.0, pyOpenSSL 26.4.0).

Evidence basis: actual Mac initial.json/restart.json were inspected and reconciled
against the accepted source. Surface outcomes, physical machine separation,
complete-fingerprint comparisons and Windows cleanup are explicitly operator-
attested; raw Windows report files were not independently inspected here.
Both hosts report PAIR_PHASE_PASS / initial exit 0 and PAIR_WORKFLOW_PASS /
restart exit 0 for the same session, source, transaction IDs and commitment.
Mac PIDs 62051 -> 62065 prove its fresh local process; Surface genuine restart is
operator-confirmed. START 1793327439 is retained, public certificate pins are fresh,
durable state agrees, supply is 28 and final balances are 0/28. TLS/HMAC precede
canonical validation and persistence. Replay rejects without memory/disk mutation;
restart performs the terminal divergence probe and persists HALTED_BY_OPTION_A.
The accepted disposable session is terminal and must not be resumed or reused.

State commitment: 98056ec92a23fc0186ef51c39c0ae6d0acf224f692c4ccfd510fa93f55547964
Transaction IDs:
0f2e6924652d5e6c37464e0cc9f6a4734c27d8fa86f555ad52ac2f614b688baa
6b3c2d0a78fbdab05e43ea376efdf0744af11405e9c324837e98dab7de19b738
Mac report directory: l28-pair-launch-Axsq8LNv in the operator's temporary folder.
initial.json SHA-256: 013c0169edf2912b961aa85ac89837d440e16a5064d69f884c991d7f394b2d71
restart.json SHA-256: ff7ee11da9a26f56ddc233c24cdecf82d41487653b164a7c35c85d2cd68d382e
Original reports/disposable state remain external and unchanged; only sanitized
public evidence references are recorded here, not copied historical/test ledgers.

Cleanup: connection_and_identity_closed=true; Mac running lock absent, no Mac
test-node process or TCP 42828 listener found at final review. Operator reports
MAC_CLEANUP_VERIFIED, SURFACE_CLEANUP_VERIFIED and L28_FINAL_CLEANUP=PASS, including
Surface listener/process absence and removal of its temporary Private firewall rule.

physical_two_host_verified=false is hardcoded in both physical and offline report
paths. It is a conservative absence of programmatic physical-topology attestation,
not a failed transaction check. Physical separation and screen comparison rely on
the operator; physical_comparison=operator_attested and transport=PRIVATE_LAN are
preserved. No Boolean was changed or independent security audit claimed.

Accepted verification reused: 34 focused cases and 141 directly affected
regressions PASS, actual offline two-process initial/restart/rejection checks PASS,
and the actual physical evidence above. One consolidated local security review
found no unresolved Critical/High implementation issue in this bounded scope;
NOT_INDEPENDENTLY_AUDITED=true. Finalization changes only completion records;
accepted node/tests/dependencies and runtime digest are unchanged. No suites or
physical sessions repeated. Final allowlist, staged/unstaged diff, whitespace,
source/evidence hash and acceptance checks are required before the local commit.

Protocol v1.0.0, economics/history, canonical validation, ledger, custody/F171 and
production blocks remain unchanged. No production custody, signing, canonical
issuance, mining, broadcast, settlement or public networking is authorized.
Historical/custody decisions and EVD-001 independent-review requirements remain
open. Earlier pending/offline-only sections below are dated historical evidence,
not the current acceptance status. STOP after the authorized local commit; any
integration/publication or new slice requires separate operator authorization.

## HISTORICAL — AUTOMATIC PAIRING / FRESH-PROCESS PHASES — 2026-10-29

Authority: AUTHORIZE_L28_AUTOMATIC_PUBLIC_PAIRING_AND_LAUNCH_AMENDMENT and
AUTHORIZE_L28_PAIRING_PER_FRESH_PROCESS_PHASE; offline implementation only,
same seven paths, branch codex/two-host-disposable-sync-v0-1, base/HEAD
530a307f56e7eb79007fb0309fc93a6e0b9f2c0b. This section supersedes the older
manual-record launch instructions below; those are retained as dated evidence.

The new paired coordinator exchanges bounded UNTRUSTED complete public records,
validates the existing certificate/role/source/endpoint/phase/context contract,
and displays a complete role-ordered, domain-separated SHA-256 fingerprint.
Each local terminal requires PAIR after physical comparison of BOTH displays.
The public acknowledgment is NOT authentication. Exact-pin TLS key-possession
verification and the existing mutually authenticated HMAC channel still precede
ledger activity. Initial context remains null during pairing; fresh session/START
are then bound inside TLS/HMAC. Restart pairing binds the retained session/START.
No manual JSON, pin, timestamp, secret or state-path copying is needed.

One generated native-shell launcher per computer sequences initial and restart
processes and handles only public reports/state paths. Two comparisons total,
one per fresh-process phase, each locally approved on both computers. No Python
credential-bearing supervisor, private IPC or serialized TLS identity was added.
Unapproved, mismatched, malformed, wrong-role/source/endpoint, interrupted and
expired pairing fails closed. Public approval acknowledgment waits only to the
existing certificate deadline, not the ordinary ten-second frame idle timeout.
TLS activation checks validity before identity cleanup; identities close before
ledger application. Active budget remains <=120 seconds and is capped by both
certificate expirations and the original session START+600. Restart never resets
START. The follower reuses the existing disposable listener's SO_REUSEADDR binding
for sequential restart, exact address/port and peer checks retained.

Current runtime digest:
6578a9d9b6ba975ef3d94b7cfa50e9f8e875d29e2c05648e8a34df1dd828dbf1
Node SHA-256:
71e4a37e9edffe78130997f2d2806dfa58e72f6742587ff73b494b48abc23413
The other nine runtime closure files, including requirements, canonical validator
and ledger, are byte-identical to the verified 3fd81298 Surface ZIP. No new
dependency. Surface parity at 3fd81298 is historical, NOT current parity.

Verification: 34 focused automatic-pairing cases PASS; 141 disjoint directly
affected coordinator/handoff/prepared regressions PASS (175 unique cases).
Two launcher-generation/syntax cases rechecked after cleanup-output adjustment,
both PASS. The initial focused run exposed two fixture errors and the new
activation-after-identity-close ordering error; fixtures/order corrected, targeted
checks and the final focused set PASS. No tests were weakened.

Actual final-source CLI via explicit AF_UNIX offline transport and public PTY
test approvals: OFFLINE_PAIRED_CLI_PASS. Initial PIDs 50865/50866; fresh restart
PIDs 50869/50870, no overlapping phase processes. Both roles independently validate
the same two events; issued supply 28, balances 0/28, identical commitments before
and after durable restart, same START, replay rejects without mutation and the
restart divergence probe halts. Each phase proves pinned TLS/HMAC and closes its
identity/connection. Declined pairing exits 1/1 (coordinator_interrupted and
pairing_not_approved), with no success report or ledger activity. All owned test
state/reports, PTYs, sockets and processes cleaned up. No TCP listener or firewall
action. Runtime check PASS with network_started=false.

State commitment: 61f3af514003e6589bdd55415e56b4262cf85dc1ddb39da328ad04a0232153d3
Transaction IDs:
eb57b66f336823d775dff030e09b45e262fdde924a03188d01890d9370cced92
504516cb55a45032fe62dceeae10aa89aac73126407e3ccea29a226272d1954a

Consolidated local security review: no unresolved Critical/High implementation
finding identified. Core TLS identity/handoff, HMAC, validation, ledger, economics,
history, custody and F171 unchanged. Existing nondisclosure regressions scan
captured output, ciphertext and persisted test records for generated private
authentication material and prohibit credential-file/keylog APIs. New public
pairing/report/launcher paths neither accept nor serialize that material.
NOT_INDEPENDENTLY_AUDITED=true; no managed scan or qualified approval claimed.
Operator physical comparison, trusted local OS/clocks and source parity remain
assumptions; Python/OpenSSL cannot guarantee all memory copies/swap erasure.
Hard-watchdog exit 124 can leave a public crash lock; never clear it to force retry.
Mac launcher parses with zsh; Windows launcher has static scope/finally checks,
but no native PowerShell execution was available here. Offline IPC is NOT proof
of Windows firewall behavior, real LAN reconnection or physical transaction PASS.

STATUS: this amendment OFFLINE PASS; full physical slice NOT PASS. Changes remain
uncommitted. Clean main preserved. No physical session, firewall change, deployment,
commit, merge or push. Next: approved source synchronization/native Surface parity
and launcher preflight, then separate authorization for one physical session.

## PREPARED ENROLLMENT AMENDMENT — 2026-10-29

Authorization: AUTHORIZE_L28_PREPARED_ENROLLMENT_AMENDMENT. PROJECT_STATE ACTIVE;
offline implementation only in the existing seven paths, same feature branch and
base 530a307f56e7eb79007fb0309fc93a6e0b9f2c0b. No physical retry or commit here.

Latest physical evidence is operator-reported: both hosts reached PUBLIC_ENROLLMENT
but neither peer-pin prompt completed. Mac reported coordinator_enrollment_expired,
MAC_INITIAL_EXIT=1; Surface exit 124 and SURFACE_CLEANUP_VERIFIED. No transaction
or agreement was verified. Exit 124 is consistent with the hard-watchdog path,
not independent proof of its precise origin. Repeated timed retries are stopped.

The operator approved direct physical inspection of the complete public record
on the independent peer computer as this disposable experiment's trust channel.
The coordinator now displays a canonical PUBLIC_ENROLLMENT envelope containing
the existing public bindings plus phase, fixed endpoint scope and public DER
certificate. Its prompt imports VERIFIED followed by that entire JSON line.
Bare pins, missing local attestation, unknown/missing/duplicate fields, altered
source/role/IP/port/phase/context, noncanonical JSON, malformed/substituted DER,
bad self-signature, unsupported certificate profile and expiry fail closed.
VERIFIED is operator attestation, not cryptographic proof of physical inspection.
It cannot safely be supplied for a merely network-learned record. Exact TLS
certificate verification and HMAC still prove the actual peer/key before ledger
application; this amendment does not create automatic trust-on-first-use.

The same memory-only TLS identity survives preparation through activation. Its
unchanged certificate expiration bounds preparation; former 300-second enrollment
and 420-second total invocation caps are superseded. A hard watchdog bounds the
wait. No socket/listener, ledger operation or new payment-session START occurs
during preparation. PREPARED_ENROLLED is not transaction PASS. Follower import
is local readiness, with no second READY; writer READY remains. Activation rechecks
local/peer certificate validity, source parity and retained restart context. Active
runtime is at most 120 seconds and no later than local/peer expiry or the original
600-second session. Monotonic preparation/peer deadlines and active transition
overhead cannot extend those budgets. Restart retains START. Expiry never refreshes
credentials or automatically retries. A late activation has a shorter runtime.

Current runtime source digest:
3fd812981f3a9e38b52173da220ebb02948f9a84ae81d912dab777da1812c7de
Current node SHA-256:
e225598e6296593d711ec18f8953c011dce902ba36b30296fc5a16d3b9350e16
The Surface's 3dd065c1 result is historical parity, not parity for this new source.
No installation or transfer performed. The other nine runtime closure files,
including requirements, canonical validator and ledger, are byte-identical to the
verified archive. Main remains unchanged. No private material is serialized.

Tests: 58 focused prepared-lifecycle/record and real both-role coordinator cases
PASS; 79 disjoint directly affected coordinator/handoff regressions PASS. Four new
offline prepared-record rejection scenarios were then added and tested separately,
all PASS: 141 unique cases, no failed/weakened tests. Superseded 300/420 timing tests
were replaced with the approved certificate-bound policy, preserving expiry,
interruption, writer READY, timeout, restart and cleanup coverage. Fake-clock cases
prove 450-second preparation without early socket/state/session activity; at 590
seconds activation is capped by remaining certificate lifetime. Initial START is
created only at activation; restart does not replace it. EOF/cancellation, malformed,
unverified, substituted, wrong-role/source/context and expired records reject.

Actual final-source CLI: runtime-check exits 0, network_started=false; retired
3dd065c1 digest rejects exit 1. Offline coordinator exits 0, prepared_public_records_verified=true,
pinned_tls_and_hmac_verified=true, independent_validation=true, cleanup_complete=true;
supply 28, balances 0/28, two transaction IDs, durable reopen agreement, replay
rejection and terminal divergence halt. Four reason=replay stderr warnings are
expected negative probes. All 11 negative CLI scenarios exit 1 with empty stdout:
wrong-pin, wrong-peer, source-mismatch, interrupted, tamper, bootstrap-context,
bootstrap-pin, unverified-record, substituted-record, wrong-record-source and
wrong-record-role. Actual CLI checks include the new public-record parser and the
shared real TLS/HMAC/ledger workflow. The console/state transition itself is tested
through coordinator_main using offline transports and fake-clock inputs, not a
native physical console. Offline physical_inspection_verified, physical_two_host_verified
and physical_process_restart_verified are all false.
State commitment: c2eb1737d98fbce27063605e5d368aae29729d8c8c79e404137fd200c8eb7b63.
Transaction IDs:
ebe9498b0656c6b68cd8d40ab8b08e0836fa3ec37e952c4030666aa7cc8e4263
e1a56f5aec12e8095651a94fb0221aba5405c82a0de1212ef95521763472efee

One consolidated local review: changed runtime scope is prepared public-record
construction/validation, certificate-bound input/deadline transition, offline
reproduction probes and their CLI choices. MemoryTLSIdentity, PinnedTLSHandoff,
HMAC transport, canonical ledger/validation, economics/history, custody and F171
are unchanged. No unresolved Critical/High implementation finding identified in
this bounded review. NOT_INDEPENDENTLY_AUDITED=true; no managed scan/qualified
approval claimed. Physical inspection cannot be machine-proven; trusted local
hosts/clocks are assumed. Python/OpenSSL memory erasure, swap/core dumps, power-loss
cleanup and Windows complete-record copy/input usability are not proven. The hard
watchdog can still exit 124 without a coordinator-specific diagnostic; preserve
numeric wrapper exit codes. No physical transaction or process restart is claimed.

STATUS: prepared enrollment OFFLINE PASS; full physical slice NOT PASS.
No physical session/listener, firewall change, secret transfer, deployment, commit,
merge or push. Existing uncommitted work preserved. Next: synchronize this candidate
to Surface through an approved method, verify native parity and prepared-record
input compatibility, then obtain separate physical-session authorization. STOP.

## FOLLOWER READY GATE CORRECTION — 2026-10-29 (HISTORICAL)

Authorization: AUTHORIZE_L28_FOLLOWER_READY_GATE_CORRECTION. Existing seven-path
scope, feature branch and base 530a307f56e7eb79007fb0309fc93a6e0b9f2c0b;
offline verification only. No physical retry, firewall change or commit here.

The follower now requests only the independently verified Mac public certificate
pin. Valid local pin entry advances directly to FOLLOWER_LISTENING, without a
second READY input. The writer still requires READY after observing that status.
Pin entry confirms local readiness, not cryptographic peer authentication: exact
pinned TLS and HMAC remain required before ledger activity. Automatic initial
numeric START, restart retention, peer/source binding and all deadlines remain
unchanged: 300 seconds enrollment, 120 active, 420 invocation, 600 network session.

Current runtime source digest:
3dd065c1a99e176d846839a45e71d55f22890934b358021c074840e8188550cd
Current node SHA-256:
9029d83ae008a15c67bc3e334352a5beb415fe1cc9fbe2fd80505585a4abc334
The previous 3aaf995f archive remains unchanged and is not current Surface parity.

Focused tests: 10 passed. Affected selection: 65 passed, including seven overlapping
new negative cases; 68 unique cases passed (10 focused plus 58 additional distinct
regressions). No failed or weakened tests. The both-role coordinator_main test
uses real TLS/HMAC over offline byte transports, verifies one follower input and
two writer inputs, matching independently validated states and listener cleanup.
Fake-clock cases cover immediate/299-second pin entry, self/malformed/empty pins,
300-second expiry, timeout mapping, EOF and cancellation, with no false PASS and
identity/socket/watchdog cleanup. No physical TCP listener was opened.

Actual CLI: runtime-check exits 0, network_started=false; retired 3aaf995f digest
rejects exit 1, coordinator_source_parity_invalid. Offline coordinator exits 0,
cleanup_complete=true, pinned_tls_and_hmac_verified=true, independent_validation=true,
supply 28, balances 0/28, two transaction IDs, durable reopen agreement, replay
rejection and divergence halt. Physical host/process restart flags remain false.
State commitment: e267ac6788a47ac16137d9fbaec712a50532676baac60dbe9e84ed9f6f47d15e.
Transaction IDs:
37532af3fbda76b76b188cd9c16132fc9a48e4adab8f797fcd2fdf60d656bf33
b81f9bb175b25083e273104200edb81f7c8bf59b2473f4ab826b5b46535742dd
Wrong-pin and interrupted CLI cases exit 1 with empty stdout and respectively
tls_peer_or_record_authentication_failed / coordinator_interrupted. Expected
reason=replay warnings are negative-probe evidence, not initial transfer failures.
The standalone offline CLI exercises the shared connected workflow; the changed
input path itself is exercised by the both-role coordinator_main/fake-clock tests.

One consolidated local review compared against the SHA-256-verified 3aaf995f ZIP:
only coordinator_main changes, exactly replacing the shared READY branch with a
writer-only branch. The other nine runtime closure files are byte-identical.
TLS certificate verification, memory-only identities, HMAC, canonical validator,
ledger, economics, history, custody and F171 are unchanged. No secret persistence
or additional authority was introduced. No unresolved Critical/High finding was
identified in this bounded local review; NOT_INDEPENDENTLY_AUDITED=true. No managed
scan or qualified approval is claimed. Existing hard-watchdog exit 124 can still
terminate without a coordinator-specific diagnostic; this diagnostic limitation
is unchanged, and the prior Surface exit cause remains UNPROVEN. No cleanup or
Windows console behavior beyond offline evidence is claimed.

STATUS: follower READY correction OFFLINE PASS; physical slice NOT PASS.
No physical session, Windows rule change, installation, transfer, commit, merge
or push performed. Next: approved minimal Surface source synchronization and
native parity at the new digest, then separately authorized physical verification.
Do not reuse expired session credentials. STOP reached for this amendment.

## ENROLLMENT TIMING AMENDMENT — 2026-10-29 (HISTORICAL)

Authorization: AUTHORIZE_L28_ENROLLMENT_TIMING_AMENDMENT. Same seven paths,
same feature branch/base; offline verification only. This supersedes prior
physical attempt authority: no physical retry, firewall change or commit here.

The existing coordinator now bounds offline public-pin enrollment/readiness at
300 seconds before any socket or ledger activity. Surface additionally confirms
READY before listening; Mac confirms READY after observing FOLLOWER_LISTENING.
Only then is its initial numeric START generated and active runtime begun.
Public pin entry remains operator-verified, not a network-learned pin or TOFU.
Cryptographic peer authentication still occurs inside unchanged pinned TLS/HMAC.

The active watchdog allows at most 120 seconds, with an absolute 420-second
invocation ceiling. Remaining credential validity and the original 600-second
session also cap runtime. Restart revalidates the retained START after enrollment;
it never generates a replacement START. The enrollment watchdog starts before
restart metadata loading. Switching watchdogs cannot extend the active deadline.
Certificates remain in memory, keep the existing lifetime and are never replaced
after pin approval; expired credentials/enrollment reject before opening sockets.
No private material, CLI signing facility, dependency or authority path was added.

Current runtime source digest:
3aaf995fafc604749068d70a99d5212642d6b5bba289562e68aea5088be496c4
Current node SHA-256:
1a89008409ab30c6a88830d4ee3c3ed30a238fd885a13288708698918e88a10b
The prior fe56e608 Surface result is historical preparation, not parity for this
changed runtime. Other nine runtime closure files are unchanged. No transfer or
dependency installation was performed by this amendment.

Validation: 17 unique fake-clock timing cases and 41 directly affected coordinator
regressions PASS. Initial focused 16 and regression 41 passed; review added a
watchdog-transition budget case and the final combined selection passed 58 cases
(82 deselected). A final review moved restart metadata loading under the existing
enrollment watchdog; only its two directly affected restart cases were rechecked,
both PASS. No tests failed or were weakened. Both-role real TLS/HMAC coordinator
paths use offline byte transports; no real TCP listener was opened.

Timing coverage includes 299-second enrollment/readiness retaining the runtime
budget; expiry at 300/301; self/malformed pins; input timeout mapping; active
timeout; credential expiry; watchdog-switch overhead; restart expiry and remaining
session budget. Every failure checks credential/socket/watchdog cleanup and no
false PASS. Existing regressions preserve pin mismatch, peer/source/session
binding, tampering, nondisclosure and validation-before-persistence checks.

Final-source native --runtime-check exits 0 with network_started=false and the
current source digest above; the prior fe56e608 digest rejects, exit 1,
coordinator_source_parity_invalid. Actual --offline-coordinator exits 0 with
cleanup_complete=true, independently validated supply 28, balances 0/28, two IDs,
durable reopen agreement, replay rejection and terminal divergence halt.
State commitment: 326d7f84c0c123cfde3bbc46d9a8a0a6ad60151252de9608be082aa611ad358b.
Transaction IDs:
ae0b493787f6caf9bac0991105e9e07da0a6f6c06769683936584205807da67f
40cc9a90963c894f5098b0eb519b852e60190a0d5fc5465f6d4f9d833865bb45
Final-source wrong-pin and interrupted CLI cases both exit 1 with empty stdout,
respectively tls_peer_or_record_authentication_failed and coordinator_interrupted.
The CLI exercises the unchanged TLS/HMAC/ledger/reopen/replay/divergence workflow;
the amended enrollment/activation path itself is exercised through coordinator_main
in focused timing and both-role offline API tests. It is not a physical console
timing demonstration. Physical two-host and physical process-restart flags are false.

Consolidated local review: relative to the verified endpoint candidate, the only
changed runtime definitions are coordinator_main and _coordinator_enrollment_input,
plus the enrollment-bound constant. All nine other closure files match the pinned
archive. Pin/certificate verification, memory-only identities, HMAC, validator,
ledger, transaction identities, history, economics and production gates are
unchanged. Review covered premature socket/state creation, phase/credential/session
expiry, watchdog transitions, delayed input, false PASS and every cleanup branch.
No unresolved Critical/High implementation finding identified in this bounded
offline review. NOT_INDEPENDENTLY_AUDITED=true. The managed security-diff skill
requires out-of-allowlist scan artifacts, so no managed scan or signoff is claimed.
No application secret/key persistence was introduced; existing nondisclosure and
cleanup regressions pass. Python/OpenSSL complete memory erasure, OS compromise,
power-loss cleanup and real Windows console timing are not proven by these checks.

STATUS: enrollment-timing amendment OFFLINE PASS; full physical slice NOT PASS.
No physical session/listener, Windows rule change, dependency installation, source
transfer, commit, merge or push. Candidate remains uncommitted. Prior failed local
session cleanup must be operator-confirmed before any later physical attempt.
Next: synchronize only this corrected candidate source/parity on Surface through
an approved method, then obtain separate physical-session authorization. Do not
reuse prior session material or continue physical work under this amendment.

## SURFACE ENDPOINT AMENDMENT — 2026-10-29 (HISTORICAL)

Authorization: AUTHORIZE_L28_SURFACE_ENDPOINT_AMENDMENT_192_168_68_54.
Current scope: Mac writer 192.168.68.50, Surface follower 192.168.68.54, TCP 42828.
Only LAN_FOLLOWER_IP changes in runtime code; socket/certificate/context bindings
continue to derive from that shared constant. No authentication, ledger, validator,
Protocol, economics, history, custody or F171 behavior is changed.

Worktree recovery restored the missing .git link and 824 missing baseline files
from exact HEAD 530a307, without replacing surviving files. All seven surviving
candidate paths matched the verified archive before restoration. Main and the
19-file verified runtime snapshot/archive are preserved. Candidate remains on
codex/two-host-disposable-sync-v0-1, uncommitted at the same base.

The Surface native preparation at the prior 2481871a digest is operator-reported
PASS (Python 3.11.6, cryptography 49.0.0, pyOpenSSL 26.4.0). It does not establish
parity after this endpoint edit. The original ZIP/manifest remain immutable
provenance for the old candidate; use the corrected full runtime digest for parity.
No physical session, firewall change, commit, merge or push is authorized here.
The dated integration evidence below is retained, not a current digest assertion.

Corrected runtime digest:
fe56e6081232fb0752f78fa10b5c405fa4338a308bad4c0481453b34947ee7a4
Corrected node SHA-256:
41eeb2fa77a7df11ba8d593d81ec4fda263dfee9aba672beacea595aaec4dea3
The old node SHA-256 d79c163dfdbdefbdc4bbeacac5f4645d0f16c61ecc99071017d6c673d9d1c72c
is required before the one-line Surface correction. The complete ten-file runtime
closure must match the approved old digest before writing and new digest after;
do not alter the historical ZIP/manifest or claim its old manifest matches new bytes.

Validation on Python 3.11.9 / cryptography 49.0.0 / pyOpenSSL 26.4.0:
- 16 passed / 107 deselected, once: endpoint context/certificate/retired-peer
  coverage, actual offline coordinator nondisclosure/cleanup, seven negative paths,
  both coordinator CLI roles, runtime parity and socket-setup cleanup failures.
  Command: python -B -m pytest -q -p no:cacheprovider
  tests/test_persistent_disposable_testnet_node.py -k 'endpoint_amendment or
  coordinator_actual_offline_execution or coordinator_negative_paths or
  coordinator_both_cli_roles or coordinator_runtime_source_parity or
  coordinator_socket_setup_failure'. No live IP socket was used by these checks.
- Exact comparison with verified snapshot confirms the sole runtime delta is
  LAN_FOLLOWER_IP .75 -> .54. Existing dependencies and nine other closure files
  remain byte-identical. New runtime-check exits 0, network_started=false; old
  digest exits 1 with coordinator_source_parity_invalid.
- Actual --offline-coordinator exits 0: pinned TLS/HMAC, independent canonical
  validation, supply 28, balances 0/28, two transaction IDs, durable reopen,
  replay rejection, divergence halt and cleanup_complete=true. Physical two-host
  and physical process restart flags remain false. Actual wrong-peer CLI exits 1,
  no stdout, coordinator_peer_address_invalid. No session/listener/firewall started.
- Consolidated local endpoint-delta review found no unresolved Critical/High issue:
  no trust-check bypass or address-only socket override; certificate SAN, context,
  peer checks and listener derive from the same constant. Not independent approval.

STATUS: Mac correction/offline verification PASS. On 2026-10-29 the operator
reported corrected Surface native preflight PASS: expected digest above,
192.168.68.54, uma/Private, TCP 42828 available, retired firewall rule absent and
network_started=false. Mac 192.168.68.50 was locally read and its runtime check
passed; Mac SSID uma is explicitly operator-confirmed. No direct Surface control
is available; its result is operator evidence, not a local measurement.

The operator now authorizes one final bounded physical session per FROZEN_SLICE,
including the narrow temporary Windows rule and a local commit only on full
physical acceptance. Initial/restart transaction evidence remains PENDING.
No physical PASS or commit is claimed from preflight. No implementation changes
or repeated offline suites are required to start this authorized test.

### Authorized physical attempt — deadline expired; NOT PASS

After Surface ARMED confirmation, one Mac writer process was started with the
approved runtime digest. It reached PUBLIC_ENROLLMENT but did not receive the
Surface public certificate pin before its 120-second invocation deadline.
The process exited 1 with coordinator_deadline_expired. No retry was started.
The operator reports Surface reached its public-pin prompt; its cleanup remains
pending confirmation. No peer authentication, connection, transaction, physical
restart or state agreement was demonstrated. Do not reuse this retired attempt.
The Mac process exited and its TCP 42828 listener check returned no entries.
Surface must cancel its follower and verify removal of the exact temporary rule
and listener. Physical acceptance remains NOT PASS; no commit is authorized.

## PHYSICAL COORDINATOR INTEGRATION — OFFLINE PASS / PHYSICAL PENDING (2026-10-27)

Operator authorized completion inside the same seven-path allowlist on 2026-10-27.
Branch codex/two-host-disposable-sync-v0-1; base/HEAD remains
530a307f56e7eb79007fb0309fc93a6e0b9f2c0b. The prior uncommitted work is preserved.
No additional dependency or repository path was introduced. requirements-m2m.txt's
existing pyOpenSSL 26.4.0 / cryptography 49.0.0 pins are unchanged in this batch.

Implemented --coordinate for the actual writer and follower CLI. It displays only
public role/certificate-pin/source enrollment data. The operator enters the peer's
64-character public certificate pin after direct comparison on that physical
machine's terminal; no network-learned pin, TOFU, secret prompt, manual START,
secret argument/environment/file, credential file or alternate auth scheme exists.
The writer generates the session and numeric START. Bounded public bootstrap data
is UNTRUSTED until the exact peer/role/network/source/session/START/phase context
matches inside pinned TLS and existing mutual HMAC; only then can the existing
ledger path validate and persist events. A single peer-IP-checked connection uses
TCP 42828, memory-BIO TLS, then unchanged HMAC/ledger frame semantics.

Initial and restart invocations share the existing validator, ledger, state
commitments, replay protection and Option A. Restart loads each host's own public
session metadata and ledger, enrolls fresh public certificate pins, and retains
the original numeric START/session window. The same connected ledger routine is
reused by the old in-memory input interface; no second ledger or consensus engine.
Successful phase reports include source, endpoints, session/START, PID, data path,
state and cleanup status. No PASS is printed after failed enrollment/setup/auth.

Current runtime source digest (supersedes all earlier archives/digests):
2481871a789dcd301e874142d26c673445821a2e85ca1c7a153adb8af63240b5
Node SHA-256:
d79c163dfdbdefbdc4bbeacac5f4645d0f16c61ecc99071017d6c673d9d1c72c

Verification on Python 3.11.9, cryptography 49.0.0, pyOpenSSL 26.4.0 using the prior
disposable dependency target /private/tmp/l28-pyopenssl-2640.9o3lHB/runtime:

- 41 unique new coordinator cases PASS. Coverage includes the integrated TLS wire
  driver, public pin enrollment, both actual CLI-role paths over offline byte
  transport, automatic START, source binding, Windows-style bounded public input,
  malformed/oversized input, mode conflicts, restart metadata and listener/identity
  cleanup on bind/listen/accept/connect/close failure. Windows input was emulated;
  no Windows-native or physical runtime PASS is claimed.
- 80 directly affected offline regressions PASS once (39 prior handoff cases and
  41 prior core cases). The existing real loopback listener test was excluded by
  the current no-listener authority; no passing unrelated suite was repeated.
- Actual CLI --offline-coordinator exits 0 after real TLS memory-BIO handoff,
  existing HMAC, the canonical-validator disposable 28 L28 coinbase/transfer,
  independent ledger agreement, durable reopen, replay rejection and divergence
  halt. State is supply 28, balances 0/28, two transaction IDs. Its report sets
  physical_two_host_verified=false and physical_process_restart_verified=false.
  Owned ephemeral ledger directories, identities, pipes and worker threads clean
  up. This proves offline reopen, not physical process restart or persistence.
- Seven actual CLI adversarial cases exit 1 with empty stdout and exact codes:
  wrong-pin / tamper => tls_peer_or_record_authentication_failed;
  wrong-peer => coordinator_peer_address_invalid;
  source-mismatch => coordinator_enrollment_binding_invalid;
  interrupted => coordinator_interrupted;
  bootstrap-context => tls_frame_binding_invalid;
  bootstrap-pin => coordinator_pin_mismatch.
- Actual --runtime-check with the pinned source digest exits 0 and reports
  network_started=false. Its source inventory covers all ten existing runtime
  closure files, not only the changed node. Surface must use this Mac-approved
  digest rather than deriving an expected value from unverified local files.
- Nondisclosure guards verify generated auth bytes/hex are absent from reports,
  logs and persisted disposable ledger files; TLS file loaders, key logging,
  real IP sockets and subprocess creation are forbidden by the offline guard.
  Existing asyncio uses AF_UNIX control socketpairs, not network peers/listeners.
- Two initial fixture guards incorrectly blocked that asyncio IPC; one diagnostic
  identified the self-pipe and only those failed cases were corrected/rechecked.
  A bootstrap test initially preloaded the follower context unlike the real
  coordinator; its diagnostic identified the mismatch, the fixture was corrected
  to real initial behavior, and the unchanged binding-rejection assertion passed.
  The evidence harness also diagnosed four expected public replay warnings on
  stderr; successful evidence requires exit/result/state checks, not empty stderr.

One consolidated local review covered all changed behavior: public-pin trust,
bootstrap-as-untrusted-data, TLS/HMAC context/role/source binding, unchanged
validation-before-persistence, framing/deadlines, fail-closed reports and cleanup.
It corrected cleanup so a socket-close error cannot skip identity disposal or
watchdog cancellation/join. No unresolved Critical/High implementation finding
was identified in this offline scope. This is not independent security approval.
No guarantee of complete Python/OpenSSL buffer erasure, protection from local OS
compromise, power-loss cleanup or an authenticated source distribution is claimed.
The operator's physical pin comparison and reviewed source digest are trust inputs.

Mac en0 was independently read as 192.168.68.50 on 2026-10-27. Surface
192.168.68.75 / trusted uma / Private profile remain operator-scoped prerequisites,
not freshly measured here. README gives fail-closed Windows dependency/parity,
IP/profile/port checks, public pin enrollment, initial/restart commands and the
separately authorized narrowly scoped firewall wrapper with mandatory finally
removal/verification. Normal failures close listener/socket/identity/input; the
120-second last-resort process deadline closes OS handles on exit. Crash locks
remain fail-closed. A killed shell/power loss requires independent rule cleanup.

STOP: offline coordinator integration PASS; full physical frozen acceptance is
still BLOCKED pending approved candidate transfer/dependencies, Windows-native
verification, fresh endpoint/source checks, explicit runtime/firewall authorization,
then actual Mac/Surface transaction, process restart and cleanup evidence. No
physical session, live TCP/IP listener, firewall modification, commit, merge,
push, deployment or production activation occurred. Primary main remains clean.
Protocol v1.0.0, economics, history, validator, custody and F171 remain unchanged.

## AUTHENTICATION-INPUT / TLS DEPENDENCY AMENDMENT — OFFLINE PASS

Historical 2026-10-26 evidence below; its runtime digest is superseded above.

Operator authorization 2026-10-26 added requirements-m2m.txt as the seventh
authorized path and approved pyOpenSSL==26.4.0. Its wheel metadata requires
Python >=3.9 and cryptography >=49,<51; compatibility was exercised on Python
3.11.9 / cryptography 49.0.0 / OpenSSL 3.6.4. Only the approved wheel and its
required typing_extensions 4.16.0 were installed into disposable target
/private/tmp/l28-pyopenssl-2640.9o3lHB/runtime; the existing interpreter and
cryptography installation were not changed. Wheel SHA-256:
f0eb0cb2d581d3ad2b9c489468485e7f2ab6727d08401bcf9d824c3caddf3c1c.

The existing node now implements TLS 1.3 memory-BIO handoff with mutually pinned
disposable certificates, direct cryptography identity objects (no credential
files), fresh undisplayed 32-byte authentication material, role/peer/source/
session/phase/numeric-START binding, bounded frames/deadlines and single-use
in-memory input into the existing mutual HMAC authentication. Manual getpass,
secret copying and redirected-stdin assumptions are removed. CLI --lan without
verified in-memory input fails closed before sockets or state creation.

Offline actual-product command:
PYTHONPATH=/private/tmp/l28-pyopenssl-2640.9o3lHB/runtime
/Users/pjaydondup/.pyenv/versions/3.11.9/envs/l28-env/bin/python -B -m
coin.persistent_disposable_testnet_node --offline-auth-handoff
(PYTHONPATH is the public dependency location, not authentication material.)
The assignment and command above form one shell command; see README for the
portable interface after installation of the approved dependencies.

Verified evidence in this amendment:

- 39 unique new focused cases passed: initial 23, additional 13, final 3 cleanup
  regressions. The final targeted run passed 11 cases (3 new plus 8 rechecks after
  failure-cleanup changes). No failing test was hidden or weakened.
- Existing directly affected offline regressions: 41 passed, once. The existing
  loopback two-process listener test was intentionally excluded by this
  amendment's no-listener boundary; its prior passing evidence is retained below.
- Actual CLI: valid handoff exit 0, TLSv1.3, both roles HMAC authenticated, inputs
  consumed, cleanup_complete=true, physical_two_host_verified=false. Runtime
  source digest: 06f0efb424e55348c730497e12e91ea196de9c162a617ec3a4f02d4ecd3adb28.
- Six actual CLI negative probes each exited 1 with no stdout: wrong-pin,
  tamper and replay => tls_peer_or_record_authentication_failed; wrong-peer =>
  tls_peer_binding_invalid; expired => lan_session_invalid_or_expired;
  incomplete => tls_delivery_incomplete. Exact codes were asserted, not merely
  nonzero status. HMAC mismatch, malformed material, context/source substitutions,
  oversize, invalid START and partial credential initialization also reject.
- Non-disclosure tests forbid socket/process creation, file writes, TLS file
  loaders and key logging. Generated authentication bytes/hex are absent from
  stdout/stderr/logs and captured ciphertext. Failed handoffs close identities,
  endpoints and owned buffers; successful inputs are single-use and discarded.
- Baseline AST comparison: all existing core functions/classes unchanged except
  the main dispatcher; ledger/validator, protected economics/history, custody and
  F171 paths unchanged. Exactly seven authorized changed paths; no staged edits.

One consolidated local security review checked trust/pin binding, TLS version,
context framing, authentication-before-ledger use, error disclosure, fail-closed
input paths, resource cleanup and unchanged authority boundaries. No unresolved
Critical/High issue was identified within this offline scope; this is not an
independent cryptographic approval. Python/OpenSSL internal key conversions and
immutable copies exist only in memory; complete erasure, OS swap/core-dump
exclusion, local OS compromise protection and physical host identity are not
claimed. The offline fixture directly enrolls public pins in one trusted process.

Physical two-host acceptance remains BLOCKED: a physical ciphertext coordinator
and independently authenticated public-pin enrollment are not supplied or tested
by this offline amendment. Windows dependency verification, refreshed source
parity and separate runtime approval remain necessary. Previous archives/digests
are stale. No new physical session, node process, socket, firewall change,
production activation, local commit, merge or push occurred in this amendment.
The primary main checkout remains clean at 530a307; candidate remains uncommitted.
The local TCP 42828 listener check returned no entries. A global process-list
check was unavailable (sysmond service absent); no claim of an OS-wide process
audit is made. All offline CLI children exited and owned worker threads joined.

## PRIOR TWO-HOST CORE EVIDENCE — RETAINED, NOT CURRENT RUNTIME APPROVAL

Authorization: `AUTHORIZE_FROZEN_SLICE_L28_TWO_HOST_DISPOSABLE_SYNC_V0_1`
Base: `530a307f56e7eb79007fb0309fc93a6e0b9f2c0b`
Branch: `codex/two-host-disposable-sync-v0-1`
Isolated worktree: `/private/tmp/l28-two-host-disposable-sync-v0-1`
Status: UNCOMMITTED; physical acceptance and completion remain BLOCKED.

The existing persistent disposable node now has an opt-in private-LAN mode for
Mac writer/client and Surface follower (endpoints superseded above). It reuses
BlocklessLedger, canonical validation, disposable signing, durable replay and
Option A without changes to those authority modules. HMAC-SHA256 challenge-response
binds roles, endpoint/network/config identities, source digest, session and fresh
challenges. Canonical bounded frames bind types and strict per-direction sequences.
The same two events are incrementally validated and persisted; only a validated
prefix can resume. Restart checks replay rejection and an expected terminal
divergence probe. Divergence writes a public halt marker, never replacement history.
Session expiry is 600 seconds; a hard watchdog bounds each invocation to 120 seconds.
The initial candidate used a hidden interactive secret prompt; this is superseded
by the in-memory TLS amendment above. Retired physical attempts did not pass and
their authentication material must never be reused.

Verified locally using Python 3.11.9 / cryptography 49.0.0:

- Focused suite initially: 38 passed, one existing loopback subprocess test blocked
  by sandbox socket permissions. A direct loopback-bind diagnostic confirmed
  `PermissionError: Operation not permitted`. Only that failed regression was
  rerun with loopback permission: 1 passed. No LAN socket was opened.
- Review-strengthened tests: 14 passed, 28 deselected (11 binding cases now use
  valid MACs over invalid bindings, plus three new CLI/path/nonprefix cases).
  **All 42 unique focused cases passed**; passing unrelated tests were not repeated.
- Affected regressions, once: **116 passed** across `test_protocol_conformance.py`,
  `test_disposable_testnet_identity.py`,
  `test_disposable_network_identity_genesis_binding.py`, and
  `test_foundation146_149_option_a_offline.py`.
- Commands used `python -B -m pytest -q -p no:cacheprovider` with the above paths.
- Real CLI `--source-inventory`: exit 0; actual subprocess LAN invocation without
  a private terminal then returned exit 1, `lan_secret_requires_private_terminal`.
  The new guard is `lan_authentication_handoff_required`; neither is physical proof.
- Offline in-memory transport tests authenticate both roles, synchronize two events,
  reopen independently persisted state, resume a partial follower, reject replay,
  compare supply/balances/IDs/commitments and persist terminal divergence halts.
- Adversarial coverage: invalid keys/roles/network/session/source/phase/type/sequence,
  Boolean substitutions, MAC tampering, old-frame replay across handshakes,
  duplicate/malformed/noncanonical/oversized JSON, interrupted frames, invalid
  transaction signatures, corrupt records, invalid state paths and stale/halt locks.

One consolidated local implementation review inspected authentication/context and
sequence binding, validation-before-persistence, bounded IO/watchdog, restart/halt
behavior, public-only evidence, exact changed paths and unchanged production gates.
No unresolved Critical/High implementation issue was identified in this bounded
offline review. This is not an independent cryptographic review or a managed
security-scan approval. The managed scan workflow requires out-of-scope artifacts;
no extra review framework or scan configuration was created.
Residual limits: HMAC provides no confidentiality; local OS compromise and traffic
denial of service are not prevented; Python memory zeroization and power-loss
durability are not claimed. A crash can leave a fail-closed lock requiring separate
inspection; no automatic lock removal, history repair or reward regeneration exists.

Earlier source-transfer and endpoint checks are historical evidence only; they do
not establish current parity after the TLS amendment. Operator-reported current
scope is Mac 192.168.68.50 and Surface 192.168.68.75 on trusted home LAN uma, with
Surface Python 3.11.6 / cryptography 49.0.0 and Private profile. Those runtime
prerequisites must be refreshed before any separately authorized physical session.
No physical state commitment or two-host PASS is claimed. No local commit is
permitted until both hosts complete the transaction/restart/rejection checks and
clean shutdown required by the full frozen slice.

Protocol v1.0.0, protected economics, historical artifacts, canonical validator,
custody and F171 remain unchanged. Production authority remains BLOCKED. EVD-001
is not integrated. No merge, push, deployment or other-project change occurred.

## COMPLETED HISTORICAL MANIFEST INTEGRITY — 2026-10-22

Status: PASS / ACTUAL-PRODUCT VERIFIED / LOCAL COMMIT CANDIDATE
Authorization: `AUTHORIZE_FROZEN_SLICE_L28_HISTORICAL_MANIFEST_INTEGRITY_V0_1`
Base: `d7b6270fcb21b4b719f10973f5e70c86744d14e5`
Branch: `codex/historical-manifest-integrity-v0-1`

The existing continuity verifier now matches all 70 manifest reference fields
against immutable code-owned literals, with exact types and closed root/section
schemas, while retaining the existing arithmetic and authority checks. References
are not loaded from caller metadata. No manifest or historical data was changed.
The reference next canonical height 100878 is checked against pinned last issuance
100877 and reported only as a reference, not as initialized consensus state.

Baseline diagnosis reproduced 22 leaf-level false-PASS cases:

- Alter/delete audit date, consolidation record count, DAG leaf count, final-lock
  path length, claimed snapshot timestamp, final entry height, last issuance
  height, snapshot byte size and raw byte size (18 cases).
- Alter consolidation hash, final-entry hash, snapshot hash and raw hash (4 cases).

Six correlated false-PASS cases also reproduced against the immutable baseline:
treasury/unlocked redistribution; missing-height/declared-supply increase;
raw-candidate count increase; parent-partition redistribution; consolidation/
genesis redistribution; and linked issuance/count/supply/consolidation increase.
All six preserved the old equations. All 28 reproduced cases now reject.

Validation with `/Users/pjaydondup/.pyenv/versions/3.11.9/envs/l28-env/bin/python`:

- Focused: `-B -m pytest -q -p no:cacheprovider
  tests/test_historical_continuity_verifier.py
  tests/test_historical_continuity_cli.py -k ManifestIntegrity` — **7 passed**.
  Includes alteration/deletion/type rejection across all 70 fields, six
  equation-preserving mutations, unknown claims and nonfinite values.
- Affected regressions: same command with `-k 'not ManifestIntegrity'` —
  **33 passed**, including existing manifest and PoW tests. Both selections ran once.
- Actual CLI subprocess tests: all 22 baseline leaf cases plus three correlated
  supply/treasury/count cases returned exit 1; equivalent valid metadata returned
  exit 0. Report IDs bind the explicit evidence/authority flags.

Actual product commands (run with the interpreter above):

```sh
python -B -m coin.historical_continuity_cli \
  --manifest docs/l28_historical_continuity_manifest_v0.1.json --pretty
python -B -m coin.historical_continuity_cli \
  --raw-dag /Users/pjaydondup/Documents/L28-Coin/l28_genesis_ledger_old.jsonl \
  --snapshot /Users/pjaydondup/Documents/L28-Coin/l28_ledger_20251225_201521.jsonl \
  --pretty
```

Both exited 0. Metadata report: `MANIFEST_METADATA_VALID=true`,
`ARTIFACT_BYTES_VERIFIED=false`, `HISTORICAL_POLICY_AUTHENTICATED=false`,
`CANONICAL_ACCEPTANCE=false`, scope `pinned_manifest_metadata_only`.
Manifest SHA256: `b477529809564ded69954ace5ea5f14f7d4888229a35a5ceb1f269043e679c7f`.
Metadata report ID: `ef24c822d28cb01484ec4762e22873bca2ed4dd66e3e0971505f0536c39ce577`.

Separate artifact verification: 102263 raw / 72098 snapshot records;
**2202/2202 raw PoW** and **817/817 selected PoW** verified. Recorded difficulty
4 passes; source difficulty 12 mismatch remains explicit. PoW report ID unchanged:
`1770505f73167a3011cac7e7fbecfccdffcf5b30af9b254d87efadf07a1f08d8`.

Original bytes independently fingerprinted before and after verification:

- raw: 40707627 bytes;
  `1ba544052cee098cea265add04c8fb0ff0562897803ba829b201293745aad669`
- snapshot: 30658355 bytes;
  `6580333e4dba688f242d82a9ea7253369b7723273b3392dc6d8ae9b78d9b2d11`

Consolidated manual offline security review covered the complete changed-file
scope, caller-controlled reference substitution, correlated arithmetic attacks,
strict types/schema, stable rejection codes, report semantics, and unchanged PoW
behavior. No unresolved Critical/High implementation findings.
NOT_INDEPENDENTLY_AUDITED=true. No managed scan artifacts outside the allowlist.

Pinned metadata remains a match to recorded claims, not fresh authentication of
consolidation bytes, timestamps, allocation ownership, treasury enforceability
or historical consensus. Missing-height issuance, difficulty-policy provenance,
and authenticated canonical continuation remain unresolved. Protocol v1.0.0,
protected economics, original history, historical manifest, canonical validator,
custody and F171 remain unchanged; production gates remain BLOCKED. No mining,
signing, import, network, settlement, merge, push or deployment occurred.

## COMPLETED OFFLINE HISTORICAL POW VERIFIER — 2026-10-22

Status: PASS / ACTUAL CLI VERIFIED / LOCAL COMMIT CANDIDATE
Authorization: `AUTHORIZE_FROZEN_SLICE_L28_OFFLINE_HISTORICAL_POW_VERIFIER_V0_1`
Base: `64d8d3fa52536ce2d0ff4c72bc3e6e2c49eb0442`
Branch: `codex/offline-historical-pow-verifier-v0-1`

The existing historical continuity verifier and CLI now support pinned offline
PoW artifact verification. Manifest-only behavior and its existing tests remain
unchanged. The prior coinbase-strictness slice is complete, not reopened.

Verified with `/Users/pjaydondup/.pyenv/versions/3.11.9/envs/l28-env/bin/python`:

- Focused: `-B -m pytest -q -p no:cacheprovider
  tests/test_historical_continuity_verifier.py
  tests/test_historical_continuity_cli.py -k HistoricalPow` — 10 passed.
- Directly affected existing regressions: same command with
  `-k 'not HistoricalPow'` — 23 passed. Each selection ran once.
- Focused coverage independently exercises exact public preimage/hash binding,
  payload/hash/height/parent/nonce tampering, insufficient declared work, Boolean
  and coerced types, missing fields, selected-record association, duplicate
  keys/records, malformed UTF-8/JSON, nonfinite values, size/count limits,
  nonregular/missing/symlink paths, and false authority flags on failure.
- Seven adversarial artifact CLI subprocess cases returned exit 1; four invalid
  CLI argument combinations returned exit 2. Internal failures were sanitized.
- Actual product command:

```sh
python -B -m coin.historical_continuity_cli \
  --raw-dag /Users/pjaydondup/Documents/L28-Coin/l28_genesis_ledger_old.jsonl \
  --snapshot /Users/pjaydondup/Documents/L28-Coin/l28_ledger_20251225_201521.jsonl \
  --pretty
```

Actual CLI exit: 0, `code=pow_evidence_valid`, evidence-only scope.
Raw: 102263 records, **2202/2202 PoW identifiers verified**.
Snapshot: 72098 records, **817/817 selected PoW identifiers verified**.
`HASH_VALID=true`, `RECORDED_DIFFICULTY_VALID=true`.
Recorded difficulty 4 passes; zero raw PoW hashes meet recovered-source default
12. `source_policy_status=MISMATCH_NOT_CONSENSUS_AUTHORITY` remains visible.
`HISTORICAL_POLICY_AUTHENTICATED=false` / `UNPROVEN`;
`CANONICAL_ACCEPTANCE=false` / `BLOCKED`.

Actual report ID:
`1770505f73167a3011cac7e7fbecfccdffcf5b30af9b254d87efadf07a1f08d8`

Original artifact fingerprints (checked before implementation, used by CLI,
and independently rechecked unchanged after actual-product verification):

- raw: `1ba544052cee098cea265add04c8fb0ff0562897803ba829b201293745aad669`
- snapshot: `6580333e4dba688f242d82a9ea7253369b7723273b3392dc6d8ae9b78d9b2d11`

Final validation: `git diff --check` passed; exactly seven authorized paths
changed and no untracked datasets were present. AST comparison confirmed every
pre-existing manifest-verifier function/class unchanged. Protected paths are
unchanged by exact-path diff inspection.

Consolidated offline manual security review covered all changed behavior:
fixed artifact identities/counts, same-byte hash/parse binding, bounded regular
file reads, strict record parsing, independent PoW recomputation, parent and
selected-record binding, CLI failure semantics, manifest compatibility, and
authority separation. No unresolved Critical/High implementation findings.
This is not independent cryptographic review; no managed scan artifacts were
created outside the approved allowlist. NOT_INDEPENDENTLY_AUDITED=true.

The tool does not authenticate outer economic fields through PoW, recompute
non-PoW identities, establish historical issuance/ownership, or select canonical
history. Source/configuration provenance, the difficulty-4/12 discrepancy,
missing-height issuance evidence and legitimate canonical continuation remain
unresolved. Original datasets stay outside Git; no historical import occurred.
Protocol v1.0.0, protected economics, historical manifest, canonical validator,
F171 and custody are unchanged. Production gates remain BLOCKED. No network,
mining, nonce search, signing, deployment, merge or push was performed.

## PRODUCT DIRECTION
L28 is being built toward a functional machine-to-machine AI payment use case.

North-star flow:

DISCOVER → REQUEST → QUOTE → PAY → WORK → VERIFY → RECEIPT → REUSE

Product path:

1. disposable offline L28 transfer — COMPLETE/PUBLISHED
2. two-agent useful service transaction — COMPLETE/PUBLISHED
3. HTTP/JSON + MCP external access — COMPLETE/PUBLISHED
4. cross-AI interoperability — COMPLETE/PUBLISHED
5. isolated local network — COMPLETE/PUBLISHED
6. limited testnet — PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED
7. public testnet — PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED
8. production entry — durable restart-safe paid AI service — PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED
9. production runtime hardening and fault recovery — PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED
10. isolated non-production signer runtime — PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED
11. disposable custody continuity — restart-stable isolated signer — PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED
12. production custody readiness and signer eligibility — PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED
13. discoverable public-testnet release candidate — PASS / ACTUAL-PRODUCT VERIFIED / LOCAL COMMIT CANDIDATE
14. persistent disposable two-node ledger core — PASS / ACTUAL-PRODUCT VERIFIED / LOCAL COMMIT PENDING
15. Protocol v1 coinbase validator strictness — PASS / ACTUAL-PRODUCT VERIFIED / LOCAL COMMIT CANDIDATE

## REPOSITORY
Local: `/Users/pjaydondup/Projects/L28-Coin`
Remote: `https://github.com/milak7888/L28-Coin.git`
Public: `milak7888/L28-Coin`

Latest independently verified remote `main`:

`cb20eec3110dfa5a26b06736ef8c4e8bc6748482`

Commit:

`Implement isolated local network service transaction`

Parent:

`91297fabd134b196049204f2b4d966f98bd139dc`

Changed paths in that commit:

- `SYSTEM_STATE L28.md`
- `coin/isolated_local_network_service_demo.py`
- `tests/test_isolated_local_network_service_demo.py`
## CANONICAL PROTOCOL
L28 Protocol v1.0.0 is frozen.

Canonical validator:

`coin.tx_validation.validate_transaction`

Core invariants:

- coinbase-only issuance
- no admin/governance/manual/discretionary mint
- canonical height comes from consensus state only
- missing required state fails closed
- no subsystem/operator override of issuance, supply, validation, height, consensus, history, or settlement
- same public validation rules for all

## PROTECTED ECONOMICS
Immutable:

- hard cap: 28,000,000 L28
- emission ceiling: 11,130,000 L28
- historically mined: 2,824,584 L28
- treasury locked: 500,000 L28
- circulating snapshot: 2,324,584 L28
- halving interval: 210,000
- rewards: 28 → 14 → 7 → 3 → 1 → 0
- historical mined-through: 100,877
- next canonical height: 100,878

Historical ledger/allocation/wallet/genesis/hash/snapshot/supply records are immutable.

Disposable test state is never canonical history.

## WORKING CAPABILITY — DISPOSABLE OFFLINE TRANSFER
Published capability:

`python -m coin.disposable_offline_transfer_demo`

Verified behavior:

- creates disposable in-memory Ed25519 participants
- Alice begins with 100 disposable L28
- Bob begins with 0 disposable L28
- signs a 28 L28 transfer
- calls `coin.tx_validation.validate_transaction`
- applies state through `BlocklessLedger.add_transaction`
- Alice becomes 72
- Bob becomes 28
- invalid signature rejected
- replay rejected
- insufficient balance rejected
- malformed amount rejected
- rejected transfers do not mutate disposable balances
- issued supply remains untouched
- canonical history remains untouched
- no public network is used
- no production keys are used

Automated verification for that slice:

- focused disposable-transfer tests: 10 passed
- protocol conformance: 42 passed

Slice result:

PASS and published to remote `main`.

## WORKING CAPABILITY — TWO-AGENT USEFUL SERVICE TRANSACTION
Published capability:

`python -m coin.two_agent_service_transaction_demo --input "L28 enables machine payments between autonomous systems."`

Service:

`structured_text_analysis`

Verified end-to-end behavior:

- Agent A creates a signed service request
- Agent B creates a signed quote for exactly 28 L28
- Agent A creates an actual disposable signed L28 payment
- payment passes the canonical validation path
- payment executes through the existing disposable ledger path
- Agent A balance changes 100 → 72
- Agent B balance changes 0 → 28
- Agent B independently verifies request/quote/payment/party/amount binding
- useful work executes only after successful payment verification
- deterministic structured-text result is returned and independently verifiable
- signed machine-readable receipt is produced and verifies using public material
- invalid signature/replay/wrong amount/wrong party/quote mismatch fail closed
- failed payment does not execute work
- tampered result/receipt fail closed
- canonical history remains untouched
- protected economics remain unchanged
- no production keys are used

Automated verification:

- focused two-agent transaction tests: 10 passed
- affected regressions: 52 passed

Published commit:

`90d6ec4b16c44f30f69d6cd7d90c9238fb3aa2e7`

Slice result:

PASS and published to remote `main`.

## WORKING CAPABILITY — HTTP/JSON + MCP EXTERNAL ACCESS
Published capability:

`python -m coin.two_agent_service_external_access_demo --input "L28 enables machine payments between autonomous systems."`

Service:

`l28.service.structured_text_analysis/v0.1`

Verified HTTP/JSON behavior:

- real local HTTP runtime exists
- hard-bound to `127.0.0.1`
- purchase endpoint:
  `POST /v1/l28/services/structured_text_analysis/purchase`
- separate local caller crosses the actual loopback HTTP runtime boundary
- successful purchase returns HTTP 200
- 28 L28 payment semantics are preserved
- useful work and signed receipt are verified
- malformed/unsupported input fails closed

Verified MCP behavior:

- real local MCP runtime exists as a separate process
- transport is stdio only
- purchased-service tool:
  `l28_purchase_structured_text_analysis`
- separate caller crosses the actual MCP stdio runtime boundary
- same 28 L28 purchase semantics are preserved
- useful work and signed receipt are verified
- malformed/unsupported protocol/tool input fails closed
- MCP creates no network listener

Shared verified behavior:

- both transports delegate to the same two-agent transaction core
- no duplicate payment validator
- no duplicate payment engine
- disposable balance semantics remain `100/0 → 72/28`
- stable service/payment semantics are equivalent
- canonical history remains untouched
- no production keys
- no production settlement

Automated verification:

- focused HTTP/MCP tests: 11 passed
- affected regressions: 27 passed

Published commit:

`4016cd180643c515865438575ad603d60b54c6e2`

Slice result:

PASS and published to remote `main`.

## WORKING CAPABILITY — CROSS-AI INTEROPERABILITY
Published capability:

`python -m coin.cross_ai_interoperability_demo --input "L28 enables machine payments between autonomous systems."`

This capability proves provider-format interoperability using two distinct AI-provider request shapes while preserving one L28 purchase core.

### OpenAI-Compatible Path

Verified behavior:

- accepts an OpenAI-compatible function/tool-call shape
- tool name:
  `l28_purchase_structured_text_analysis`
- provider request id is preserved in evidence
- adapter validates bounded JSON arguments
- delegates through the existing real HTTP/JSON L28 runtime
- does not call the two-agent core directly
- receives exactly 28 L28 quote semantics
- payment is applied and verified
- useful service executes
- result and signed receipt verify

Actual-product evidence:

- `openai_compatible_call=true`
- `openai_provider_request_id=call_001`
- `openai_transport=http_json`
- `openai_external_call=true`
- `openai_purchase_verified=true`
- `openai_quoted_amount=28`
- `openai_payment_verified=true`
- `openai_service_executed=true`
- `openai_receipt_verified=true`

### Anthropic-Compatible Path

Verified behavior:

- accepts an Anthropic-compatible `tool_use` shape
- tool name:
  `l28_purchase_structured_text_analysis`
- provider request id is preserved in evidence
- adapter validates bounded input
- delegates through the existing real MCP stdio L28 runtime
- does not call the two-agent core directly
- receives exactly 28 L28 quote semantics
- payment is applied and verified
- useful service executes
- result and signed receipt verify

Actual-product evidence:

- `anthropic_compatible_call=true`
- `anthropic_provider_request_id=toolu_001`
- `anthropic_transport=mcp_stdio`
- `anthropic_external_call=true`
- `anthropic_purchase_verified=true`
- `anthropic_quoted_amount=28`
- `anthropic_payment_verified=true`
- `anthropic_service_executed=true`
- `anthropic_receipt_verified=true`

### Cross-Provider Equivalence

Verified:

- both paths purchase the same L28 service
- both preserve price = 28 L28
- both preserve the same canonical validation/payment semantics
- both preserve `100/0 → 72/28`
- deterministic service output is equivalent for the same input
- both verify result and signed receipt
- `same_l28_service=true`
- `same_l28_core_transaction=true`
- `stable_semantics_equivalent=true`
- `service_output_equivalent=true`
- `canonical_history_touched=false`
- `public_network_used=false`
- `live_provider_api_used=false`
- `provider_credentials_used=false`
- `provider_billing_used=false`
- `production_keys_used=false`
- `production_settlement=false`

Important boundary:

This slice proves OpenAI-compatible and Anthropic-compatible request-format interoperability only.

It does NOT claim that live OpenAI or Anthropic commercial APIs/models were contacted.

No live provider API, provider credentials/API keys, or provider billing/spending were used.

Automated verification:

- focused cross-AI tests: 10 passed
- affected regressions: 38 passed

Actual-product verification:

- OpenAI-compatible path: PASS
- Anthropic-compatible path: PASS
- cross-provider semantic equivalence: PASS
- observable evidence: PASS

Consolidated security review:

- OpenAI path reuses existing HTTP runtime: PASS
- Anthropic path reuses existing MCP runtime: PASS
- caller amount override: rejected
- direct core bypass: false
- duplicate payment validator: false
- live provider API used: false
- provider credential access: false
- unresolved Critical/High findings: 0

Published commit:

`b64dad0dbc14c7a5732fcc1b9ff34079152b38b2`

Slice result:

PASS and published to remote `main`.

The Cross-AI Interoperability frozen slice has reached its STOP condition.

## EXISTING INTEROPERABILITY / M2M FOUNDATION
Existing repository surfaces include:

- M2M message/profile work
- service request/quote/payment authorization/settlement reference/service receipt concepts
- UAII / universal AI access
- REST/OpenAPI work
- MCP work
- Python SDK
- TypeScript SDK
- quote/payment/receipt validation surfaces
- canonical JSON rules
- signed-receipt primitives
- transaction-validation delegation to the canonical validator

Known UAII operations include:

- `discover_capabilities`
- `get_protocol_status`
- `get_balance`
- `create_quote`
- `create_unsigned_payment_request`
- `validate_payment`
- `get_payment_receipt`
- `verify_signed_receipt`

## CURRENT PRODUCTION SIGNER / CUSTODY STATE
Production signer/custody remains unresolved.

Recorded production-level restrictions remain:

- `CUSTODY_READINESS=UNRESOLVED`
- `RUNTIME_HARDENING=UNRESOLVED`
- `FAULT_RECOVERY=UNRESOLVED`
- `F171_SIGNER_ELIGIBILITY_RESULT=BLOCKED`
- `SIGNER_RUNTIME_ACTIVE=false`
- `BROADCAST=false`
- production `SETTLEMENT=false`

The completed disposable, two-agent, HTTP/MCP, cross-AI, testnet, and restart-safe payment capabilities do NOT make a production signer eligible.

The disposable restart-safe runtime and the later hardening slice do not change these production gates. `RUNTIME_HARDENING` and `FAULT_RECOVERY` remain UNRESOLVED.

## ASSURANCE MODEL
`ASSURANCE_MODEL=OPEN_SOURCE_PUBLIC_REVIEW`

`NOT_INDEPENDENTLY_AUDITED=true`

No paid or independent audit is claimed for the completed slices.

Known Critical/High findings involving secret exposure, unauthorized signing, Protocol bypass, arbitrary minting, supply/history mutation, validation bypass, or unauthorized production settlement block the affected capability.

## BITCOIN
Bitcoin is external evidence only.

Bitcoin has zero authority over L28 issuance, supply, canonical height, validation, consensus, history, or settlement.

Observation ≠ settlement.

## WORKING CAPABILITY — ISOLATED LOCAL NETWORK
Published capability:

`python -m coin.isolated_local_network_service_demo --input "L28 enables machine payments between autonomous systems."`

Service:

`l28.service.structured_text_analysis/v0.1`

Verified:

- exactly two child agent processes
- IPv4 TCP loopback only on `127.0.0.1`
- request, 28 L28 quote, payment, result, and receipt cross TCP
- canonical validator reused
- `BlocklessLedger` reused
- balances transition 100/0 → 72/28
- work executes only after verified payment
- Agent A verifies result and receipt
- both processes terminate and sockets close
- canonical history untouched
- no public network
- no production keys
- no production settlement

Automated verification:

- focused tests: 10 passed
- affected regressions: 41 passed

Actual-product verification: PASS

Security review: PASS

Unresolved Critical/High findings: 0

Published commit:

`cb20eec3110dfa5a26b06736ef8c4e8bc6748482`

Slice result:

PASS and published to remote `main`.

## WORKING CAPABILITY — LIMITED TESTNET
Verified capability:

`python -m coin.limited_testnet_service_demo --role provider --requester-host 192.168.1.129 --provider-host 192.168.1.138 --port 28428`

`python -m coin.limited_testnet_service_demo --role requester --requester-host 192.168.1.129 --provider-host 192.168.1.138 --port 28428`

Service:

`l28.service.structured_text_analysis/v0.1`

Network identity:

`L28-DISPOSABLE-LIMITED001`

Verified two-host behavior:

- requester `192.168.1.129`
- provider `192.168.1.138:28428`
- distinct explicit RFC1918 endpoints
- signed request, quote for exactly 28 L28, disposable payment, result, and receipt
- canonical validator reused
- `BlocklessLedger` reused
- payment tx id `cf1e700befd46e413218af74120f1edbb3140c11a830b0078ca8d52d5881a537`
- balances transition 100/0 → 72/28
- requester verified the result and the receipt
- duplicate payment rejected with `reason=replay`
- original payment remained applied exactly once
- balances remained 72/28 after replay rejection
- canonical history untouched
- historical state not imported
- no public network
- no production keys
- no mining
- no broadcast
- no production settlement
- sockets closed

Automated verification:

- focused tests: 9 passed
- affected regressions: 52 passed

Actual-product verification: PASS

Security review: PASS

Unresolved Critical/High findings: 0

Identity-module flags `RUNTIME_AUTHORIZED`, `NETWORK_AUTHORIZED`, `TESTNET_START_AUTHORIZED`, `SIGNING_AUTHORIZED`, `MINING_AUTHORIZED`, `BROADCAST_AUTHORIZED`, and `SETTLEMENT_AUTHORIZED` stay false.

Slice result:

PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED

The Limited Testnet frozen slice reached its STOP condition and is published on remote main at commit `586362ef17138e8e82ddfa4ac954e3f54d33ea9d`.

## WORKING CAPABILITY — PUBLIC TESTNET
Verified capability:

`python -m coin.public_testnet_service_demo --role provider --port 28429`

Service:

`l28.service.structured_text_analysis/v0.1`

Network identity:

`L28-DISPOSABLE-PUBLIC001`

Verified public path:

- Surface requester on a separate internet connection
- public endpoint `https://remaining-successful-springs-new.trycloudflare.com`
- ephemeral Cloudflare Quick Tunnel
- Mac provider bound only to `127.0.0.1:28429`

Provider evidence:

- `coordination=provider_evidence`
- `public_testnet=true`
- `canonical_validation=PASS`
- payment tx id `c95bbee5d1e9b5d8dadf66db319099f2930bd7edc624335f3a0f4e2beec579d2`
- balances 100/0 → 72/28
- `payment_applied=true`
- `payment_verified=true`
- `replay_rejected=true`
- `service_executed=true`
- `receipt_created=true`
- `bounded_provider_shutdown=true`
- canonical history untouched
- historical state not imported
- no production keys
- no mining
- no canonical broadcast
- no production settlement

The Surface requester completed the same public HTTPS transaction and showed the same payment tx id. That command completes only after the existing quote, payment, result, and receipt verification flow.

Automated verification after the provider-evidence change:

- focused tests: 7 passed
- affected regressions: 72 passed

Actual-product verification: PASS

Security review: PASS

Unresolved Critical/High findings: 0

Identity-module authorization flags stay false. Protocol v1.0.0 and protected economics are unchanged.

Slice result:

PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED

The Public Testnet frozen slice reached its STOP condition and is published on remote main at commit `3fa23117aafbc1ee78c7bec0e52259008a2783ff`.

## COMPLETED DURABLE RUNTIME SLICE
The Production Entry — Durable Restart-Safe Paid AI Service slice reached its STOP condition and is published on remote main at commit `c0f5467bb2f58a2f59a47cbc2920dcb2e5b3f1a6`.

## COMPLETED HARDENING SLICE
The Production Runtime Hardening / Fault Recovery slice reached its STOP condition and is published on remote main at commit `02974da1c300f18f293980c6fec035f553e87c1f`.

## CURRENT FROZEN SLICE
`FROZEN_SLICE L28.md`

**Protocol v1 Coinbase Validator Strictness v0.1**

Status: PASS / ACTUAL-PRODUCT VERIFIED / LOCAL COMMIT CANDIDATE

Baseline: `3ff8bbaff1055f406fcd3ae768c3a339df64e4d2`

Branch: `codex/protocol-v1-coinbase-validator-strictness-v0-1`

Operator amendment:
`AUTHORIZE_L28_COINBASE_STRICTNESS_LEDGER_SCOPE_AMENDMENT_V0_1`

The canonical validator now requires exact coinbase identity, an explicit
nonempty string miner matching the receiver, and nonnegative exact-integer
issued supply. The ledger passes raw supply to canonical validation, including
`None` for an absent attribute, and no longer converts invalid state into a
valid-looking integer. Validated replay also passes its raw supply accumulator.
Rejection occurs before the ledger's persistence and balance/index updates.

Verification on 2026-10-22, using
`/Users/pjaydondup/.pyenv/versions/3.11.9/envs/l28-env/bin/python`:

- `-B -m pytest -q -p no:cacheprovider tests/test_protocol_conformance.py`:
  49 passed, including 16 empty/funded-ledger invalid-supply subcases;
- `-B -m pytest -q -p no:cacheprovider tests/test_uaii_reference_core.py`:
  22 passed;
- both suites ran once after the correction;
- actual product: a standalone `python -B -` process exercised the real
  `BlocklessLedger.add_transaction` and validated `load_from_disk` paths in
  temporary directories; no keys, signing, mining, or sockets were used;
- `True`, `False`, `0.0`, `"0"`, `-1`, missing, and null supply each rejected
  with `issued_supply_unavailable` after one valid persisted disposable event;
- all rejected cases preserved supply value/type/absence, balances, height,
  transaction count/volume, indexes, shards, readiness, and persisted bytes;
- the existing event's SHA-256 stayed
  `9c343f472dbfd0158895898f0fd53507ce533007f2ba1b4aa640682d55dbbafc`
  in every invalid-supply product case;
- malformed coinbase identity and absent miner also rejected without mutation;
- valid disposable coinbase
  `d885dcd2666754d094078fa402b2fbb6b0f9b8e834d137703ea492d8683a8526`
  produced balance/supply `28/28`, height `1`, reloaded identically, and rejected
  replay without mutation;
- temporary ledgers were removed after verification;
- AST comparison against the baseline confirmed unchanged economic/historical
  constants, reward schedule, strict integer parser, and transaction identity;
- `git diff --check`: PASS.

Consolidated source/security review: PASS. The previously confirmed ledger
coercion and partial-mutation defect no longer reproduces. No unresolved
Critical/High implementation findings in this slice. This is an engineering
review, not an independent cryptographic or production-security approval.
Networked/signing demos were not run; the bounded ledger, validated replay,
protocol, and UAII paths above are the verification scope.

Protocol v1.0.0, economics, historical records, F171, and custody gates are
unchanged. `CUSTODY_READINESS=UNRESOLVED`,
`F171_SIGNER_ELIGIBILITY_RESULT=BLOCKED`, and `SIGNER_RUNTIME_ACTIVE=false`.
The historical-manifest correction was not started. This slice stops at one
local commit; merge, push, deployment, and production activation remain
unauthorized.

## PRIOR PERSISTENT DISPOSABLE TWO-NODE SLICE

Slice:

**Persistent Disposable Two-Node Ledger Core v0.1**

Status:

PASS / ACTUAL-PRODUCT VERIFIED / LOCAL COMMIT PENDING

Baseline:

`1ed38b5ac44015e87517d321cc2d56ca9021a384`

Branch:

`codex/persistent-disposable-two-node-core-v0-1`

Two separate local node processes now use the existing canonical transaction
validator and `BlocklessLedger` to validate and persist the same disposable
events over IPv4 loopback. The writer creates one test-only 28 L28 coinbase at
height zero and one ephemeral-key signed 28 L28 transfer. The follower
independently validates and persists both events.

Actual local product command:

`python -B -m coin.persistent_disposable_testnet_node`

Verified result:

- network `L28-DISPOSABLE-PERSISTENT001`;
- genesis hash `5284cbdc2ae6041735375dd7f4c5888c79c539c79a0e7279d7e359ffcd305c0d`;
- config hash `abf1e128de2883c24a86163dc4dfeceee89d24274559293ef7b0a8fc72bd8d7d`;
- two independent validators agreed on two event IDs;
- balances converged to disposable `0/28` with issued supply `28` and mint
  height `1`;
- final state commitment `9105d2ebc3e457e35efa5e59aebb5dd58cef82002218300b2175e184b7508675`;
- both nodes stopped and restarted from strict validated durable replay;
- replay after restart, truncated persistence, malformed input, and
  cross-network input rejected;
- divergent state invoked `OPTION_A_HALT_ON_CONFLICT` without mutation;
- all node processes terminated and temporary private material did not persist;
- canonical history untouched; no mining, broadcast, public network, production
  key, or production settlement.

Automated verification:

- focused and adversarial tests: 10 passed;
- directly affected regressions: 186 passed;
- final post-review ledger regressions: 42 passed;
- actual-product CLI: PASS;
- `git diff --check`: PASS.

Consolidated security review: PASS with complete changed-source coverage and
zero reportable findings. Unresolved Critical/High implementation findings: 0.
Three non-reportable exactness gaps found during review were corrected before
the final focused tests and actual-product run: boolean frame scalar
substitution, blank durable records, and unexpected shard files now reject.

This result is a local non-production ledger-foundation experiment only. It
does not define confirmations, fork choice, finality, consensus, canonical
history continuation, peer discovery, or a public endpoint.

EVD-001 is not integrated. Protocol v1.0.0, protected economics, canonical
history, custody gates, and F171 are unchanged.

`CUSTODY_READINESS=UNRESOLVED`

`F171_SIGNER_ELIGIBILITY_RESULT=BLOCKED`

`SIGNER_RUNTIME_ACTIVE=false`

Signing, canonical broadcast, mining, and production settlement stay false.

## PRIOR PRODUCTION CUSTODY READINESS SLICE

Slice:

**Production Custody Readiness and Signer Eligibility**

Status:

PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED

The Production Custody Readiness and Signer Eligibility slice reached its STOP condition and is published on remote main at commit `36c07394558a29f795ce899dc34ec710cb669a13`.

Baseline:

`fd0dd7174385a3d308a25822f8073b9aa0aae871`

A live disposable custody directory was assessed from its public record while the private-key file was absent. Public identity `l28disp_b0f34efeb88c5e6b5ce8442a155012855c974e1a295ea2bd6a21c1b5bbec4fad` was reported. The existing custody evaluator returned `BLOCKED_BY_UNRESOLVED_CUSTODY_DECISIONS`. The existing signer-eligibility reassessment returned `GATE_READINESS_BLOCKED`.

Claiming an unresolved custody decision was RESOLVED was rejected. A signer process asked for production eligibility exited before opening custody. The disposable signer still started with the same public identity.

Focused tests: 6 passed. Affected regressions: 67 passed.

Security review: PASS. Unresolved Critical/High findings: 0.

This does not resolve production custody or signer eligibility.

`CUSTODY_READINESS=UNRESOLVED`

`RUNTIME_HARDENING=UNRESOLVED`

`FAULT_RECOVERY=UNRESOLVED`

`F171_SIGNER_ELIGIBILITY_RESULT=BLOCKED`

`SIGNER_RUNTIME_ACTIVE=false`

Signing, canonical broadcast, mining, and production settlement stay false.

## COMPLETED CUSTODY CONTINUITY SLICE
`FROZEN_SLICE L28.md`

Slice:

**Disposable Custody Continuity — Restart-Stable Isolated Signer**

Status:

PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED

The Disposable Custody Continuity — Restart-Stable Isolated Signer slice reached its STOP condition and is published on remote main at commit `522d181da436a0d936eee7b0e4d8e2e7389f51f6`.

Baseline:

`16da76b59593d0505b18f9eb89e3c37c9258a4ed`

Profile: `L28-DISPOSABLE-CUSTODY-CONTINUITY001`

A real signer process initialized disposable custody, signed as identity `l28disp_adbe504225163cbd10d6ca2e3416a0f94de3a1f8e92b928c7598c973d1917a3e`, and completed payment `b1cdee2cec21cae9bf1e44d2aa5710079463d6d25c4a19c6a82271c93c94bbd4`. Canonical validation passed. Balances moved 100/0 to 72/28. The result and receipt verified.

That signer process stopped. A new signer process reopened the same custody directory and presented the same identity. Replay of the original payment was rejected. Balances stayed 72/28. The service did not run again.

Fresh payment `54ec2457814cfd717250764ebf70c85ce24ff3970934f355fa27565cfcd9284b` paid that same identity, moving balances 72/28 to 44/56. The result and receipt verified.

Separate disposable copies rejected truncated custody (`custody_corrupt`), an unexpected identity replacement (`custody_replaced`), a group-readable key file (`permissions_invalid`), and a group-accessible custody directory (`permissions_invalid`) before signing. The successful custody directory was not modified by those probes.

The private key was not present in stdout, stderr, or the evidence object. Canonical history was not touched.

Focused tests: 11 passed. Affected regressions: 73 passed.

Security review: PASS. Unresolved Critical/High findings: 0.

This does not resolve production custody. The on-disk integrity record is owner-only test metadata, not a production custody claim.

`CUSTODY_READINESS=UNRESOLVED`

`RUNTIME_HARDENING=UNRESOLVED`

`FAULT_RECOVERY=UNRESOLVED`

`F171_SIGNER_ELIGIBILITY_RESULT=BLOCKED`

`SIGNER_RUNTIME_ACTIVE=false`

Signing, canonical broadcast, mining, and production settlement stay false.

## COMPLETED ISOLATED SIGNER SLICE
`FROZEN_SLICE L28.md`

Slice:

**Isolated Non-Production Signer Runtime**

Status:

PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED

The Isolated Non-Production Signer Runtime slice reached its STOP condition and is published on remote main at commit `ce8a5e37248d7b823c055c53274b49fd68d2080b`.

Baseline:

`6dc5c4bbdf33ee94a952afdc7301ff10192bac1c`

A separate localhost process holds one disposable signing key. The payment process has no signing key. It still uses canonical validation and the durable exactly-once store.

Run 1 payment `eab61398b14764be20044ac4f0c32a8d4f1b1da60626d2f79c73b808061557c5` moved balances 100/0 to 72/28. The result and receipt verified.

The payment process stopped and restarted against the same signer and the same state directory. Replay of that payment was rejected. Balances stayed 72/28.

Run 3 payment `844b6e882adc77846ee2deb2fbb0b093e68c1610625d9edde46a7bc467eea877` paid the same signer identity, moving that provider balance from 28 to 56 and the requester from 72 to 44.

The signer process did not write the key. Production signer gates stayed closed.

Focused tests: 3 passed. Affected regressions: 103 passed.

Security review: PASS. Unresolved Critical/High findings: 0.

`CUSTODY_READINESS=UNRESOLVED`

`RUNTIME_HARDENING=UNRESOLVED`

`FAULT_RECOVERY=UNRESOLVED`

`F171_SIGNER_ELIGIBILITY_RESULT=BLOCKED`

`SIGNER_RUNTIME_ACTIVE=false`

Signing, canonical broadcast, mining, and production settlement stay false.

## PRIOR HARDENING SLICE
Slice:

**Production Runtime Hardening and Fault Recovery**

Status:

PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED

The Production Runtime Hardening / Fault Recovery slice reached its STOP condition and is published on remote main at commit `02974da1c300f18f293980c6fec035f553e87c1f`.

Baseline:

`b3c5dd1f0321e07c12ac874311b47d912ff7e9e4`

The disposable payment runtime now rejects a world-readable state file, a group-accessible state directory, a rolled-back database inside the same directory, a corrupt audit chain, an older payment timestamp, and an over-nested request. A real process still completes the 28 L28 purchase, rejects the replay after restart, and completes a second fresh payment.

Run 1 payment `103c4f35033ba784488b2b9e1b81dcff4415ef621cf7054b1444f1bf0e1024dd` moved balances 100/0 to 72/28.

Run 2 rejected that same payment. Balances stayed 72/28.

Run 3 payment `3c8cf49e8f6e7efa59d95872eda0e738ecffcb241f21c5cb2a962950ec8c4650` completed. The original provider balance stayed 28.

Real process probes rejected `permissions_invalid`, `stale_state`, and `corrupt_state` before any service execution.

Focused tests: 13 passed. Affected regressions: 116 passed.

Security review: PASS. Unresolved Critical/High findings: 0.

This does not resolve the production signer gates. Replacing every file in the state directory together is still outside this slice. No production rate, skew, or topology values were invented.

`CUSTODY_READINESS=UNRESOLVED`

`RUNTIME_HARDENING=UNRESOLVED`

`FAULT_RECOVERY=UNRESOLVED`

`F171_SIGNER_ELIGIBILITY_RESULT=BLOCKED`

`SIGNER_RUNTIME_ACTIVE=false`

Signing, canonical broadcast, mining, and production settlement stay false.

## DURABLE RUNTIME EVIDENCE
Slice:

**Production Entry — Durable Restart-Safe Paid AI Service**

Status:

PASS / ACTUAL-PRODUCT VERIFIED / PUBLISHED

The Production Entry — Durable Restart-Safe Paid AI Service slice reached its STOP condition and is published on remote main at commit `c0f5467bb2f58a2f59a47cbc2920dcb2e5b3f1a6`.

Baseline:

`d3f533b5b4e1b60d9f96ba925d08699fc247ae2d`

A real provider process completed one disposable 28 L28 purchase, stopped, and restarted on the same state directory. The original payment was rejected as a replay. A second fresh disposable payment then completed.

Run 1 payment `896222f3a3e07752e91ad9dd1b2f1edec4897b15e8b19505b6eebbad5e939b1e` moved balances 100/0 to 72/28. Canonical validation passed. The result and receipt verified. Durable state version became 1.

Run 2 reopened that state at restart generation 2. The same payment was rejected. Balances stayed 72/28. The service did not run again.

Run 3 payment `5a008e8e2ee662c2f9079a19e7fccb0700438d8a45e2369ecab9a354f15d08ad` moved the same requester from 72 to 44 and a new disposable provider from 0 to 28. The original provider balance stayed 28. The result and receipt verified.

Focused tests: 10 passed. Affected regressions: 58 passed.

Security review: PASS. Unresolved Critical/High findings: 0.

This is local disposable runtime evidence. It is not canonical settlement finality.

`CUSTODY_READINESS=UNRESOLVED`

`RUNTIME_HARDENING=UNRESOLVED`

`FAULT_RECOVERY=UNRESOLVED`

`F171_SIGNER_ELIGIBILITY_RESULT=BLOCKED`

`SIGNER_RUNTIME_ACTIVE=false`

Signing, canonical broadcast, mining, and production settlement stay false.

## NEXT AFTER THIS SLICE
**Production signing, deployment, and settlement**

Status:

NOT AUTHORIZED / NOT STARTED

Do not automatically start production signer/custody, deployment, exchange/listing/liquidity, or REA/Bitcoin/BTCPay work.

## SOURCE-OF-TRUTH RULE
This file records current verified project state.

Update after every completed frozen slice.

Repository/files are authoritative.

Do not treat chat memory as authoritative implementation state.
