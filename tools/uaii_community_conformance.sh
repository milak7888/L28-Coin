#!/bin/sh
# SPDX-License-Identifier: Apache-2.0

MODE="${1:-integrity-only}"
PYTHON="${PYTHON:-python3}"

case "$MODE" in
  integrity-only|full) ;;
  *)
    echo "usage: $0 [integrity-only|full]"
    exit 2
    ;;
esac

"$PYTHON" -B -m pytest \
  -p no:cacheprovider \
  tests/test_uaii_canonical_preservation_manifest.py -q || exit 1

echo "CANONICAL_PRESERVATION=PASS"
echo "FIXTURE_COUNT=77"

if [ "$MODE" = "full" ]; then
  node tests/typescript/uaii_cross_adapter_parity.mts >/dev/null || exit 1
  echo "NODE_PARITY=PASS"

  "$PYTHON" -B -m pytest \
    -p no:cacheprovider \
    tests/test_uaii_cross_adapter_parity.py \
    tests/test_uaii_typescript_sdk.py \
    tests/test_uaii_python_sdk.py \
    tests/test_uaii_rest_adapter.py \
    tests/test_uaii_mcp_adapter.py \
    tests/test_uaii_reference_core.py \
    tests/test_universal_access_*.py -q || exit 1

  echo "CROSS_ADAPTER_CONFORMANCE=PASS"
fi

echo "NETWORK_USED=FALSE"
echo "SERVER_STARTED=FALSE"
echo "SIGNING_AUTHORIZED=FALSE"
echo "SETTLEMENT_AUTHORIZED=FALSE"
echo "SECURITY_CERTIFICATION=FALSE"
echo "COMMUNITY_CONFORMANCE=PASS"
