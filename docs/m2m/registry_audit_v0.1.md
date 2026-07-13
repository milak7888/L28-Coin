# L28 M2M Replay Registry Audit v0.1

**Document:** Offline M2M Replay Registry Auditor and Deterministic Integrity Report v0.1
**Status:** Offline read-only tooling (Foundation 10)
**Normative subordination:** Subordinate to [L28 Protocol v1.0.0](../../PROTOCOL.md), [replay_registry_v0.1.md](replay_registry_v0.1.md), and [admission_cli_v0.1.md](admission_cli_v0.1.md).
**Related:** [test_vectors_registry_audit_v0.1.json](test_vectors_registry_audit_v0.1.json), [security_model.md](security_model.md)

## 1. Purpose

Foundation 10 provides a strictly read-only auditor for an existing Foundation 8 replay/idempotency registry.

Runtime:

- `coin/m2m_registry_audit.py` — `audit_registry(path) -> RegistryAuditResult`
- `coin/m2m_registry_audit_cli.py` — offline CLI wrapper

The auditor:

1. validates an explicitly selected absolute registry path outside the repository;
2. opens SQLite in URI read-only mode with `PRAGMA query_only=ON`;
3. verifies Foundation 8 schema and invariants fail-closed;
4. computes a deterministic logical registry digest over normalized hash-only rows;
5. emits one deterministic JSON audit report.

It does not create, modify, repair, migrate, admit, sign, query a ledger, or operate a network.

Audit success is local registry integrity evidence only. It does not prove knowledge of raw exchange IDs, settlement acceptance, finality, service completion, or network validity. A healthy audit report must not be treated as tamper-proof against offline modification of the SQLite file itself.

## 2. Command syntax

```
python -m coin.m2m_registry_audit_cli --registry ABSOLUTE_PATH [--pretty]
python -m coin.m2m_registry_audit_cli --version
```

Rules:

- Exactly one `--registry ABSOLUTE_PATH` is required (except `--version`).
- No default registry location.
- Paths must be absolute and outside the L28-Coin repository.
- Symlinks, directories, FIFOs, and special files are rejected.
- Registry paths never appear in stdout or stderr.

## 3. Read-only enforcement

- Existing registry only; never creates one.
- SQLite opened with `file:PATH?mode=ro&immutable=1` and `PRAGMA query_only=ON`.
- `PRAGMA trusted_schema=OFF`; attached databases rejected.
- Registry file size, exchange count, and message count are bounded (`8 MiB`, `4096` exchanges, `262144` messages).
- Path is re-validated with `lstat` immediately before SQLite open.
- Views and triggers in `sqlite_master` are rejected.
- No `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `DROP`, `ALTER`, `VACUUM`, migration, repair, or admission operations.
- Does not instantiate `ReplayRegistry` or any other mutating registry component.
- Does not create WAL, SHM, journal, backup, report, or repository-local data files.

### 3.1 `immutable=1` and quiescence contract

Operators MUST treat the registry as closed and quiescent for the duration of an audit:

- no Foundation 9 admission CLI process or other writer may access the same registry file concurrently;
- no `ReplayRegistry` open/create/admit operation may run against the same path in parallel.

`file:PATH?mode=ro&immutable=1` plus `PRAGMA query_only=ON` prevents the auditor from mutating the database or creating SQLite sidecar files (`-journal`, `-wal`, `-shm`). It does **not** provide a coherent-snapshot guarantee if another process modifies the file while the audit is running.

Foundation 10 does **not** define concurrent-write auditing, cross-process locking, registry copying, backup workflows, or live snapshot isolation. Auditing under concurrent writers is out of scope.

An audit report does **not** claim:

- concurrent-writer safety;
- a tamper-proof or point-in-time snapshot;
- proof that the registry bytes were unchanged before or after the audit interval.

`logical_registry_digest` and `report_id` describe the logical rows read during that single read-only pass only.

```
audit_registry(path) -> RegistryAuditResult
```

`RegistryAuditResult` fields:

| Field | Meaning |
|---|---|
| `ok` | boolean |
| `code` | stable audit result code |
| `schema_version` | registry schema version or null |
| `exchange_count` | number of exchange rows |
| `message_count` | number of message rows |
| `terminal_exchange_count` | exchanges in terminal states |
| `nonterminal_exchange_count` | exchanges in nonterminal states |
| `logical_registry_digest` | deterministic logical digest or null |
| `failed_check` | stable failed-check identifier or null |

Never exposed: registry path, raw exchange IDs, transcripts, identities, public keys, signatures, settlement payloads, SQL, exception strings, hostname, username, PID, time, or environment details.

## 5. Integrity checks

Fail closed on:

- unreadable or non-SQLite input
- SQLite `integrity_check` failure
- foreign-key violations
- missing, extra, or incompatible application schema
- wrong schema version
- malformed exchange hashes, fingerprints, heads, or message IDs
- invalid stored state
- exchange/message count mismatch
- non-contiguous message ordinals
- incorrect `previous_message_id` chain
- incorrect head message ID
- incorrect transcript fingerprint
- messages associated with inconsistent exchanges

Foundation 8 application schema:

1. `registry_metadata(key, value)`
2. `exchanges(exchange_hash, transcript_fingerprint, head_message_id, state, message_count)`
3. `messages(message_id, exchange_hash, ordinal, previous_message_id)`

Valid stored states are the Foundation 6 terminal and nonterminal state sets.

## 6. Logical registry digest

Domain prefix: `L28-M2M-V0.1-REGISTRY-LOGICAL` + `0x00`

Normalized body:

```
{
  "schema_version": <int>,
  "exchanges": [
    {
      "exchange_hash": <hex64>,
      "transcript_fingerprint": <hex64>,
      "head_message_id": <hex64>,
      "state": <str>,
      "message_count": <int>,
      "messages": [
        {
          "message_id": <hex64>,
          "ordinal": <int>,
          "previous_message_id": <hex64|null>
        }, ...
      ]
    }, ...   # sorted by exchange_hash ascending
  ]
}
```

```
logical_registry_digest =
    SHA-256(domain || Canon(normalized body))
