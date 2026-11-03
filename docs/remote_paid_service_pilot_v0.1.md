# Remote Paid Service Pilot v0.1

## Limited Private Testnet v0.1 — two purchases, one balance

For the separately frozen two-purchase mode, use the existing loopback
procedure below with these changes:

1. Add `--two-purchases` to `--role pilot-config`. Use a fresh session,
   free loopback port and new temporary state directory. Keep the exact
   configuration bytes for both phases, within the original 120-second window.
2. Start the provider as documented. Give the requester both `--input`
   and `--second-input` with different valid text. One requester process and
   one provider process sign both purchases with the same respective keys.
   Expect 100/0 -> 72/28 -> 44/56 and two signed result/receipt bundles.
3. Save the requester's `public_artifacts` object as shown below. It contains
   two ordered purchases and their original signed delivery envelopes.
   After both processes exit, restart the provider on the **same** state and
   configuration. Restart the requester with both original inputs plus
   `--replay-artifacts`. Require two rejected replays, no new work/debit,
   unchanged state commitment and a different provider PID.
4. Verify both listeners are closed and remove only this run's temporary
   state. Keep only sanitized evidence if needed.

The focused executable acceptance driver invokes the actual CLI roles, checks
the signed receipts, and cleans up owned processes and temporary state:

```sh
python -B -m pytest -p no:cacheprovider -q -s \
  tests/test_public_testnet_service_demo.py::test_private_reuse_actual_cli
```

The signed purchase index and transaction nonce distinguish the two
purchases. Reopening the store only permits verification; it does not recover
keys or resume spending. A post-commit interruption may leave an accepted
payment without a result. No refund, atomic delivery or canonical settlement
is provided. This mode is authorized on IPv4 loopback only; two-device
acceptance requires fresh operator permission and verified private routing.

## Historical single-purchase pilot

NON-PRODUCTION / disposable commerce only. PROJECT_STATE ACTIVE.
The historical offline implementation is documented below; see SYSTEM_STATE for
the separately accepted physical outcome and its qualifications.
No canonical history, issuance, consensus, custody/F171 or settlement authority.

## One purchase, existing interfaces

`DISCOVER -> REQUEST -> QUOTE 28 L28 -> PAY -> WORK -> VERIFY -> RECEIPT`

Use `coin.public_testnet_service_demo` with `--private-pilot`. The existing three
HTTP paths, commerce artifacts, deterministic extractive summary and canonical
validator are reused. The private catalog is signed and explicitly declares that
its transport is not the public-HTTPS interface. Default service/public behavior
is unchanged. No marketplace, payment engine, wallet or new consensus is added.

The complete public configuration binds fresh 32-lowercase-hex session ID,
provider/requester IPv4 endpoints and port, creation/expiration, summary service,
price, source digest, outer PUBLIC001 transport network and inner
DISPOSABLE_OFFLINE payment domain. These domains are deliberately distinct;
persistent-node coinbase/signatures/state are not imported or composed here.

Every private envelope uses existing CanonUaii/PureEd25519 signing under
`L28-REMOTE-PAID-SERVICE-PILOT-V0.1\0`. Exact body order is context, role,
public_key, peer, method, path, payload; signature follows. Context is SHA-256 of
that domain followed by compact UTF-8 ordered configuration JSON. Signatures cover
the complete body, including exact nested artifacts. Discovery and hello pin the
same ephemeral provider key; request envelopes use the payment spender's key.
After a valid request, the provider pins that requester key. Inner signatures
bind service/input/request/quote/payment/result/receipt using existing rules.
Public output retains configuration, signed HTTP transcript and original artifacts.

No acknowledgement proves an encrypted route. Loopback mode admits only
127.0.0.1 for both endpoints. Future private mode admits only distinct Tailscale
100.64.0.0/10 IPv4 endpoints and exact public node keys. Before either role opens
its HTTP connection/listener it reads installed `tailscale status --json`, requiring
Running, the matching local device key/IP and the matching online peer key/IP.
The provider binds only its configured IP; it admits only the exact requester IP.
The requester binds its configured source and checks the connected destination.
HTTP itself is not TLS; the verified Tailscale route supplies encryption/device
authentication. Independent operator verification of account/device ownership and
access-network topology remains mandatory. Never forward this HTTP service publicly.

## Durable acceptance and interruption semantics

The provider reuses DurableProvider/DurableStore, SQLite FULL synchronization,
audit/lineage checks and canonical-ledger rehydration. Its existing public marker
also binds the pilot context; a wrong context cannot reopen or reseed that state.
Only the first purchase in a context may use the preloaded 100/0 fixture. Payment
acceptance and 72/28 balances commit before summary computation. Issued supply
and mint height stay zero; these are disposable preloaded balances, not issuance.

An accepted ID always rejects as replay, including after genuine process restart
with fresh in-memory keys. Rejected payments cause no balance/state/work mutation.
Crash after payment acceptance is deliberately fail-closed: no re-debit or repeated
work, no refund/remint, and no promise of result delivery/recovery. An interrupted
accepted purchase can remain charged with work/receipt incomplete. This pilot is
at-most-once work, not atomic payment-and-delivery or production settlement.
State rollback protection is local audit/lineage consistency, not external trusted
anti-rollback custody. Restart verification uses public old signed artifacts only.
The provider replay endpoint checks the accepted ID and original signed payment
proof only; it never recomputes the summary, including through result-verifier
side effects. Full result/receipt verification is independently requester-side.

