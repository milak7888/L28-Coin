# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_report_generation_is_deterministic():
    subprocess.run(
        [
            sys.executable,
            "tools/generate_uaii_conformance_report.py",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(
        (
            ROOT /
            "reports/uaii_conformance_report_v0.1.json"
        ).read_text()
    )

    assert report["status"] == "PASS"
    assert report["fixture_count"] == 77
    assert report["network_used"] is False
    assert report["server_started"] is False
    assert report["signing_authorized"] is False
    assert report["settlement_authorized"] is False


def test_report_files_exist():
    assert (
        ROOT /
        "reports/uaii_conformance_report_v0.1.json"
    ).is_file()

    assert (
        ROOT /
        "reports/uaii_conformance_report_v0.1.md"
    ).is_file()
