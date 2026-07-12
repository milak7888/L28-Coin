# L28 M2M Conformance CLI v0.1

**Document:** L28 M2M Offline Conformance CLI and Deterministic Verification Report v0.1
**Status:** Offline verify-only tooling (Foundation 7)
**Normative subordination:** Subordinate to [L28 Protocol v1.0.0](../../PROTOCOL.md) and [transcript_validation_v0.1.md](transcript_validation_v0.1.md).
**Related:** [test_vectors_report_v0.1.json](test_vectors_report_v0.1.json), [security_model.md](security_model.md)

## 1. Purpose

Foundation 7 provides a read-only offline CLI that:

1. accepts one signed M2M transcript from an explicitly selected local file or standard input;
2. runs the Foundation 6 transcript validator on the original bytes;
3. emits exactly one deterministic JSON conformance report to standard output.

It does not sign, spend, query a ledger, operate a network, write report files, or create persistent replay state.

Foundation 8 introduces a separate offline replay registry. Foundation 9 adds optional registry integration to this CLI; see [admission_cli_v0.1.md](admission_cli_v0.1.md). Without registry flags, Foundation 7 behavior is unchanged.

Successful reports mean coordination consistency only. They do not mean L28 settlement acceptance, finality, service delivery, refund, or dispute resolution.

## 2. Command syntax

```
python -m coin.m2m_conformance_cli --input PATH [--require-terminal] [--pretty] \
  [--replay-registry ABSOLUTE_PATH | --create-replay-registry ABSOLUTE_PATH]
python -m coin.m2m_conformance_cli --stdin [--require-terminal] [--pretty] \
  [--replay-registry ABSOLUTE_PATH | --create-replay-registry ABSOLUTE_PATH]
python -m coin.m2m_conformance_cli --version
```

Rules:

- Exactly one of `--input PATH` or `--stdin` is required (except `--version`).
- No directory scanning, globbing, recursive reads, or default interactive stdin.
- No `--output`, URL, signing, or wallet options.
- `--pretty` changes formatting only.
- `--require-terminal` is forwarded to Foundation 6.

## 3. Input safety

`MAX_INPUT_BYTES = 1048576`

| Mode | Behavior |
|---|---|
| File | Explicit regular file only; reject missing paths, directories, symlinks, devices, sockets, FIFOs; binary read once; path never appears in the report |
| Stdin | Binary read; reject interactive TTY stdin; same byte limit |

Oversized input is rejected before JSON parsing. Raw transcript bytes are not retained after processing and are not echoed in errors.

## 4. Report schema

Exactly one JSON object is emitted with these fields:

| Field | Meaning |
|---|---|
| `report_version` | `l28-m2m-conformance-report/v0.1` |
| `profile` | `l28-m2m-transcript/v0.1` |
| `ok` | boolean |
| `code` | Foundation 6 or CLI failure code |
| `state` | current/terminal state or null |
| `exchange_id` | M2M `transaction_id` or null |
| `verified_messages` | integer count |
| `failed_index` | integer or null |
| `envelope_code` | underlying envelope code or null |
| `settlement_transaction_id` | cited L28 tx id or null |
| `require_terminal` | boolean flag echo |
| `input_mode` | `file`, `stdin`, or null |
| `input_size_bytes` | byte length or null |
| `input_sha256` | SHA-256 of exact received bytes (lowercase hex) or null |
| `report_id` | deterministic report integrity id (lowercase hex) |

Never included: wall-clock time, hostname, username, PID, platform, absolute path, private material, raw input, or stack traces.

### 4.1 Input hash

`input_sha256 = SHA-256(raw input bytes)` as lowercase hex.

Different whitespace or encoding produces a different hash even if semantic JSON is equivalent.

### 4.2 Report ID

Domain prefix: `L28-M2M-V0.1-REPORT` + `0x00`

```
report_id = SHA-256(domain || Canon(report body excluding report_id))
```

`Canon` is Foundation 5 L28-M2M Canonical JSON. `report_id` is integrity identification only — not a signature, attestation, settlement proof, or trust claim.

## 5. Exit codes

| Code | Meaning |
|---|---|
| `0` | transcript conformance passed |
| `1` | input read, verification/conformance failed |
| `2` | usage or input acquisition failure |
| `3` | internal/backend failure |

Examples: bad signature → 1; incomplete with `--require-terminal` → 1; missing file/symlink/oversized/TTY → 2; verification backend unavailable → 3.

## 6. stdout / stderr contract

- stdout: exactly one JSON object + one final newline
- compact mode: sorted keys, compact separators
- pretty mode: sorted keys, stable indentation
- stderr empty for normal pass/fail reports
- usage text may appear on stderr for usage errors
- no ANSI color; no logging noise on stdout

## 7. Version

`--version` prints `l28-m2m-conformance-cli/v0.1` and exits 0 without reading input or creating runtime data.

## 8. CLI failure codes

`usage_error`, `input_not_found`, `input_not_regular_file`, `input_symlink_rejected`, `stdin_is_tty`, `input_read_error`, `input_too_large`, `internal_error`

## 9. Test vectors

Deterministic fixtures: [test_vectors_report_v0.1.json](test_vectors_report_v0.1.json).
