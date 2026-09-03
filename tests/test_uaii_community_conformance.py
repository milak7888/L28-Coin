# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "uaii_community_conformance.sh"


def test_runner_exists():
    assert RUNNER.is_file()


def test_integrity_mode_passes():
    completed = subprocess.run(
        ["/bin/sh", str(RUNNER), "integrity-only"],
        cwd=ROOT,
        env={**__import__("os").environ, "PYTHON": sys.executable},
        capture_output=True,
        text=True,
        check=True,
    )

    assert "CANONICAL_PRESERVATION=PASS" in completed.stdout
    assert "FIXTURE_COUNT=77" in completed.stdout
    assert "COMMUNITY_CONFORMANCE=PASS" in completed.stdout
    assert "NETWORK_USED=FALSE" in completed.stdout


def test_invalid_mode_fails_closed():
    completed = subprocess.run(
        ["/bin/sh", str(RUNNER), "invalid"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
