# L28 Offline Node-Role Composition-Manifest Evidence v0.1

## Status and purpose

Foundation 27 defines offline deterministic simulation evidence for one caller-supplied Foundation 26 composition manifest and its deterministic Foundation 26 report.

- Evidence: `l28-node-role-composition-manifest-evidence/v0.1`
- Verifier: `l28-node-role-composition-manifest-evidence-verifier/v0.1`
- CLI report: `l28-node-role-composition-manifest-evidence-report/v0.1`

A successful result verifies a logical content binding only. It is not runtime evidence and does not construct CoreL28Node or L28P2PNode instances.

## Security boundary

Automatic discovery is not supported. The production verifier accepts JSON text or bytes only; it has no filesystem access or mutation. The CLI accepts one explicit regular-file path, rejecting directories and symbolic links.

This component performs no runtime, network, ledger, mining, wallet, checkpoint, signing, or deployment activation. It creates no listener, connects no peer, reads no credentials, and starts no background worker.

## Evidence schema

Evidence must be one JSON object with exactly these fields:

```json
{
  "evidence_version": "l28-node-role-composition-manifest-evidence/v0.1",
  "manifest": {},
  "report": {}
}
```

Duplicate keys, non-finite JSON constants, non-object top-level values, missing fields, extra fields, invalid UTF-8, and payloads over 2 MiB fail closed.

`manifest` is supplied to Foundation 26 `verify_node_role_composition_manifest_json`. It must return `manifest_valid`.

## Foundation 26 report binding

The submitted `report` must have exactly Foundation 26 `REPORT_FIELDS`.

The verifier then:

1. Requires a lowercase 64-character SHA-256 `report_id`.
2. Recomputes Foundation 26 `compute_report_id(report)`.
3. Requires the submitted identifier to equal the recomputed identifier.
4. Rebuilds the expected Foundation 26 report from the verified manifest.
5. Requires canonical equality between the supplied and expected reports.

This prevents a valid but changed manifest from reusing an old report. It binds the manifest SHA-256, components, roles, trust boundaries, Foundation 25 evidence values, and all Foundation 26 checks to the current manifest.

## Canonical evidence commitment

The evidence SHA-256 is calculated over canonical JSON:

```text
SHA-256(UTF-8(JSON(value, ensure_ascii=false, allow_nan=false,
  sort_keys=true, separators=(",", ":"))))
```

Formatting and object-key order do not change the commitment. Semantic changes do.

## Result contract

A result contains:

```text
ok, code, detail,
evidence_sha256, manifest_sha256, report_id,
component_ids, roles, trust_boundary_ids, checks,
evidence_version, manifest_version, report_version, verifier_version
```

Success uses stable code `evidence_valid` and the checks:

```text
identity
schema
manifest_verification
report_schema
report_identifier
manifest_report_binding
semantic_commitment
```

Stable failure codes include:

```text
input_type_invalid
evidence_too_large
invalid_encoding
invalid_json
duplicate_key
schema_error
version_unsupported
manifest_invalid
report_schema_invalid
report_id_invalid
manifest_report_mismatch
internal_error
```

Unexpected exceptions return only `internal_error` and `internal_failure`.

## CLI

```text
python -m coin.node_role_composition_manifest_evidence_cli \
  --evidence path/to/evidence.json
```

`--pretty` changes presentation only. The deterministic CLI report is bound to the domain:

```text
l28-node-role-composition-manifest-evidence-report/v0.1
```

The `source_report_id` field is the verified Foundation 26 report identifier.

Exit codes:

| Exit | Meaning |
| --- | --- |
| 0 | Evidence valid |
| 1 | Verification failure |
| 2 | CLI usage failure |
| 3 | Internal failure |
