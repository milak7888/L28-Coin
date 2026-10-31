# L28 Coin

L28 is a public machine-to-machine settlement protocol designed for software,
devices, autonomous systems, and AI agents. It is independent from the private
Leap28 orchestration system and may be implemented or self-hosted under the
Apache License 2.0.

## Configurable two-network disposable peers (offline candidate)

The existing two-host coordinator now accepts explicitly configured, distinct
private IPv4 peer addresses and an unprivileged TCP port. It reuses the same
canonical transaction validator, ledger, pairing, pinned TLS handoff and HMAC
frames; no discovery, relay or new consensus mechanism is added. The accepted
LAN defaults and separate loopback workflow are retained. This is NOT native
mainnet settlement, historical continuation or a production custody release.

Physical cross-network acceptance is **PENDING**. No listener, route/VPN change,
firewall change or physical session is authorized by the offline candidate.
Private IP syntax does not prove encryption, host ownership or different access
networks. Before any future execution the operator must approve the exact peers,
an existing encrypted private route covering the entire connection (including
the PUBLIC pre-authentication pairing exchange and later HMAC ledger frames),
source parity, narrow firewall boundary and one bounded session. The HMAC ledger
transport itself is authenticated but **not encrypted**. No automatic public
fallback, DNS discovery or unauthenticated certificate trust is permitted.

With Python 3.11, cryptography 49.0.0 and pyOpenSSL 26.4.0 already available, this
command exercises the actual configurable TLS/HMAC/ledger path entirely offline
over in-memory byte pipes, including durable reopen and rejection probes:

```sh
python -B -m coin.persistent_disposable_testnet_node --offline-coordinator \
  --peer-writer-ip 10.28.1.10 --peer-follower-ip 100.77.2.20 \
  --peer-port 42828 --ack-encrypted-private-route
```

These are example addresses, NOT approved physical endpoints. The acknowledgment
is a required local assertion, not proof of encryption or execution permission.
Require exit zero, OFFLINE_COORDINATOR_PASS, supply 28, balances 0/28, agreement,
replay rejection, divergence halt and cleanup. Physical and encrypted-route
verification flags remain false. Add `--coordinator-case wrong-peer`, `wrong-pin`,
`source-mismatch`, `interrupted` or `tamper` to require nonzero rejection.

`--source-inventory` prints the public runtime digest. `--runtime-check
--expected-source-digest DIGEST` with the same peer arguments verifies the native
runtime/configuration without networking. Both physical hosts must independently
report identical source digests and peer configuration before a session.

After separate physical authorization, `--print-launcher --launcher-platform mac
--role writer` (or `windows --role follower`), `--expected-source-digest DIGEST`
and those same four peer/route arguments **print**, but do not execute, the existing
native initial/restart/cleanup launch procedure. Generate the launcher locally on
each host so repository/Python paths are native. Do not execute the printed script
before authorization; the Windows template includes a temporary Private-profile
firewall rule restricted to the exact configured local/remote IPs and port.

Each phase requires direct physical comparison of the complete role-ordered
SHA-256 fingerprints and local PAIR approval on both hosts: one initial comparison,
another after genuine process restart. Hosts can be physically beside each other
while using different access networks. If direct physical comparison is unavailable,
STOP until the operator approves a trusted comparison method; this candidate does
not silently authorize remote enrollment. A network echo or chat from an
unauthenticated peer is not a trusted comparison channel.
Private TLS/payment credentials remain memory-only; restart generates fresh
identities and cannot change the peers, source digest, session START or stored
ledger identity. Certificates retain their expiration, active runtime is at most
120 seconds and the original network session is at most 600 seconds across restart.
Failure ends the attempt; owned handles/processes and any separately approved
firewall rule must be cleaned up. No automatic retry or canonical history rewrite.

The existing public-testnet v0.1.0-rc1 inventory remains pinned to the accepted
baseline, not this changed working-tree README. This candidate is not a new release
package; its physical source synchronization/publication needs separate approval.

