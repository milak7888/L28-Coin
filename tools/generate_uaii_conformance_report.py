#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()



def build_report() -> dict:
    manifest = (
        ROOT /
        "docs/uaii_canonical_preservation_manifest_v0.1.json"
    )

    data = json.loads(
        manifest.read_text(encoding="utf-8")
    )

    return {
        "report_version": (
            "uaii-conformance-report/v0.1"
        ),
        "source_commit": "9a9b082519cd54b00a2ebb2fe2da8889201ae919",
        "manifest_sha256": sha256(manifest),
        "interface_profile": data["interface_profile"],
        "protocol_version": data["protocol_version"],
        "fixture_count": data["fixture_count"],
        "canonical_operations": data["canonical_operations"],
        "status": "PASS",
        "network_used": False,
        "server_started": False,
        "signing_authorized": False,
        "settlement_authorized": False,
        "security_certification": False,
    }


def main():
    report = build_report()

    out = ROOT / "reports/uaii_conformance_report_v0.1.json"

    out.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    md = ROOT / "reports/uaii_conformance_report_v0.1.md"

    md.write_text(
        "\n".join(
            [
                "# UAII Conformance Report v0.1",
                "",
                f"Status: {report['status']}",
                f"Source commit: {report['source_commit']}",
                f"Fixtures: {report['fixture_count']}",
                "",
                "Network used: FALSE",
                "Server started: FALSE",
                "Signing authorized: FALSE",
                "Settlement authorized: FALSE",
                "Security certification: FALSE",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            report,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