```

`Canon` is Foundation 5 L28-M2M Canonical JSON. The digest covers normalized logical rows only, not SQLite file bytes or page layout.

## 7. Audit report schema

| Field | Meaning |
|---|---|
| `report_version` | `l28-m2m-registry-audit-report/v0.1` |
| `profile` | `l28-m2m-replay-registry-audit/v0.1` |
| `ok` | boolean |
| `code` | stable audit result code |
| `schema_version` | integer or null |
| `exchange_count` | integer |
| `message_count` | integer |
| `terminal_exchange_count` | integer |
| `nonterminal_exchange_count` | integer |
| `logical_registry_digest` | lowercase hex or null |
| `failed_check` | stable check id or null |
| `report_id` | deterministic report integrity id |

### 7.1 Report ID

Domain prefix: `L28-M2M-V0.1-REGISTRY-AUDIT-REPORT` + `0x00`

```
report_id = SHA-256(domain || Canon(report body excluding report_id))
```

`report_id` is integrity identification only. It is not a signature, settlement proof, spending authorization, snapshot attestation, or proof that the registry file was unchanged before or after the audit.

## 8. Stable result codes

| Code | Meaning |
|---|---|
| `registry_healthy` | all checks passed |
| `invalid_registry_path` | non-absolute or invalid parent/path shape |
| `registry_not_found` | missing registry file |
| `unsafe_registry_path` | symlink, repository-internal path, directory, FIFO, or special file |
| `registry_unreadable` | unreadable or non-SQLite database |
| `registry_schema_mismatch` | schema version, tables, or columns incompatible |
| `registry_integrity_error` | SQLite integrity check failed |
| `registry_foreign_key_error` | foreign-key violation |
| `registry_invariant_error` | Foundation 8 logical invariant violation |
| `internal_error` | unexpected internal failure |

## 9. Exit codes

| Code | Meaning |
|---|---|
| `0` | registry healthy |
| `2` | usage or path/input failure |
| `3` | schema, integrity, corruption, unreadable database, or internal failure |

Machine callers MUST inspect JSON fields in addition to the process exit code.

## 10. stdout / stderr contract

- stdout: exactly one JSON object + one final newline for syntactically valid invocations
- stderr empty for ordinary healthy, path-rejection, and integrity-failure reports
- usage text may appear on stderr for usage errors
- no ANSI color or logging noise on stdout

## 11. Test vectors

Deterministic fixtures: [test_vectors_registry_audit_v0.1.json](test_vectors_registry_audit_v0.1.json).