## Current status

- Protocol specification: frozen at v1.0.0
- Protocol and source: available
- Former hosted L28 server: offline
- Leap28-operated always-on public network: not currently running
- Local and independently operated implementations: supported by the public protocol boundary
- Automatic mining or distribution: not started merely by cloning or importing the code

L28 being available does not mean Leap28 controls it. Leap28 may interact only
through the same public transaction, ledger, consensus-height, reward, and work
validation interfaces available to other implementations.

## Canonical economic record

| Fact | Preserved value |
|---|---:|
| Protocol hard cap | 28,000,000 L28 |
| Emission schedule ceiling | 11,130,000 L28 |
| Historically mined | 2,824,584 L28 |
| Treasury locked | 500,000 L28 |
| Circulating at the recorded snapshot | 2,324,584 L28 |
| Halving interval | 210,000 |
| Reward sequence | 28 → 14 → 7 → 3 → 1 → 0 |

The historical allocation checkpoint records 2,824,584 L28 mined through entry
100,877. Bootstrap or test execution must never mint that historical amount a
second time.

## Protocol boundary

See [PROTOCOL.md](PROTOCOL.md) for the normative v1.0.0 rules. In particular:

- coinbase is the only issuance mechanism;
- canonical height comes from consensus state;
- missing required state fails closed;
- issued supply never exceeds 28,000,000 L28;
- Leap28 cannot inject mint events, override supply, or bypass validation.

## Relationship to Leap28

Historical Ledger Proof
        ↓
Genesis Bootstrap
        ↓
genesis_state.json
        ↓
BlocklessLedger Runtime
        ↓
Mining + Transactions
        ↓
L28 M2M Settlement Layer
        ↓
Leap28 Autonomous AI Economy

Leap28 supplies decision-making and policy. L28 supplies independently
verifiable settlement. Either system can exist without embedding the other.

## Community validation

L28 includes deterministic offline public validation tooling.

Run the canonical-integrity check:

`PYTHON=python3 tools/uaii_community_conformance.sh integrity-only`

Run the full UAII cross-adapter conformance suite:

`PYTHON=python3 tools/uaii_community_conformance.sh full`

See the published deterministic
[UAII conformance report](reports/uaii_conformance_report_v0.1.md).

A conformance PASS is evidence of deterministic public-interface behavior.
It is not production security certification, deployment authorization,
testnet activation, signer authorization, or settlement authorization.

## Non-production public-testnet release candidate

`l28-public-testnet-v0.1.0-rc1` packages the existing disposable 28 L28
one-shot service with machine-readable discovery and a local executable
provider/requester example. It is explicitly a NON-PRODUCTION DISPOSABLE
TESTNET candidate; no public endpoint is configured or authorized by this
repository change.

Run the actual local HTTP/JSON product path:

```sh
python -m coin.public_testnet_service_demo \
  --role local-example \
  --input "L28 enables machine payments between autonomous systems."
```

See the [public-testnet v0.1 release guide](docs/public_testnet_release_v0.1.md)
for discovery, requester, local-only MCP, manifest, exposure-boundary, and
rollback instructions.

## Persistent disposable two-node ledger core

The local persistent-node candidate runs one disposable writer and one
independently validating follower as separate processes over IPv4 loopback.
Both use `coin.tx_validation.validate_transaction` and `BlocklessLedger` for
the same test-only 28 L28 coinbase and signed 28 L28 transfer. They then stop,
restart from validated durable event logs, compare deterministic public state
commitments, and reject replay, corruption, cross-network input, malformed
frames, and divergent state.

Run the actual bounded product path:

```sh
python -B -m coin.persistent_disposable_testnet_node
```

The command uses temporary directories and an ephemeral disposable signing
key that is never persisted or printed. This is not mining, consensus,
confirmation, canonical-history continuation, public networking, production
signing, broadcast, or settlement.

### Bounded Mac/Surface coordinator — accepted disposable physical experiment

