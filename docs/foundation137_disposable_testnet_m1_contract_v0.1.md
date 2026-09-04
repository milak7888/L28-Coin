# Foundation 137 - Disposable Testnet M1 Identity + Genesis/Config Contract v0.1

**Status:** specification only / offline / non-activating

Foundation 137 defines the minimum contract for a future disposable L28 test environment.

This milestone addresses planning for F37-12 and M1 only. It does not close F37-12.

Required future properties:

- an explicit disposable network identifier distinct from MAIN;
- deterministic binding between network identity and disposable genesis configuration;
- a required genesis hash before any future runtime can claim testnet identity;
- an explicitly tagged ephemeral data directory;
- hard rejection of historical checkpoint balances as live disposable genesis;
- hard rejection of main-network identity reuse;
- hard rejection of production or creator private-key material;
- preservation of Protocol v1.0.0 economics and canonical validation authority.

Protected economic facts remain immutable:

- hard cap: 28,000,000 L28;
- emission ceiling: 11,130,000 L28;
- historically mined: 2,824,584 L28;
- treasury locked: 500,000 L28;
- circulating snapshot: 2,324,584 L28;
- halving interval: 210,000;
- reward sequence: 28 -> 14 -> 7 -> 3 -> 1 -> 0;
- historical mined-through entry: 100,877;
- next canonical height: 100,878.

No network id instance, genesis artifact, writer, validator, node process, socket,
wallet, signing path, broadcast path, mining path, deployment, or settlement path
is created or authorized by Foundation 137.

F37-12 remains BLOCKED until a later separately reviewed implementation provides
fail-closed validation and deterministic binding tests.

Starting any testnet requires separate explicit operator authorization.
