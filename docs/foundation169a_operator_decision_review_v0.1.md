# Foundation 169A — Explicit Operator Decision Boundary Review v0.1

## Result

**PASS 7 / GAP 0 / BLOCKED 0 — commit-ready.**

F169A records the operator's explicit decision `AUTHORIZE_ONE_NEW_BOUNDED_EXPERIMENT` for exactly one bounded F168 experiment. This grants the new one-shot authorization decision, but supplies no invocation and creates no execution permission.

## Current state

- `F166_DECISION=AUTHORIZE_ONE_NEW_BOUNDED_EXPERIMENT`
- `F169A_DECISION=AUTHORIZE_ONE_NEW_BOUNDED_EXPERIMENT`
- `F169A_OPERATOR_DECISION_RECORDED=true`
- `F169A_AUTHORIZATION_GRANTED=true`
- `F168_INVOCATION_PRESENT=false`
- `F168_EXECUTION_AUTHORIZED=false`
- `F168_AUTHORIZATION_CONSUMED=false`
- `F168_EXECUTION_OCCURRED=false`
- `EXECUTION_GATE_OPEN=false`

This authorization is supplied explicitly by the operator, not inferred from implementation, tests, the F168 package, or any previous authorization. It is one-shot only. The F159 authorization is non-reusable and `F159_RETRY_FORBIDDEN=true` remains unchanged.

## Decision contract

The F169A gate is the exact ten-key decision-evidence object required by `coin.foundation168_execution_authorization.OneShotExecutionAuthorization.validate_dual_evidence`. Its authorization ID and F164/F166/F167 bindings are exact. The decision alone leaves `F168_INVOCATION_PRESENT=false`, `F168_EXECUTION_AUTHORIZED=false`, `F168_AUTHORIZATION_CONSUMED=false`, `F168_EXECUTION_OCCURRED=false`, and `EXECUTION_GATE_OPEN=false`.

The operator decision, security review, and a separate explicit F169B invocation remain distinct boundaries. This candidate supplies the operator decision and its offline security review only; it supplies no F169B invocation or execution permission.

## Binding integrity

The decision evidence binds the F164 candidate, committed F166 decision gate, F167 preflight gate, experiment ID, authorization ID, and required base commit exactly as required by the unchanged F168 authorization validator.

## Capability and authority firewalls

The new Python files are offline data-model and test code. They contain none of the forbidden runtime imports or calls, and provide no process, thread, socket, network, or F168 invocation path. No runtime activity, authorization consumption, signing, testnet, mining, broadcast, settlement, or deployment occurred.

The package creates zero authority over issuance, supply, height, validation, consensus, history, ledger, settlement, signing, wallet, or Bitcoin. Protocol v1.0.0 and the canonical validator `coin.tx_validation.validate_transaction` remain hash-bound and unchanged.

## Security review

| Review item | Result | Evidence |
|---|---|---|
| Decision integrity | PASS | The operator-selected decision and all ten required bindings are exact. |
| Authorization separation | PASS | Authorization is recorded, but no invocation or execution permission is created. |
| F159 non-reuse | PASS | Reuse is false and retry remains forbidden in the decision evidence and tests. |
| F168 boundary preservation | PASS | Execution authorization and occurrence remain false; F169B remains separate. |
| Capability firewall | PASS | Static AST checks reject every prohibited import and runtime call. |
| Authority preservation | PASS | Protected authority stays false; protocol and validator hashes are unchanged. |
| Exact scope | PASS | Git scope contains exactly the four existing F169A files. |

## Terminal conclusion

F169A records one new bounded-experiment authorization decision without activating F168. A separate exact invocation remains required; none is present, and no authorization has been consumed or executed.
