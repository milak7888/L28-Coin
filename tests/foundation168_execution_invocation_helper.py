# SPDX-License-Identifier: Apache-2.0
"""Sole explicit future F168 execution entrypoint. Importing is inert."""

import argparse
import hashlib
import json
from pathlib import Path

from coin.foundation168_bounded_runtime_driver import (
    BoundedRuntimeDriver,
    EXPECTED_ARTIFACT_HASHES,
    default_backend_factory,
    exact_scope,
)
from coin.foundation168_execution_authorization import (
    OneShotExecutionAuthorization,
    initial_state,
)
from coin.foundation168_execution_evidence import persist_evidence


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_PATHS = {
    "f164_candidate": ROOT / "coin/future_live_adapter_candidate.py",
    "f166_gate": ROOT / "docs/l28_foundation166_runtime_authorization_decision_gate_v0.1.json",
    "f167_gate": ROOT / "docs/l28_foundation167_bounded_execution_preflight_gate_v0.1.json",
    "protocol": ROOT / "PROTOCOL.md",
    "validator": ROOT / "coin/tx_validation.py",
}


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path):
    def reject_duplicate_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("DUPLICATE_INVOCATION_EVIDENCE_KEY:" + key)
            result[key] = value
        return result

    return json.loads(
        Path(path).read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
    )


def invoke_foundation168_once(
    decision_evidence_path,
    invocation_evidence_path,
    persistent_claim_path,
    evidence_output_path,
):
    """Validate, claim once, run once, and persist terminal evidence."""

    artifact_hashes = {name: _sha256(path) for name, path in ARTIFACT_PATHS.items()}
    if artifact_hashes != EXPECTED_ARTIFACT_HASHES:
        raise RuntimeError("F168_BOUND_ARTIFACT_HASH_MISMATCH")
    authorization = OneShotExecutionAuthorization(
        initial_state(), persistent_claim_path=persistent_claim_path
    )
    driver = BoundedRuntimeDriver(
        authorization,
        default_backend_factory(ROOT),
    )
    evidence = driver._run_claimed_once(
        exact_scope(),
        artifact_hashes,
        _load_json(decision_evidence_path),
        _load_json(invocation_evidence_path),
    )
    return persist_evidence(evidence_output_path, evidence)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--execute-once",
        required=True,
        choices=["AUTHORIZE_FOUNDATION168_EXECUTION_ONCE"],
    )
    parser.add_argument("--decision-evidence", required=True)
    parser.add_argument("--invocation-evidence", required=True)
    parser.add_argument("--persistent-claim", required=True)
    parser.add_argument("--evidence-output", required=True)
    args = parser.parse_args(argv)
    return invoke_foundation168_once(
        args.decision_evidence,
        args.invocation_evidence,
        args.persistent_claim,
        args.evidence_output,
    )


if __name__ == "__main__":
    main()
