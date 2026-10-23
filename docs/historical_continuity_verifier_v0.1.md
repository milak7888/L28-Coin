# L28 Offline Historical Continuity Verifier v0.1

- Foundation: 17
- Status: Public manifest verification; non-activation
- Verification modes: Unchanged manifest v0.1; historical PoW evidence v0.1

## Purpose

The L28 Offline Historical Continuity Verifier validates the public
Foundation 16 historical-continuity manifest without requiring or discovering
private historical ledger files.

It produces a deterministic JSON report for independent review, automation,
and machine-to-machine verification.

## Historical manifest integrity correction (2026-10-22)

Manifest validity now requires exact, typed agreement with 70 immutable,
code-owned reference fields, in addition to the existing arithmetic checks.
The candidate manifest cannot redefine its own expected hashes, supply, sizes,
counts, heights or provenance flags. Unknown root/section fields also reject.
Whitespace and key ordering are not pinned; equivalent JSON serialization passes.

Reference provenance is explicit:

- Protected economics come from frozen Protocol/project controls: 28000000 cap,
  11130000 emission ceiling, 2824584 declared supply, 500000 treasury commitment,
  2324584 circulating snapshot, last issuance 100877 and reference next height
  100878. None is a live ledger initialization value.
- Raw/snapshot hashes, byte sizes, counts and issuance heights were independently
  rechecked against the operator-specified public files. Sizes are 40707627 and
  30658355 bytes; physical counts are 102263 and 72098 respectively.
- Other historical metadata is pinned to the published Foundation16 audit and
  manifest at commit `d7b6270fcb21b4b719f10973f5e70c86744d14e5`. Claimed timestamps,
  consolidation identity and allocation/provenance statements remain recorded
  claims, not newly authenticated events. Consolidation bytes are not read here.

The existing manifest has no next-height field. The verifier pins last issuance
height and separately requires its successor to equal 100878; the report exposes
`reference_next_canonical_height`, never an active canonical-state claim. No
historical manifest or original data was rewritten to add this field.

Manifest reports additionally expose:

- `verification_scope=pinned_manifest_metadata_only`;
- `MANIFEST_METADATA_VALID` (true only on successful manifest validation);
- `ARTIFACT_BYTES_VERIFIED=false`;
- `HISTORICAL_POLICY_AUTHENTICATED=false`;
- `CANONICAL_ACCEPTANCE=false`.

These fields participate in the existing deterministic report ID. Exit 0 means
the metadata matches the pinned references, not that the referenced files were
opened. Use the separate explicit PoW artifact command below to verify bytes.
Correlated equation-preserving alterations, missing fields, wrong types, altered
hashes and unknown claims fail closed with the existing schema/invariant codes.

Recovered source difficulty 12 versus recorded 4, missing-height issuance,
treasury enforceability, policy provenance and canonical continuation remain
unresolved. This correction grants no production or consensus authority.

## Scope

Version 0.1 verifies the public manifest's:

- schema, version, status, and required field types;
- wallet-address derivation evidence;
- snapshot and raw-DAG identities;
- deterministic reconstruction commitments;
- parent-graph accounting;
- issuance and treasury-lock arithmetic;
- consolidation evidence boundaries;
- mining-policy evidence boundaries; and
- non-activation requirements.

The manifest mode accepts only an explicitly supplied manifest path. It does not
search for ledgers, wallets, keys, logs, or private infrastructure.

## Command-line usage

Run from the L28-Coin repository root:

    python3 -m coin.historical_continuity_cli \
      --manifest docs/l28_historical_continuity_manifest_v0.1.json

For human-readable JSON:

    python3 -m coin.historical_continuity_cli \
      --manifest docs/l28_historical_continuity_manifest_v0.1.json \
      --pretty

Compact and pretty output represent the same logical report.

## Report fields

A successful report includes `ok`, `code`, `detail`, `profile`,
`report_version`, `manifest_version`, `manifest_sha256`, `checks`, and
`report_id`.

The report identifier deterministically binds the logical report body.
Repeated verification of identical input produces the same logical report and
report identifier.

## Exit codes

| Code | Meaning |
|---:|---|
| 0 | Manifest passed verification |
| 1 | Manifest content failed verification |
| 2 | Command usage or manifest-path failure |
| 3 | Sanitized internal failure |

Verification fails closed. A failure never activates historical state.

## Input protections

The verifier:

- reads only the caller-supplied manifest path;
- rejects missing paths, directories, and symbolic links;
- rejects oversized input before parsing;
- requires valid UTF-8 and valid JSON;
- rejects duplicate JSON keys at any nesting depth;
- enforces required fields and exact field types;
- validates expected hashes and arithmetic relationships; and
- sanitizes unexpected internal errors.

The manifest is read-only and is not modified by verification.

## Security boundary

The verifier performs no:

