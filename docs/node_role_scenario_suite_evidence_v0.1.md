# L28 Offline Node-Role Scenario-Suite Evidence v0.1

## 1. Purpose

This document specifies an offline verifier for a Foundation 24 node-role
scenario suite and its deterministic Foundation 24 report.

The verifier establishes that:

- the supplied suite is valid under the public Foundation 24 rules;
- the supplied Foundation 24 report has the exact public schema;
- the report identifier is valid for the supplied report body;
- the report is the exact deterministic report for the supplied suite;
- all required Core and P2P transitions remain covered;
- all reserved-state rejection requirements remain covered; and
- every scenario case supplies successful terminal `STOPPED` evidence.

This component is an offline pure-data verifier.

It does not construct a runtime node, open a network connection, access or
modify a ledger, mine L28, access a wallet, sign data, activate a checkpoint,
or claim that a real deployment occurred.

## 2. Foundation relationship

Foundation 25 builds only on public L28-Coin components:

- Foundation 20 node-role conformance;
- Foundation 21 inert node-role model;
- Foundation 22 offline transition transcript verification;
- Foundation 23 offline inert scenario execution; and
- Foundation 24 offline scenario-suite verification and reporting.

Foundation 25 does not alter those foundations.

The Foundation 24 suite verifier and deterministic report builder remain the
authoritative sources for suite semantics and report construction.

## 3. Normative language

The terms **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## 4. Security classification

Foundation 25 output is classified as:

`offline deterministic simulation evidence`

It MUST NOT be represented as:

- runtime node evidence;
- network-listener evidence;
- peer-connectivity evidence;
- ledger activation evidence;
- mining evidence;
- wallet ownership evidence;
- signing evidence;
- checkpoint acceptance evidence; or
- deployment evidence.

## 5. Versions and identifiers

The evidence version is:

`l28-node-role-scenario-suite-evidence/v0.1`

The core verifier version is:

`l28-node-role-scenario-suite-evidence-verifier/v0.1`

The deterministic CLI version is:

`l28-node-role-scenario-suite-evidence-cli/v0.1`

The deterministic CLI report version is:

`l28-node-role-scenario-suite-evidence-report/v0.1`

The CLI profile is:

`l28-node-role-scenario-suite-evidence-verification/v0.1`

## 6. Input boundary

The core verifier accepts caller-supplied `str` or `bytes` only.

The CLI accepts one explicit caller-supplied file path through `--evidence`.

The core verifier MUST NOT:

- discover evidence automatically;
- search directories;
- read environment variables;
- read configuration files;
- write files;
- make network requests; or
- start background work.

The maximum encoded evidence size is 2,097,152 bytes.

Oversized input MUST be rejected before JSON parsing.

## 7. Top-level evidence schema

The evidence document is a JSON object with exactly three fields:

```json
{
  "evidence_version": "l28-node-role-scenario-suite-evidence/v0.1",
  "suite": {},
  "report": {}
}
```

The fields are:

- `evidence_version`: exact Foundation 25 evidence version;
- `suite`: complete Foundation 24 scenario-suite object; and
- `report`: complete deterministic Foundation 24 CLI report object.

Missing and additional fields MUST be rejected.

The `suite` and `report` values MUST be JSON objects.

## 8. Strict JSON processing

Input MUST be valid UTF-8 JSON.

The verifier MUST reject:

- invalid UTF-8;
- duplicate object keys at any depth;
- `NaN`;
- positive or negative infinity;
- a non-object top level; and
- unsupported input types.

The verifier fails closed.

## 9. Foundation 24 suite verification

The `suite` object is canonically serialized and supplied to the public
Foundation 24 suite verifier.

The suite MUST produce:

- `ok` equal to `true`; and
- `code` equal to `suite_valid`.

Any invalid or incomplete suite produces `suite_invalid` evidence.

Foundation 25 does not replace or weaken Foundation 24 suite validation.

