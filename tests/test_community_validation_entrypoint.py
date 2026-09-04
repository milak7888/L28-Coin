# SPDX-License-Identifier: Apache-2.0

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_readme_exposes_public_validation_entrypoint():
    text = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "## Community validation" in text
    assert "tools/uaii_community_conformance.sh integrity-only" in text
    assert "tools/uaii_community_conformance.sh full" in text
    assert "reports/uaii_conformance_report_v0.1.md" in text
    assert "CONTRIBUTING.md" in text
    assert "SECURITY.md" in text


def test_contributing_preserves_nonactivation_boundaries():
    text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

    assert "Protocol v1.0.0 is frozen" in text
    assert "deterministic offline validation" in text
    assert "private keys" in text
    assert "public testnets" in text
    assert "settlement" in text
    assert "SECURITY.md" in text
    assert "does not certify production security" in " ".join(text.split())


def test_foundation135_is_documentation_only():
    text = (
        ROOT
        / "docs/foundation135_public_community_validation_entrypoint_v0.1.md"
    ).read_text(encoding="utf-8")

    assert "documentation integration / non-activating" in text
    assert "changes no Protocol" in text
    assert "Protocol v1.0.0 remains frozen" in text
