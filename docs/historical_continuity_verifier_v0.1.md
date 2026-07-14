# L28 Offline Historical Continuity Verifier v0.1

- Foundation: 17
- Status: Public manifest verification; non-activation
- Verification mode: Manifest only

## Purpose

The L28 Offline Historical Continuity Verifier validates the public
Foundation 16 historical-continuity manifest without requiring or discovering
private historical ledger files.

It produces a deterministic JSON report for independent review, automation,
and machine-to-machine verification.

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

The verifier accepts only an explicitly supplied manifest path. It does not
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

## Future modes

Snapshot and reconstruction verification may be added in later versions.
Those modes must require explicit caller-supplied artifact paths and preserve
the same offline, read-only, fail-closed security boundary.

They are not implemented or implied by version 0.1.
