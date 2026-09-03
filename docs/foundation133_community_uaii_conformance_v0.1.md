# Foundation 133 — Community UAII Conformance Runner v0.1

**Status:** deterministic offline public validation tooling / non-activating

Foundation 133 provides a command-line validation runner over existing
Universal Access Interface conformance evidence.

Usage:

PYTHON=python3 tools/uaii_community_conformance.sh integrity-only

PYTHON=python3 tools/uaii_community_conformance.sh full

The runner validates existing canonical conformance evidence.

It does not:

- install dependencies
- start servers
- use network services
- load keys or credentials
- sign transactions
- broadcast transactions
- submit transactions
- mine
- bridge
- settle funds
- authorize production activity

A PASS is conformance evidence only.

A PASS is not:

- security certification
- independent security review
- signer authorization
- deployment approval
- settlement approval

Protocol v1.0.0 remains frozen.

coin.tx_validation.validate_transaction remains the sole L28
transfer/coinbase validation authority.
