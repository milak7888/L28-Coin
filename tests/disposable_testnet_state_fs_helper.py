# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from coin.disposable_testnet_m2 import DisposableLocalTipAuthority
from coin.disposable_testnet_runtime_boundary import (
    DisposableRuntimeBinding,
    validate_runtime_binding,
)


class DisposableTestStateSandbox:
    TEST_ONLY = True

    def __init__(
        self,
        binding: DisposableRuntimeBinding,
        tip: DisposableLocalTipAuthority,
    ) -> None:
        validate_runtime_binding(binding, tip)

        self.binding = binding
        self.tip = tip
        self._temp = tempfile.TemporaryDirectory(
            prefix="l28-foundation140-"
        )
        self.root = Path(self._temp.name)
        self.state_dir = self.root / (
            "state-" + binding.config_hash[:16]
        )
        self.closed = False

    def _assert_inside_root(self, path: Path) -> None:
        root = self.root.resolve()
        candidate = path.resolve()

        if candidate != root and root not in candidate.parents:
            raise RuntimeError("sandbox_path_escape")

    def create(self) -> Path:
        if self.closed:
            raise RuntimeError("sandbox_closed")

        self._assert_inside_root(self.state_dir)

        if self.state_dir.exists():
            raise RuntimeError("sandbox_state_exists")

        self.state_dir.mkdir(parents=False)

        marker = {
            "profile": "l28-foundation140-test-sandbox/v0.1",
            "network_id": self.binding.network_id,
            "genesis_hash": self.binding.genesis_hash,
            "config_hash": self.binding.config_hash,
            "test_only": True,
            "runtime_authorized": False,
            "network_authorized": False,
            "signing_authorized": False,
            "mining_authorized": False,
            "settlement_authorized": False,
        }

        marker_path = self.state_dir / "binding.json"
        marker_path.write_text(
            json.dumps(
                marker,
                sort_keys=True,
                separators=(",", ":"),
            )
            + chr(10),
            encoding="utf-8",
        )

        return self.state_dir

    def reset(self) -> Path:
        if self.closed:
            raise RuntimeError("sandbox_closed")

        self._assert_inside_root(self.state_dir)

        if not self.state_dir.exists():
            raise RuntimeError("sandbox_state_missing")

        shutil.rmtree(self.state_dir)
        return self.create()

    def cleanup(self) -> None:
        if self.closed:
            return

        self._assert_inside_root(self.root)
        self._temp.cleanup()
        self.closed = True
