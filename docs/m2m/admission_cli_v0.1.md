# L28 M2M Admission CLI v0.1

**Document:** L28 M2M Offline Conformance CLI Replay Admission Gate and Deterministic Admission Report v0.1
**Status:** Offline verify-and-admit tooling (Foundation 9)
**Normative subordination:** Subordinate to [L28 Protocol v1.0.0](../../PROTOCOL.md), [conformance_cli_v0.1.md](conformance_cli_v0.1.md), and [replay_registry_v0.1.md](replay_registry_v0.1.md).
**Related:** [test_vectors_admission_v0.1.json](test_vectors_admission_v0.1.json), [security_model.md](security_model.md)

## 1. Purpose

Foundation 9 extends the Foundation 7 offline conformance CLI with an optional replay admission gate backed by the Foundation 8 replay/idempotency registry.

When registry mode is selected, the CLI:

1. acquires transcript bytes using Foundation 7 input rules;
2. verifies the signed transcript with Foundation 6 **before** opening or creating any registry;
3. only after successful conformance, opens or creates the explicitly selected registry and calls Foundation 8 `check_and_record_json` on the original raw bytes;
4. emits exactly one deterministic admission report to stdout.

When registry mode is **not** selected, Foundation 7 behavior remains byte-for-byte unchanged.

Successful admission reports are coordination and local idempotency evidence only. They do not mean L28 settlement acceptance, finality, service delivery, refund, dispute resolution, or authorization to spend.

## 2. Command syntax

```
python -m coin.m2m_conformance_cli --input PATH [--require-terminal] [--pretty] \
  [--replay-registry ABSOLUTE_PATH | --create-replay-registry ABSOLUTE_PATH]

python -m coin.m2m_conformance_cli --stdin [--require-terminal] [--pretty] \
  [--replay-registry ABSOLUTE_PATH | --create-replay-registry ABSOLUTE_PATH]

python -m coin.m2m_conformance_cli --version
```

### 2.1 Registry options

| Option | Meaning |
|---|---|
| `--replay-registry ABSOLUTE_PATH` | Open an **existing** registry (`ReplayRegistry(create=False)`). Never creates a missing registry. |
| `--create-replay-registry ABSOLUTE_PATH` | Create a **new** registry (`ReplayRegistry(create=True)`). Fails if the destination already exists. Parent directory must already exist. |

Rules:

- Registry mode is optional.
- The two registry options are mutually exclusive.
- Paths must be absolute and outside the L28-Coin repository.
- Symlinks, directories, FIFOs, and special files are rejected.
- No default registry path is provided.
- Registry paths never appear in stdout or stderr.

## 3. Verify-before-registry order

For registry mode:

1. Acquire transcript bytes (Foundation 7 input rules).
2. Run Foundation 6 transcript verification first.
3. If conformance fails: do **not** open an existing registry, do **not** create a new registry, write no registry state, emit an admission report containing the conformance failure.
4. Only after successful conformance: open or create the selected registry, call Foundation 8 check-and-record on the original raw transcript, close the registry deterministically.
5. Emit one admission report.

`ReplayRegistry` revalidates the transcript internally. There is no trusted preverified shortcut.

## 4. Admission report schema

When registry mode is selected:

| Field | Meaning |
|---|---|
| `report_version` | `l28-m2m-admission-report/v0.1` |
| `profile` | `l28-m2m-replay-admission/v0.1` |
| `ok` | Admission gate evaluated successfully; may be true for idempotent no-op results |
| `code` | Foundation 6 / CLI conformance code |
| `state` | current/terminal state or null |
| `exchange_id` | M2M `transaction_id` or null |
| `verified_messages` | integer count |
| `failed_index` | integer or null |
| `envelope_code` | underlying envelope code or null |
| `settlement_transaction_id` | cited L28 tx id or null |
| `require_terminal` | boolean flag echo |
| `input_mode` | `file`, `stdin`, or null |
| `input_size_bytes` | byte length or null |
| `input_sha256` | SHA-256 of exact received bytes or null |
| `conformance_report_id` | deterministic Foundation 7 conformance `report_id` for the same inputs |
| `admitted` | true iff `newly_recorded` is true |
| `registry_code` | Foundation 8 replay result code or null |
| `newly_recorded` | true only for `recorded_new` or `recorded_extension` |
| `new_messages` | count of messages newly recorded in this invocation |
| `exchange_hash` | hashed exchange identifier or null |
| `transcript_fingerprint` | hashed transcript fingerprint or null |
| `head_message_id` | head message id or null |
| `registry_message_count` | stored message count or null |
| `report_id` | deterministic admission report integrity id |

Never included: wall-clock time, hostname, username, PID, platform, registry path, private material, raw input, SQL, or exception text.

### 4.1 Admission report ID

Domain prefix: `L28-M2M-V0.1-ADMISSION-REPORT` + `0x00`

```
report_id = SHA-256(domain || Canon(admission report body excluding report_id))
```

`report_id` is integrity identification only. It is not a signature, settlement proof, service completion proof, authorization to spend, or network acceptance.

### 4.2 Conformance report binding

The CLI builds the normal Foundation 7 conformance report internally and exposes its `report_id` as `conformance_report_id`. The standalone conformance report is not emitted separately in registry mode.

## 5. Admission semantics

Downstream action is permitted **only** when `newly_recorded == true` (`recorded_new` or `recorded_extension`).

| Registry result | `ok` | `admitted` | `newly_recorded` | `new_messages` |
|---|---|---|---|---|
| `recorded_new` / `recorded_extension` | true | true | true | > 0 |
| `already_recorded` / `already_recorded_prefix` | true | false | false | 0 |
| `exchange_fork` / `message_replay` / `terminal_exchange_extension` / conformance failure | false | false | false | 0 |
| registry path/open/integrity failures | false | false | false | 0 |

`admitted` is true iff `newly_recorded` is true.

## 6. Exit codes

### 6.1 No registry mode

Foundation 7 exit codes are unchanged:

| Code | Meaning |
|---|---|
| `0` | transcript conformance passed |
| `1` | verification/conformance failed |
| `2` | usage or input acquisition failure |
| `3` | internal/backend failure |

### 6.2 Registry mode

| Code | Meaning |
|---|---|
| `0` | new work recorded (`recorded_new`, `recorded_extension`) |
| `1` | transcript/replay admission rejected |
| `2` | CLI input or registry path/open/create failure |
| `3` | internal/backend/registry integrity failure |
| `4` | valid idempotent no-op (`already_recorded`, `already_recorded_prefix`) |

Safety rules:

- Only exit `0` may correspond to `newly_recorded=true`.
- Exit `4` always has `newly_recorded=false`.
- No other exit may have `admitted=true`.

Machine callers MUST inspect JSON fields in addition to the process exit code.

## 7. No-registry backward compatibility

If neither registry option is present:

- same `report_version`, fields, `report_id`, stdout bytes, exit codes, and `--version` output as Foundation 7;
- no registry import side effect at module import time;
- no registry file access.

## 8. Privacy and limitations

- Registry paths remain caller-local configuration and are never echoed.
- The registry is local, offline, and not authenticated against malicious local modification.
- Admission success does not imply settlement finality, service completion, or spending authority.
- Cross-exchange `message_replay` detection in Foundation 8 may require an open registry session; when equivalent offline corruption breaks registry integrity, CLI open fails closed with `registry_integrity_error` (exit `3`).

## 9. Test vectors

Deterministic fixtures: [test_vectors_admission_v0.1.json](test_vectors_admission_v0.1.json).
