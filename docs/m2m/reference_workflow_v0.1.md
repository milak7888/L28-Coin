# L28 M2M Offline Reference Workflow v0.1

**Document:** L28 M2M Reference Workflow v0.1
**Status:** Specification (documentation only)
**Profile:** `l28-m2m-reference-workflow/v0.1`
**Report version:** `l28-m2m-reference-workflow-report/v0.1`

## Purpose

Foundation 14 provides one offline end-to-end reference workflow that exercises the released M2M components together:

1. Transcript validation
2. Disposable replay-registry creation and admission
3. Exact source idempotency (`already_recorded`)
4. Source registry audit
5. Registry backup
6. Registry restore to a new path
7. Restored registry audit
8. Restored idempotency (`already_recorded`)
9. Logical-state comparison
10. One deterministic verification report

The workflow is conformance-only. It does not sign messages, store private keys, access wallets, query ledgers, start networks, claim settlement finality, or leave operational state behind.

## API

`run_reference_workflow_json(raw, *, require_terminal=False, input_mode="api")`

- Accepts untrusted raw JSON bytes or UTF-8 text only.
- Does not accept a prevalidated transcript shortcut.
- Returns a frozen `ReferenceWorkflowResult` with bounded public fields.

## Temporary-state boundary

All SQLite, backup, and restore artifacts exist only inside one `TemporaryDirectory` resolved outside the repository. The workflow rejects a `TMPDIR` or temporary root that resolves inside the checkout. Registry handles are closed before audit, backup, and restore. No report file is written to disk.

## Success conditions

A successful workflow requires:

- transcript conformance succeeds;
- initial admission returns `recorded_new`;
- source repeat returns `already_recorded` (not `already_recorded_prefix`);
- source audit returns `registry_healthy`;
- backup returns `backup_created`;
- restore returns `restore_created`;
- restored audit returns `registry_healthy`;
- restored repeat returns `already_recorded`;
- source and restored logical digest, schema version, exchange count, and message count match;
- all temporary files are removed.

## Deterministic report

Report-ID domain:

`L28-M2M-V0.1-REFERENCE-WORKFLOW-REPORT\x00`

The report ID is computed from canonical JSON of the report body excluding exactly `report_id`. The report excludes temporary SQLite byte hashes, backup artifact SHA-256 values, backup/restore report IDs, timestamps, and host-specific material.

The report ID is not a signature, settlement proof, finality proof, service-completion proof, or spending authority.

## CLI

```text
python -m coin.m2m_reference_workflow --input PATH [--require-terminal] [--pretty]
python -m coin.m2m_reference_workflow --stdin [--require-terminal] [--pretty]
python -m coin.m2m_reference_workflow --version
```

Exit codes:

| Code | Meaning |
|---|---|
| 0 | Complete workflow verified (`ok=true`) |
| 1 | Input acquired but conformance/workflow verification failed |
| 2 | Usage or input acquisition failure |
| 3 | Backend, temporary-environment, or internal failure |

Only exit `0` may produce `ok=true`.

## Related documents

- [test_vectors_reference_workflow_v0.1.json](test_vectors_reference_workflow_v0.1.json)
- [test_vectors_transcript_v0.1.json](test_vectors_transcript_v0.1.json)
- [README.md](README.md)
