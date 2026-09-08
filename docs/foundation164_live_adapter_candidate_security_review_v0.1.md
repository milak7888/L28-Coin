# Foundation164 Non-Activating Live-Adapter Candidate Security Review v0.1

Status: `PASS_NON_ACTIVATING_LIVE_ADAPTER_CANDIDATE`

## Purpose and boundary

Foundation164 introduces the first production-package adapter candidate while deliberately keeping it non-activating. The candidate validates and freezes injected opaque references, verifies the F161 lifecycle owner, F162 security boundary, committed F163 readiness record, and data-only deadline descriptor, then produces preparation, lifecycle, cleanup-eligibility, release, and terminalization data only.

It does not create, start, connect, signal, terminate, or otherwise operate any process, thread, synchronization primitive, queue, channel, socket, network, wallet, signer, miner, settlement path, deployment, or testnet runtime.

## Isolation and provenance

The candidate is not imported by `coin.__init__`, any CLI, node, server, runtime, testnet, wallet, signer, or public entrypoint. Loading it requires a future caller to do so explicitly; this package does not add such a caller.

Registration requires complete ready, result-channel, child, startup-supervisor, F161-owner, F162-boundary, F163-gate, and bounded-deadline inputs. Exact identity and ordered collection correspondence are checked against both F161 and F162. Duplicate resources, missing values, equality lookalikes, owner mismatch, malformed F163 evidence, and deadline mismatch fail closed before any reference is frozen.

After validation, the candidate retains the exact references and an immutable snapshot of the F163 gate. Resource replacement, repeated freeze, and post-freeze gate mutation fail closed while preserving references for cleanup planning.

## Lifecycle, deadline, and cleanup

The six F161 phases remain strictly ordered. F164 creates data-only transition plans and never calls the injected owner or boundary. Skipped, backward, repeated, and direct-release transitions are rejected. One immutable bounded-deadline descriptor covers resource construction, startup supervision, child bootstrap, active work, and cleanup initiation; no timer is implemented.

Cleanup eligibility remains unavailable until the planned cleanup phase, every exact child is recorded terminal, and every exact startup supervisor is recorded quiescent. Eligibility and release plans explicitly record that no cleanup action occurred and no resource was released.

## Terminalization

`SUCCESS`, `EXECUTION_ABORT`, `CLEANUP_FAILURE`, and `TERMINALIZATION_FAILURE` are distinct one-way data states. Recording a state performs no execution or cleanup. Unknown or repeated terminal transitions fail closed.

## Authorization, capability, and authority firewalls

Preparation is not execution authority. `F161_EXECUTION_AUTHORIZED=false`, `F162_EXECUTION_AUTHORIZED=false`, `F163_EXECUTION_AUTHORIZED=false`, and `F164_EXECUTION_AUTHORIZED=false`. Old authorization is non-reusable; F159 retry remains forbidden. A new authorization, separate security review, and separate explicit execution invocation remain mandatory before any future execution could be considered.

The F164 Python files import none of the prohibited runtime/capability modules, dynamically load none, and invoke no prohibited operation. No environment, credential, secret, wallet, key, RPC, or infrastructure discovery exists.

F164 has zero authority over issuance, supply, height, validation, consensus, history, ledger, settlement, signing, wallet state, or Bitcoin evidence. Protocol v1.0.0 and `coin.tx_validation.validate_transaction` remain unchanged; Bitcoin remains external evidence only.

## Review result and remaining work

The cross-module review result is `PASS 13 / GAP 0 / BLOCKED 0` for candidate isolation, provenance, lifecycle, deadline, failure preservation, cleanup, terminalization, authorization separation, capability firewall, runtime-import isolation, protected authority, historical preservation, wording, and exact six-file scope.

This candidate is suitable for non-activating code review only. It is not a live adapter, execution authorization, runtime authorization, testnet readiness, or production readiness. Any activation design is separate future work and requires new explicit authority.