Physical acceptance PASS, finalized under operator authorization on 2026-10-30.
Session `a649173ab9cdf2a4e432cdb284027e90` completed initial transfer and genuine
process restart on Mac and Surface with source digest below, supply 28, balances
0/28 and matching commitment
`98056ec92a23fc0186ef51c39c0ae6d0acf224f692c4ccfd510fa93f55547964`.
Mac reports were inspected; Surface results, physical separation/fingerprint
comparison and Windows cleanup are operator-attested. Replay rejects, terminal
divergence halt and both-host cleanup passed. See SYSTEM_STATE for report hashes,
transaction IDs, evidence qualifications and unchanged production blocks.

`physical_two_host_verified=false` is hardcoded even for the physical LAN path:
the executable does not independently attest physical topology. It does not
negate the successful transaction checks. The operator's physical attestation
supplements machine evidence; no independent security audit is claimed.
PROJECT_STATE remains ACTIVE. This accepted session is terminal; do not reuse it.
Launch procedures below describe the implementation, not authorization for a new
session. Finalization permits only completion records and one local commit.

#### Automatic pairing workflow — retained for separately authorized reproduction

Use `--paired-coordinate`, through the generated native-shell launcher, for the
separately authorized physical experiment. Older `--coordinate`/VERIFIED
JSON procedures below are compatibility/history, not the current launch method.
No manual JSON, pin, secret, START or state-directory copying is required.

Current runtime digest:
`6578a9d9b6ba975ef3d94b7cfa50e9f8e875d29e2c05648e8a34df1dd828dbf1`.
Node SHA-256:
`71e4a37e9edffe78130997f2d2806dfa58e72f6742587ff73b494b48abc23413`.
Surface native preparation/source parity at this digest is operator-reported PASS.
Any future experiment must reverify its source with
`--runtime-check --expected-source-digest`; earlier 3fd81298 parity is historical. Existing
Python 3.11 / cryptography 49.0.0 / pyOpenSSL 26.4.0
dependencies are unchanged; do not reinstall without a demonstrated need.

After separate physical-session authorization, one launch command per host
generates then evaluates public-only shell instructions. The generator exits
before the first node starts; the native shell sequences initial/restart children,
never holds or transports authentication material, and preserves numeric failures.
The Windows script creates/removes only the scoped temporary Private-profile TCP
42828 exception, local 192.168.68.54 from 192.168.68.50. Mac IP and port/process
checks are automatic; trusted Wi-Fi uma on Mac remains operator-attested. Windows
checks its IP, uma/Private profile, port and old rule/process absence. Any failure
stops, with cleanup; no automatic failed-session retry.

**Do not execute these physical launch commands under offline-only authority.**
From each approved candidate root, using its already verified Python environment:

```zsh
# Mac visible Terminal; the verified OpenSSL runtime must already be on PYTHONPATH.
l28Script="$(python -B -m coin.persistent_disposable_testnet_node --print-launcher --role writer --ack-private-lan --expected-source-digest 6578a9d9b6ba975ef3d94b7cfa50e9f8e875d29e2c05648e8a34df1dd828dbf1)" && eval "$l28Script"
```

