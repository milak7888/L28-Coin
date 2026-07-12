# Security Policy

Report suspected L28 protocol vulnerabilities privately through GitHub's
private vulnerability-reporting feature for this repository when available.
If it is unavailable, contact the repository owner privately through their
verified GitHub account and request a secure reporting channel.

Do not publish exploit details, private keys, wallet credentials, unpatched
vulnerabilities, or destructive reproductions in a public issue.

Testing must:

- use temporary or explicitly disposable ledger state;
- avoid the historical canonical ledger and allocation records;
- avoid starting mining or network services during test discovery;
- avoid accessing systems or data not owned by the tester;
- preserve the 28,000,000 L28 cap and frozen v1.0.0 invariants.

Include the affected revision, minimal reproduction, expected and observed
behavior, impact, and any proposed mitigation. Reporting an issue does not
grant authorization to operate nodes, access wallets, alter ledgers, or test
third-party infrastructure.