REUSE means a second fresh session, fresh disposable identities and a separate
new state directory. It never resets or overwrites the first accepted state.
Private keys remain process memory only; no private serialization/environment/
command-argument storage. Python does not promise secure memory zeroization.

## Executable loopback procedure

Use the verified Python 3.11 environment with existing repository dependencies.
No installation is authorized by this slice. All files below contain PUBLIC
configuration/artifacts or disposable provider state; do not reuse production paths.
Choose an unused port >=1024. Prepare commands first; configuration expires in
120 seconds. Each invocation is bounded, with provider cleanup time reserved.

```sh
python -B -m coin.public_testnet_service_demo --role pilot-runtime-check
python -B -m coin.public_testnet_service_demo --role pilot-config \
  --pilot-session <fresh-public-32-hex-id> --port 28429 > /tmp/l28-pilot-public.json
```

Provider terminal (one application process):

```sh
python -B -m coin.public_testnet_service_demo --role provider --private-pilot \
  --pilot-config /tmp/l28-pilot-public.json --state-dir /tmp/l28-pilot-new-state
```

After `pilot_provider_ready`, requester terminal (second application process):

```sh
python -B -m coin.public_testnet_service_demo --role requester --private-pilot \
  --pilot-config /tmp/l28-pilot-public.json \
  --input 'Agents buy summaries. L28 binds payment to work. Results carry receipts.' \
  > /tmp/l28-pilot-public-result.json
```

The requester verifies delivery, probes the exact accepted payment as replay and
requests signed shutdown. Both commands must exit zero. Extract only the public
`public_artifacts` object for keyless restart verification:

```sh
python -c 'import json; r=json.load(open("/tmp/l28-pilot-public-result.json")); print(json.dumps(r["public_artifacts"],ensure_ascii=False,separators=(",",":")))' > /tmp/l28-pilot-public-artifacts.json
```

Restart the provider with the SAME unexpired config/state, then run:

```sh
python -B -m coin.public_testnet_service_demo --role requester --private-pilot \
  --pilot-config /tmp/l28-pilot-public.json --replay-artifacts /tmp/l28-pilot-public-artifacts.json \
  --input 'Agents buy summaries. L28 binds payment to work. Results carry receipts.'
```

Require replay=true, work=false, unchanged accepted ID/balances/state commitment,
durable_state_reopened=true and clean shutdown. Expiration fails closed; do not
change config timestamps/context to reopen old state. REUSE repeats the initial
purchase with another fresh session and separate state/config paths.

On failure stop the owned provider PID (never broad process kills), wait for exit,
and verify the exact configured port has no listener. Do not retry automatically.
No firewall changes are needed for loopback. The product driver verifies child
exit codes and probes each exact endpoint after shutdown; tests are not substituted
for separate actual-product evidence.

## Verification and physical gate

Focused: the two authorized test modules with `-k pilot`. Affected regressions:
the same modules with `-k 'not pilot'` plus existing transaction/external-access,
disposable transfer, limited-testnet, identity and protocol-conformance tests.
Use `-p no:cacheprovider` and the verified environment; no dependency changes.
One security review covers only the nine-path change and direct consumers.
NOT_INDEPENDENTLY_AUDITED=true.

Physical execution requires separate operator authorization for one exact bounded
session: provider host, requester host, current Tailscale IPs AND public device
keys independently verified on both machines; source inventory/digest and native
requester runtime/dependencies checked; no stale processes/listeners/rules; exact
provider port available; both operator-controlled devices and encrypted route
verified. Any temporary provider ingress permission must be separately authorized
and source-restricted. No inbound rule is needed for the outbound requester.
Two successful remote purchases require separate fresh disposable state; full
physical acceptance remains PENDING until actual two-computer evidence and cleanup.

## Accepted offline evidence — 2026-11-01

OFFLINE_ACCEPTANCE_PASS; PHYSICAL_ACCEPTANCE_PENDING. No commit is authorized.
45 unique focused cases PASS; 168 disjoint affected regressions PASS once.
One inherited restart-bind defect was corrected and only its failed case rerun;
three later focused deadline/replay cases also PASS. No passing full suite repeated.
Actual CLI evidence was refreshed after concrete runtime corrections.

Final source digest:
`49c627d75fee56ee3ff3f830021084dff74e6245c3170ef6091905e815a1350b`.

Final evidence digest (local path omitted):

SHA-256: `3522f341691dadac467b0b2bb81c2c0bee649e530a96bd76e1f569f51ba9137c`.
The adjacent two public configs, original-artifact bundles and four full phase
records preserve both provider/requester PIDs, signed transcripts, summaries and
receipts. First purchase session `54fb217b0cd84c5e8846a6df70f1e7e5`; REUSE session
`a92dddcd037e43f0ab5d42c22db7dd13`. Each independently reports 100/0 -> 72/28,
one accepted payment, zero issuance/height, genuine restart and replay-only recovery.
Matching initial/restart commitments respectively:

- `3f3419b8cb44192d58bc307d3ecd5c80e8aaaaca698ddcabbbaed6c1d67be5f2`
- `8b4c02d8e86bb04537def8041516ce340cdf20e62435c8af30b089cd652ed4c7`

All eight final application processes exited zero. Both exact loopback listeners
closed and generated disposable state was removed. Only public evidence remains.
Primary-agent consolidated security review completed with no unresolved Critical/
High affecting scope; review snapshot/correction qualification in SYSTEM_STATE.
This offline evidence alone claims no independent audit, native requester parity,
or genuine remote execution.