- network access;
- automatic artifact discovery;
- ledger initialization, migration, repair, or activation;
- mining, wallet, signing, or deployment activity;
- private-key or seed access;
- execution or import of supplied artifacts; or
- copying or publication of private historical ledgers.

Historical snapshot and raw-DAG files are not bundled with L28-Coin.

## Interpretation boundaries

A valid report confirms that the public manifest is internally consistent with
the audited Foundation 16 evidence. It does not independently prove:

- a currently canonical or active ledger;
- a live or spendable wallet balance;
- independent public timestamp publication of the private snapshot;
- proof-of-work validity for historical issuance;
- canonical network continuation;
- bridge reserves or wrapped-asset backing; or
- ownership or spendability of the unconsolidated genesis reward.

Historical supply, treasury-lock, allocation, and consolidation statements
remain evidence claims with the qualifications recorded in the manifest.

## Historical PoW evidence mode (2026-10-22)

This extension independently verifies PoW records in the two pinned public
historical artifacts. It does not run the historical miner or import a ledger.
The manifest-only command and report contract above remain unchanged.

```sh
python -B -m coin.historical_continuity_cli \
  --raw-dag /Users/pjaydondup/Documents/L28-Coin/l28_genesis_ledger_old.jsonl \
  --snapshot /Users/pjaydondup/Documents/L28-Coin/l28_ledger_20251225_201521.jsonl \
  --pretty
```

The two artifact arguments are required together and cannot be combined with
`--manifest`. There is no fingerprint override or unpinned-success mode.

| Input | SHA-256 | Records | PoW records |
|---|---|---:|---:|
| Raw DAG | `1ba544052cee098cea265add04c8fb0ff0562897803ba829b201293745aad669` | 102263 | 2202 |
| Snapshot | `6580333e4dba688f242d82a9ea7253369b7723273b3392dc6d8ae9b78d9b2d11` | 72098 | 817 |

The verifier hashes the same bounded bytes it subsequently parses. Inputs must
be regular files, not final-path symlinks, at most 64 MiB each. JSONL permits
one final newline, but not blank records. Limits are 110000 records per file,
8192 bytes per record, nesting depth 16, 256 members per container, 1024
characters per key and 4096 per string value. Integers have magnitude at most
2^63−1; nonfinite numbers, unpaired surrogate values and duplicate keys reject.
These are evidence-parser resource limits, not new consensus rules.

PoW records require the original issuance field set plus exact-integer
`difficulty=4`. Heights and nonces are nonnegative exact integers, never Booleans
or coerced strings/floats. The payload has exactly `type`, `miner`, `timestamp`,
`nonce`, with `type="mining"` and nonempty string miner/timestamp. Legacy outer
numeric fields retain their historical representation; no migration occurs.

```text
P = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
preimage = UTF8(decimal(entry_height) + prev + P + decimal(payload.nonce))
identifier = SHA256(preimage).hexdigest()
```

The nonce appears inside the payload and again as the decimal suffix. No extra
delimiter/newline is added. This is a hash preimage, not a signed message.
Every PoW identifier must reproduce, meet recorded difficulty 4, resolve its
parent in the raw DAG and have parent height + 1. Every selected PoW record must
match its raw record, including fields not covered by PoW. Duplicate identifiers
reject; competing records at the same height are not silently selected or removed.

The `l28-historical-pow-evidence/v0.1` JSON report includes pinned artifact
digests, verified counts, a deterministic body-bound `report_id`, and separate:

- `HASH_VALID` — all scoped PoW hashes reproduced;
- `RECORDED_DIFFICULTY_VALID` — all scoped PoW hashes satisfy recorded difficulty;
- `HISTORICAL_POLICY_AUTHENTICATED=false`, status `UNPROVEN`;
- `CANONICAL_ACCEPTANCE=false`, status `BLOCKED`.

The recovered source's default difficulty 12 versus recorded 4 is always
disclosed as `MISMATCH_NOT_CONSENSUS_AUTHORITY`, with a count of raw hashes
meeting 12. This is a historical source comparison, not an expected future target.
No input can promote the last two flags. On failure the validity flags stay false
(not established); no partial success is presented as complete verification.

Exit 0 means **evidence-only verification success**, including visible unresolved
policy mismatch. Exit 1 means artifact/record verification failed, 2 means CLI
usage failure, and 3 means sanitized unexpected internal failure. Fixed codes
in `POW_CODES` identify failures without echoing input records or local paths.

Outer reward, supply, difficulty and timestamps are not authenticated by these
PoW preimages; their original bytes are protected by the pinned artifact hashes.
Non-PoW identifiers and the two treasury attestations are not independently
revalidated by this mode. Full DAG reconstruction, policy provenance, issuance
authentication, ownership, enforceable treasury locking, spendability and
canonical continuation remain outside its result. No historical files are bundled.