## 10. Foundation 24 report schema

The supplied report MUST contain exactly the Foundation 24 report fields:

- `ok`;
- `code`;
- `detail`;
- `profile`;
- `report_version`;
- `cli_version`;
- `suite_version`;
- `scenario_version`;
- `model_version`;
- `transcript_version`;
- `verifier_version`;
- `case_count`;
- `roles`;
- `suite_sha256`;
- `core_covered_transitions`;
- `core_missing_transitions`;
- `p2p_covered_transitions`;
- `p2p_missing_transitions`;
- `core_reserved_rejections`;
- `core_missing_reserved_rejections`;
- `p2p_reserved_rejections`;
- `p2p_missing_reserved_rejections`;
- `cases`;
- `checks`; and
- `report_id`.

Missing, additional, or wrongly typed fields MUST fail closed.

The Foundation 24 `report_id` MUST be 64 lowercase hexadecimal characters.

## 11. Foundation 24 report identifier

Foundation 25 recomputes the Foundation 24 report identifier using the public
Foundation 24 report algorithm.

The recomputed identifier MUST equal the supplied `report_id`.

A report whose identifier is malformed or mismatched is invalid even when the
remaining fields appear plausible.

Recomputing a report identifier after inserting a false claim does not make
that claim valid. Suite-to-report binding is checked separately.

## 12. Suite-to-report binding

After the suite passes verification, Foundation 25 constructs the expected
Foundation 24 report directly from the verified suite result.

The supplied and expected reports are compared as canonical JSON bytes.

They MUST match exactly.

This comparison binds all Foundation 24 report claims, including:

- suite commitment;
- versions;
- role coverage;
- transition coverage;
- reserved-state rejection coverage;
- case results;
- completed checks; and
- report identifier.

## 13. Transition coverage recheck

Foundation 25 independently confirms that the verified suite result reports:

- all 11 required Core transitions;
- no missing Core transitions;
- all 8 required P2P transitions; and
- no missing P2P transitions.

An incomplete transition claim produces `coverage_invalid`.

## 14. Reserved-state rejection recheck

Foundation 25 independently confirms complete rejection coverage for:

- `CANONICAL_READY_RESERVED`;
- `RUNNING_RESERVED`; and
- `LISTENING_RESERVED`.

The Core and P2P missing-reserved lists MUST be empty.

Reserved-state coverage records rejected requests only. They do not indicate
that a reserved state was entered.

## 15. Terminal evidence recheck

At least one verified case MUST be present.

Every Foundation 24 case result MUST:

- be successful; and
- end in `STOPPED`.

No Foundation 25 evidence may treat `PAUSED`, `FAILED`, a reserved state, or an
unknown state as successful terminal evidence.

## 16. Canonical evidence commitment

The logical evidence object is serialized using:

- UTF-8 encoding;
- lexicographically sorted object keys;
- no insignificant whitespace;
- comma separator `,`;
- colon separator `:`;
- non-ASCII text preserved; and
- non-finite numbers prohibited.

The evidence commitment is:

```text
SHA-256(canonical_evidence_bytes)
```

Semantically identical JSON formatting produces the same commitment.

A semantic change produces a different commitment.

## 17. Immutable result

The core verifier returns an immutable result containing:

- verification status;
- stable code and sanitized detail;
- evidence SHA-256;
- Foundation 24 suite SHA-256;
- source Foundation 24 report identifier;
- case count and role identities;
- Core and P2P transition counts;
- Core and P2P reserved-rejection counts;
- completed checks; and
- component versions.

Input data MUST NOT be modified.

## 18. Stable core codes

The stable core codes are:

- `evidence_valid`;
- `input_type_invalid`;
- `evidence_too_large`;
- `invalid_encoding`;
- `invalid_json`;
- `duplicate_key`;
- `schema_error`;
- `version_unsupported`;
- `suite_invalid`;
- `report_schema_invalid`;
- `report_id_invalid`;
- `suite_report_mismatch`;
- `coverage_invalid`;
- `terminal_evidence_invalid`; and
- `internal_error`.

