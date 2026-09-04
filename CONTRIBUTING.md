# Contributing to L28

L28 Protocol v1.0.0 is frozen. Breaking protocol changes require a governed
v2.0.0 rather than silent reinterpretation of v1.0.0.

Contributions should begin with deterministic offline validation.

Run:

`PYTHON=python3 tools/uaii_community_conformance.sh integrity-only`

For the complete public UAII validation surface run:

`PYTHON=python3 tools/uaii_community_conformance.sh full`

Preserve the canonical protocol, economic record, historical evidence,
validation authority, UAII schemas, and fail-closed behavior.

Do not include private keys, seeds, mnemonics, wallet/RPC credentials,
tokens, production credentials, or private infrastructure details.

Ordinary contribution testing must not start or activate servers, nodes,
miners, wallets, networks, signing, broadcast, bridges, deployment,
public testnets, transaction submission, or settlement.

For ordinary issues or pull requests, include the affected revision,
minimal reproduction, expected behavior, observed behavior, and focused
tests where applicable.

Security vulnerabilities must follow [SECURITY.md](SECURITY.md) and should
not be disclosed publicly before appropriate handling.

Passing conformance tests is evidence only. It does not certify production
security or grant protocol, signing, deployment, or settlement authority.
