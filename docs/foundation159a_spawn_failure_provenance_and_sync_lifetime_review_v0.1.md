# Foundation159A Spawn-Failure Provenance and Synchronization-Lifetime Review v0.1

Status: `PASS_OFFLINE_REMEDIATION_NO_EXECUTION_AUTHORITY`

## Provenance correction

The authoritative F158 consumption marker machine-persists only `result=ABORT`, parent `execution_error="Empty:"`, terminal consumed/non-restartable state, and successful cleanup. It does not persist either child traceback.

The two `FileNotFoundError` errno `2` tracebacks at `multiprocessing.synchronize.SemLock._rebuild`, their occurrence before agent initialization, and the absence of an operator-session retry are classified as `OPERATOR_OBSERVED_NOT_MACHINE_PERSISTED`. No stderr is fabricated, reconstructed, or claimed as hash-bound.

The SemLock traceback is a proximate observed failure location only. It does not prove a deeper operating-system or multiprocessing root cause.

## Retry and future authority

The exclusive F158 consumption marker proves the consumed authorization cannot pass a second execution claim. It does not prove that no rejected retry invocation was attempted because no invocation audit exists. Operator observation separately records that no retry was observed or performed in the operator session.

`NEW_AUTHORIZATION_REQUIRED=true`, `SEPARATE_SECURITY_REVIEW_REQUIRED=true`, `SEPARATE_EXPLICIT_EXECUTION_INVOCATION_REQUIRED=true`, and `F159_RETRY_FORBIDDEN=true`. Any future experiment must use a new authorization identity and cannot reuse F157, F158, or F159 consumption state.

## Synchronization-lifetime review

The consumed F158 helper creates the shared `ready` event as a setup-thread local, passes it in both child argument tuples, and returns only the results queue and process list. Therefore the helper does not structurally demonstrate a parent-owned strong reference to `ready` across the entire child-bootstrap and active-execution lifetime.

This supports only the hypothesis `SHARED_READY_EVENT_PARENT_LIFETIME_MAY_NOT_COVER_CHILD_BOOTSTRAP`; it does not establish causation for the F159 abort.

The offline future-design contract requires a returned runtime bundle to retain every synchronization primitive required by spawned children from creation through process construction, start supervision, child bootstrap, active execution, and cleanup. Cleanup may release those references only after every child is terminal. Fake object-lifetime tests cover that contract without importing multiprocessing, starting children, opening sockets, or using a network.

The historical F158 helper is not modified or reauthorized. The future-design contract is structurally covered offline; no live runner remediation, execution authority, or production readiness follows.