Unexpected exceptions MUST produce only `internal_error` with the sanitized
detail `internal_failure`.

## 19. Deterministic Foundation 25 CLI report

The CLI emits one deterministic JSON object.

Its fields are:

- `ok`;
- `code`;
- `detail`;
- `profile`;
- `report_version`;
- `cli_version`;
- `evidence_version`;
- `suite_version`;
- `source_report_version`;
- `verifier_version`;
- `evidence_sha256`;
- `suite_sha256`;
- `source_report_id`;
- `case_count`;
- `roles`;
- `core_transition_count`;
- `p2p_transition_count`;
- `core_reserved_rejection_count`;
- `p2p_reserved_rejection_count`;
- `checks`; and
- `report_id`.

`source_report_id` is the verified Foundation 24 report identifier.

`report_id` is the separate Foundation 25 CLI report identifier.

## 20. Foundation 25 report identifier

The Foundation 25 CLI report identifier is domain separated.

Its preimage is:

```text
UTF8("l28-node-role-scenario-suite-evidence-report/v0.1")
|| 0x00
|| canonical_report_body_without_report_id
```

The identifier is the lowercase hexadecimal SHA-256 digest of that preimage.

Pretty output changes presentation only. It does not change the logical report
or its identifier.

## 21. Command-line usage

Run from the L28-Coin repository root:

```console
python3 -m coin.node_role_scenario_suite_evidence_cli \
  --evidence /explicit/path/to/evidence.json
```

Pretty output is optional:

```console
python3 -m coin.node_role_scenario_suite_evidence_cli \
  --evidence /explicit/path/to/evidence.json \
  --pretty
```

Automatic discovery is not supported.

## 22. CLI path safety

The CLI MUST:

- use only the explicit caller-supplied path;
- reject directories;
- reject symbolic links;
- reject non-regular files;
- reject files exceeding the maximum before payload verification;
- detect file identity changes during bounded reading when supported; and
- avoid including caller paths in deterministic failure details.

## 23. Exit codes

The CLI exit codes are:

- `0`: evidence valid;
- `1`: verification or path failure;
- `2`: command usage failure; and
- `3`: internal failure.

## 24. Failure behavior

All validation is fail closed.

The verifier MUST NOT accept evidence merely because:

- its report identifier is internally consistent;
- its suite commitment has the right shape;
- its coverage counts have plausible values;
- it contains both role names; or
- its cases claim `STOPPED`.

Those claims are recomputed from the supplied suite.

Failure details MUST remain bounded and sanitized.

## 25. Non-activation guarantees

Foundation 25 MUST NOT:

- construct `CoreL28Node` or `L28P2PNode` runtime instances;
- enter any reserved lifecycle state;
- open a listener;
- connect to a peer;
- access or mutate a ledger;
- issue or mine L28;
- access a wallet or signing key;
- activate a checkpoint;
- start a background thread or process;
- deploy software; or
- claim runtime readiness.

## 26. Acceptance criteria

Foundation 25 is conformant only when:

1. strict evidence JSON parsing passes;
2. the exact evidence schema passes;
3. the Foundation 24 suite independently verifies;
4. the Foundation 24 report schema is exact;
5. the Foundation 24 report identifier recomputes exactly;
6. the supplied report matches the deterministic report for the suite;
7. all 11 Core transitions are covered;
8. all 8 P2P transitions are covered;
9. all three reserved-state rejections are covered;
10. every case successfully terminates in `STOPPED`;
11. the evidence commitment is deterministic;
12. the Foundation 25 CLI report is deterministic and content bound;
13. malformed and adversarial inputs fail closed;
14. unexpected failures are sanitized; and
15. no runtime, network, ledger, mining, wallet, or deployment activation
    occurs.