```powershell
# Surface Administrator PowerShell; use the existing verified isolated python.exe.
& { $s = & python -B -m coin.persistent_disposable_testnet_node --print-launcher --role follower --ack-private-lan --expected-source-digest 6578a9d9b6ba975ef3d94b7cfa50e9f8e875d29e2c05648e8a34df1dd828dbf1; if ($LASTEXITCODE -ne 0) { throw 'STOP: launcher generation failed' }; & ([scriptblock]::Create(($s -join "`n"))) }
```

Both roles automatically exchange bounded UNTRUSTED public records on the same
scoped endpoint. At `PAIRING_REQUIRED`, physically inspect the **complete identical
64-character fingerprint on both screens**, then type `PAIR` locally on each.
Decline/interrupt on any mismatch. Repeat once after the genuine process restart:
**two comparisons total**, two local approvals per comparison. Public acknowledgments
cannot authorize themselves; TLS must subsequently prove possession of the exact
approved private identities before HMAC/ledger work. Never approve remotely learned
or truncated fingerprints. No private authentication prompt or display exists.

Fingerprint construction: SHA-256 of `L28-PHYSICAL-PUBLIC-PAIRING-V0.1\0` followed
by existing canonical JSON bytes of exactly `profile`, `writer`, `follower`.
Profile is `l28-physical-public-pairing/v0.1`; writer/follower values are the complete
role-ordered PUBLIC_ENROLLMENT envelopes described below. Existing canonical JSON
sorts keys, has compact separators and UTF-8 encoding. Initial records bind fresh
certificates/source/endpoints/phase with null context; the automatically generated
fresh session/START is then authenticated inside TLS/HMAC. Restart records bind
the retained session/START, new public identities and the same source/endpoints.
No TOFU, automatic approval, private-key persistence or cross-process credential
handoff. Preparation/approval waits expire with the unchanged certificates;
active runtime <=120 seconds, also capped by certificates and original START+600.

Each phase writes only an exclusive public JSON report under a newly created
temporary report directory. Restart checks the previous report, a different local
PID, fresh certificate pins, retained session/START, identical durable state,
replay rejection and divergence halt. Shell cleanup verifies no node/listener;
Windows also verifies temporary rule removal. Public disposable state is retained
for evidence on physical hosts, never imported into canonical state. Watchdog
exit 124 can leave a public crash lock: preserve evidence, do not force retry.

Offline evidence: 34 focused tests, 141 affected regressions, actual two-process
initial/restart CLI with fresh PIDs over AF_UNIX socketpairs, and declined-pairing
CLI checks PASS. AF_UNIX test mode is explicit, POSIX-only, requires local public
terminal input, and always reports `physical_two_host_verified=false`; its logical
endpoint adapter is not physical-IP evidence. Test approvals are offline fixtures,
not a physical automatic-approval mode. Mac script syntax passes zsh; Windows
script scope/finally paths were statically checked locally; its subsequent native
Windows execution and cleanup are operator-reported PASS in the accepted session.
Offline tests alone do not prove physical operation. The final acceptance above
uses actual Mac reports plus explicit operator Surface/physical attestation.
Neither offline nor physical PASS authorizes production activity or a new session.

#### Earlier manual prepared-enrollment interface — not the current launch path

The disposable LAN core reuses the ledger, canonical validator, replay protection
and Option A. Authorized future endpoints are Mac writer `192.168.68.50` and
Surface follower `192.168.68.54:42828`. This legacy section describes pre-acceptance
behavior, not a request to repeat the accepted physical session.

The authentication amendment uses pinned `pyOpenSSL==26.4.0` with
`cryptography==49.0.0` on Python 3.11 (including pyOpenSSL's required typing
backport). Its actual offline interface opens no sockets or child processes:

```sh
python -B -m coin.persistent_disposable_testnet_node --offline-auth-handoff
```

It executes real mutually certificate-pinned TLS 1.3 through memory BIOs,
generates one fresh random 32-byte authentication value without displaying it,
and passes matching single-use in-memory inputs into the existing mutual HMAC
authentication. Peers, source digest, fresh session ID, numeric START, roles and
phase are bound to the handoff. START is configured automatically; no secret or
timestamp copying prompt exists. TLS credentials are passed as cryptography
objects, never certificate/private-key files. Library conversions may create
transient private bytes in RAM. Owned buffers are cleared and references closed;
Python/OpenSSL do not guarantee erasure of all copies, OS swap or core dumps.

`--handoff-case wrong-pin`, `wrong-peer`, `expired`, `incomplete`, `tamper` and
`replay` select offline negative probes; each must exit nonzero with a stable
public rejection code. Successful evidence includes cleanup status and explicitly
sets `physical_two_host_verified=false`. No ledger transaction is claimed by this
authentication-only command.

Public pins are trust anchors, not secrets. `--coordinate` displays its own
complete, canonical PUBLIC_ENROLLMENT JSON line. After direct physical inspection
on the independently controlled peer computer, import `VERIFIED ` followed by that
peer's **entire JSON line** at the local public prompt (no quotes or extra newline).
Do not enter only a 64-character pin. Do not approve a record learned solely from
an unauthenticated network connection, remote page or third party. No
trust-on-first-network-use is performed. This record and its input are public;
authentication material is generated and transferred only inside pinned TLS.
No operator ever sees or types an authentication secret.

The public envelope has exactly `status` and `enrollment`; status is
`PUBLIC_ENROLLMENT`. Enrollment has exactly `profile`, `role`, `pin`,
`source_digest`, `context`, `phase`, `writer`, `follower`, `port`, `certificate_der`.
The versioned profile is `l28-prepared-public-enrollment/v0.1`; roles/phases and
private endpoints are exact scoped values, port is integer 42828 (not Boolean),
pin/source digest are lowercase SHA-256 hex, and certificate_der is canonical
public DER encoded as lowercase even-length hex (at most 4096 characters).
Initial context is null; restart context must equal the retained session/START.
The self-signed certificate's fingerprint, role, IP, signature, algorithm and
validity are checked before activation. Unknown/missing/duplicate fields,
noncanonical JSON, substitution, expiry and unverified input reject.

`VERIFIED` is the operator's local attestation that the complete record was
physically compared. Software cannot prove that human action occurred. The
record is not cryptographic proof of peer key possession: unchanged exact-pin
TLS and HMAC must still succeed before state application. PREPARED_ENROLLED is
not transaction PASS, and reports `network_started=false`. The same memory-only
identity remains alive until activation/cleanup; it cannot be saved/restarted to
reuse an enrollment. Native Windows full-record entry/copy usability and physical
inspection are not established by offline verification.

The writer generates the fresh session and numeric START automatically. A bounded
public bootstrap carries them to the follower; this is UNTRUSTED metadata until
the exact context agrees inside mutually pinned TLS and existing HMAC. A changed
bootstrap cannot authorize ledger application. The same peer-IP-checked connection
carries the memory-BIO TLS handoff and then existing HMAC ledger frames. No second
port, router, ledger, signing authority or consensus mechanism is added.
Standalone `--lan` without verified in-memory input still fails closed. Retired
manual-secret coordinators must not be used.

The existing HMAC ledger transport provides integrity/authentication, not payload
confidentiality; only public disposable events may use it. The TLS handoff protects
the authentication value. Local OS compromise and production custody are outside
this bounded experiment. No signing, custody or consensus authority is added.

The integrated offline interface exercises that same wire driver, TLS, HMAC,
canonical disposable payment path, durable reopen, replay rejection and divergence
halt without a TCP/IP listener or network socket. Existing asyncio ledger code
uses local OS control socketpairs on the verified Mac; those are not peers or
listeners. It does not prove physical hosts or actual process restart:

```sh
python -B -m coin.persistent_disposable_testnet_node --offline-coordinator
```

The successful offline command also emits four public, expected `reason=replay`
ledger warnings on stderr. Those are the negative probes, not transaction failures.
Require exit 0 plus the structured OFFLINE_COORDINATOR_PASS/state/cleanup fields;
do not use an empty-stderr heuristic or print a manual PASS after a failure.

Negative probes add `--coordinator-case wrong-pin`, `wrong-peer`, `source-mismatch`,
`interrupted`, `tamper`, `bootstrap-context`, `bootstrap-pin`, `unverified-record`,
`substituted-record`, `wrong-record-source` or `wrong-record-role`. Each must exit 1
with the expected public rejection code, not a PASS record. Temporary offline
ledger paths are removed; no historical state is read. Normal failures close
connections, identities and single-use inputs. The former 300-second preparation
and 420-second total invocation caps are superseded by the authorized prepared
enrollment amendment. Preparation is bounded by the existing certificate expiry
(unchanged creation+600 seconds, with the existing 30-second not-before backdate),
not an unlimited wait or a renewable lease. No listener or ledger
activity starts during preparation. Initial numeric START is generated only at
the writer's readiness transition; restart retains that START and the original
600-second network session. Active runtime is at most 120 seconds, capped further
by both certificates' remaining validity and the retained session. A late activation
has less than 120 seconds available; it cannot reset the deadline. Expired
preparation or credentials reject, without silently
regenerating an enrolled certificate. OS exit closes handles at the hard deadline; a public crash
lock can remain and must not be cleared to force a retry. Local OS compromise,
swap/core dumps and power-loss cleanup are not guaranteed.

#### Preparation only — no physical session authorized by offline PASS

Both machines need Python **3.11.x**, cryptography **49.0.0**, pyOpenSSL **26.4.0**
and its required typing backport. Installation or source transfer on the Surface
must use the separately approved method; neither is performed by these commands.
Use a fresh candidate directory, not an overlay of old retired session data.
Windows console input uses the documented standard-library
[kbhit/getwch interfaces](https://docs.python.org/3.11/library/msvcrt.html#console-i-o);
Windows-native console/runtime execution remains to be verified on the Surface.

For the current paired workflow use the digest above; the following manual
prepared-enrollment example is historical. From the reviewed Mac candidate root, obtain
the public inventory and retain its approved `source_digest`:

```sh
python -B -m coin.persistent_disposable_testnet_node --source-inventory
```

On Surface, from the approved updated candidate root, use the **Mac-approved**
digest below, never a value derived from the unverified Surface itself. The
inventory compares every file in the existing ten-file runtime closure, including
the validator, ledger, node and pinned requirements; matching just the node file
is insufficient. Runtime check opens no listener and generates no session/key:

```powershell
$ErrorActionPreference = 'Stop'
$L28Digest = '3fd812981f3a9e38b52173da220ebb02948f9a84ae81d912dab777da1812c7de'
py -3.11 -B -m coin.persistent_disposable_testnet_node --runtime-check --expected-source-digest $L28Digest
if ($LASTEXITCODE -ne 0) { throw 'L28 runtime/source parity failed' }
```

#### Historical endpoint-only Surface correction — retired after timing amendment

Do NOT run the historical block below for the current timing candidate: it targets
only the earlier fe56e608 endpoint candidate, not the current 3fd81298 runtime.
It is retained as prior procedure/evidence, not a source-update instruction.
The corrected node source must be synchronized through a separately approved method
and checked against the current complete runtime digest above before physical use.
No dependency changes are needed. The earlier procedure edited one node constant, verified
the entire old runtime closure before writing, validates expected new bytes before
writing, and checks the complete new runtime closure afterward. No dependency,
source archive transfer, listener or firewall action is required. Preserve the
old ZIP/SOURCE_SHA256.json as historical provenance, not a manifest of amended
bytes. Documentation/tests are not part of the ten-file runtime source digest.

```powershell
Set-Location 'C:\Users\pjgur\Downloads\L28-Surface-2481871a-prep\L28-Surface-2481871a'
$ErrorActionPreference = 'Stop'
$p = (Resolve-Path 'coin\persistent_disposable_testnet_node.py').Path
$old = 'd79c163dfdbdefbdc4bbeacac5f4645d0f16c61ecc99071017d6c673d9d1c72c'
$new = '41eeb2fa77a7df11ba8d593d81ec4fda263dfee9aba672beacea595aaec4dea3'
$L28Digest = 'fe56e6081232fb0752f78fa10b5c405fa4338a308bad4c0481453b34947ee7a4'
if ((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne $old) { throw 'Unexpected original node: STOP' }
& .\.venv\Scripts\python.exe -B -m coin.persistent_disposable_testnet_node --runtime-check --expected-source-digest 2481871a789dcd301e874142d26c673445821a2e85ca1c7a153adb8af63240b5
if ($LASTEXITCODE -ne 0) { throw 'Original runtime parity failed: STOP' }
$text = [IO.File]::ReadAllText($p, [Text.Encoding]::UTF8)
$from = 'LAN_FOLLOWER_IP = "192.168.68.75"'
$to = 'LAN_FOLLOWER_IP = "192.168.68.54"'
if ([regex]::Matches($text, [regex]::Escape($from)).Count -ne 1) { throw 'Unexpected endpoint contents: STOP' }
$bytes = [Text.UTF8Encoding]::new($false).GetBytes($text.Replace($from, $to))
$sha = [Security.Cryptography.SHA256]::Create()
try { $hash = ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant() } finally { $sha.Dispose() }
if ($hash -ne $new) { throw 'Corrected bytes mismatch: nothing written' }
[IO.File]::WriteAllBytes($p, $bytes)
if ((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne $new) { throw 'Write verification failed: STOP' }
& .\.venv\Scripts\python.exe -B -m coin.persistent_disposable_testnet_node --runtime-check --expected-source-digest $L28Digest
if ($LASTEXITCODE -ne 0) { throw 'Corrected runtime parity failed: STOP' }
```

The historical result above does not establish current source parity. The timing
amendment stops offline; no physical session or firewall change is authorized by it.

Do not proceed if missing dependencies, altered source or any native command
fails. No trailing manual PASS is permitted. Before runtime, verify trusted Wi-Fi
uma, both operator-controlled machines, Mac `192.168.68.50`, Surface
`192.168.68.54`, aligned clocks, a Private Windows profile and no TCP 42828
listener or leftover rule. The addresses are not automatically changed:

```powershell
$L28IP = @(Get-NetIPAddress -AddressFamily IPv4 | Where-Object IPAddress -eq '192.168.68.54')
if ($L28IP.Count -ne 1) { throw 'Surface IP changed: STOP' }
$L28Profile = Get-NetConnectionProfile -InterfaceIndex $L28IP[0].InterfaceIndex
if ($L28Profile.NetworkCategory -ne 'Private') { throw 'Private profile required' }
netsh wlan show interfaces
if ($LASTEXITCODE -ne 0) { throw 'Cannot verify trusted Wi-Fi' }
if (Get-NetTCPConnection -LocalPort 42828 -State Listen -ErrorAction SilentlyContinue) { throw 'Port occupied: STOP' }
[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
```

On Mac, read `ifconfig en0` and `date -u +%s`, verify the exact scoped IP and
trusted network, then run the same `--runtime-check --expected-source-digest`
with the approved Python/dependency runtime. A changed endpoint blocks the session.

#### Future physical procedure — separate runtime/firewall approval required

Run these only after preparation and explicit physical-session authorization.
Use the verified runtime on each machine. Preparation must finish before the
unchanged certificate expires, then at most 120 seconds of active runtime remain,
further capped by both certificate expirations and the retained session. Do not
reuse a timed-out session or key. Prepare both visible local terminals first;
do not relay public pins or readiness through chat during either phase.

1. Surface starts follower, displaying its complete public enrollment JSON line.
2. Mac starts writer, displaying its complete public line. Directly inspect both
   records on their origin machines. Import Surface's verified complete line on
   Mac with the `VERIFIED ` prefix; Mac waits at its public READY prompt.
3. Import Mac's physically verified complete line on Surface, also with the
   `VERIFIED ` prefix. This alone confirms
   local readiness and begins its bounded listener runtime; no Surface READY input.
   Record import does not replace the required TLS/HMAC peer authentication.
   After Surface displays FOLLOWER_LISTENING, enter READY on Mac; only then does
   its active runtime/automatic initial START begin. No START value or secret is entered.
4. Compare both COORDINATOR_PHASE_PASS reports: supply 28, balances 0/28, same
   transaction IDs, state commitment, source digest, session and numeric START.
   Both commands must exit 0. Save the two public `data_dir` paths.
5. Restart as new processes using `--phase restart --data-dir <that host's path>`.
   Fresh complete public enrollment records must again be physically compared
   and imported; TLS keys and
   authentication material are fresh, while public session/START come from each
   independently persisted state. Finish inside the original 600-second window.
   Both reports must show replay rejection, unchanged state and terminal divergence
   halt. Each host's PID must differ from its own initial invocation.

Mac commands (from this worktree, with the verified dependencies available):

```sh
python -B -m coin.persistent_disposable_testnet_node --coordinate --role writer --phase initial --ack-private-lan --expected-source-digest <MAC_APPROVED_SOURCE_DIGEST>
python -B -m coin.persistent_disposable_testnet_node --coordinate --role writer --phase restart --data-dir <MAC_PUBLIC_DATA_DIR> --ack-private-lan --expected-source-digest <MAC_APPROVED_SOURCE_DIGEST>
```

Surface Administrator PowerShell: the following future-session wrapper creates
only the explicitly authorized narrow rule and removes it in `finally`, on success
or failure. Keep this terminal open through restart. Do not run it now. Run all
preflight checks above first. If any prerequisite fails, STOP before this wrapper.

```powershell
$L28Rule = 'L28-TEMP-TWOHOST-42828'
if (Get-NetFirewallRule -Name $L28Rule -ErrorAction SilentlyContinue) { throw 'Retired rule present: STOP' }
$L28Created = $false
try {
  New-NetFirewallRule -Name $L28Rule -DisplayName $L28Rule -Profile Private -Direction Inbound -Action Allow -Protocol TCP -LocalAddress 192.168.68.54 -RemoteAddress 192.168.68.50 -LocalPort 42828 | Out-Null
  $L28Created = $true
  py -3.11 -B -m coin.persistent_disposable_testnet_node --coordinate --role follower --phase initial --ack-private-lan --expected-source-digest $L28Digest
  if ($LASTEXITCODE -ne 0) { throw 'Initial phase failed: STOP' }
  $L28State = Read-Host 'PUBLIC Surface data_dir from its new PASS report'
  py -3.11 -B -m coin.persistent_disposable_testnet_node --coordinate --role follower --phase restart --data-dir $L28State --ack-private-lan --expected-source-digest $L28Digest
  if ($LASTEXITCODE -ne 0) { throw 'Restart phase failed: STOP' }
} finally {
  if ($L28Created) { Remove-NetFirewallRule -Name $L28Rule -ErrorAction Stop }
  if (Get-NetFirewallRule -Name $L28Rule -ErrorAction SilentlyContinue) { throw 'Firewall cleanup failed' }
  if (Get-NetTCPConnection -LocalPort 42828 -State Listen -ErrorAction SilentlyContinue) { throw 'Listener remains: STOP and identify process' }
}
```

Verify both Python invocations exited on both machines; check no Mac listener via
`lsof -nP -iTCP:42828 -sTCP:LISTEN` and no Windows listener/rule as above. A killed
PowerShell window or power loss cannot guarantee `finally`; independently verify
and remove only the exact authorized rule before another attempt. Retain public
evidence only. Do not delete ledgers or clear crash/halt markers to force recovery.
No physical PASS, commit, merge, push or production approval follows from offline
coordinator PASS. Protocol, economics, history, custody and F171 remain unchanged.

See [CONTRIBUTING.md](CONTRIBUTING.md) before proposing changes and
[SECURITY.md](SECURITY.md) for vulnerability reporting.

## Safety

L28 is protocol software, not an investment promise. Do not use historical
balances, test ledgers, or protocol examples as evidence of market value.
Never commit private keys, seed phrases, or wallet credentials.

Report vulnerabilities according to [SECURITY.md](SECURITY.md).

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) and
[NOTICE](NOTICE).
