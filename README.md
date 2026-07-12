# L28 Coin

L28 is a public machine-to-machine settlement protocol designed for software,
devices, autonomous systems, and AI agents. It is independent from the private
Leap28 orchestration system and may be implemented or self-hosted under the
Apache License 2.0.

## Current status

- Protocol specification: frozen at v1.0.0
- Protocol and source: available
- Former hosted L28 server: offline
- Leap28-operated always-on public network: not currently running
- Local and independently operated implementations: supported by the public protocol boundary
- Automatic mining or distribution: not started merely by cloning or importing the code

L28 being available does not mean Leap28 controls it. Leap28 may interact only
through the same public transaction, ledger, consensus-height, reward, and work
validation interfaces available to other implementations.

## Canonical economic record

| Fact | Preserved value |
|---|---:|
| Protocol hard cap | 28,000,000 L28 |
| Emission schedule ceiling | 11,130,000 L28 |
| Historically mined | 2,824,584 L28 |
| Treasury locked | 500,000 L28 |
| Circulating at the recorded snapshot | 2,324,584 L28 |
| Halving interval | 210,000 |
| Reward sequence | 28 → 14 → 7 → 3 → 1 → 0 |

The historical allocation checkpoint records 2,824,584 L28 mined through entry
100,877. Bootstrap or test execution must never mint that historical amount a
second time.

## Protocol boundary

See [PROTOCOL.md](PROTOCOL.md) for the normative v1.0.0 rules. In particular:

- coinbase is the only issuance mechanism;
- canonical height comes from consensus state;
- missing required state fails closed;
- issued supply never exceeds 28,000,000 L28;
- Leap28 cannot inject mint events, override supply, or bypass validation.

## Relationship to Leap28

Historical Ledger Proof
        ↓
Genesis Bootstrap
        ↓
genesis_state.json
        ↓
BlocklessLedger Runtime
        ↓
Mining + Transactions
        ↓
L28 M2M Settlement Layer
        ↓
Leap28 Autonomous AI Economy

Leap28 supplies decision-making and policy. L28 supplies independently
verifiable settlement. Either system can exist without embedding the other.

## Safety

L28 is protocol software, not an investment promise. Do not use historical
balances, test ledgers, or protocol examples as evidence of market value.
Never commit private keys, seed phrases, or wallet credentials.

Report vulnerabilities according to [SECURITY.md](SECURITY.md).

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) and
[NOTICE](NOTICE).
