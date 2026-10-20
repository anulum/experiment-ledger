<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
EXPERIMENT-LEDGER — repository identity and validation foundation
-->

# Storage and verification boundaries

## Input and ownership

An experiment record binds code revisions, data and model identities, configuration, environment and typed evidence references. Four planned record formats distinguish ordinary records, quantum preregistration, amendments and result links. Their names in repository metadata are declarations of intended ownership; they do not establish registration or implemented parser support.

Evidence Manifest Toolkit remains the Common verification supplier. The Ledger must retain complete source bytes, typed references, caller-selected context and full verification reports. A stored report does not establish present eligibility, scientific validity or an independent replication.

## Native implementations

Python and Rust must each implement storage, transactions, replay, query snapshots, lineage and Ledger-domain interpretation. Rust may call the same installed Toolkit through a narrow Python binding for Common verification. It must not use Python Ledger storage to stand in for its own implementation.

Both implementations must interoperate with the same provisioned SQLite store and exact engine, filesystem and journal constraints. Write transactions use an explicit expected head and replay token; acknowledgement follows successful commit. Unknown commit outcomes require observation of the original transaction state rather than blind replay or repair.

Sequences use bounded canonical decimal text rather than binary floating point or fixed-width SQLite integers. The planned protocol includes an explicit 256-digit limit. Neither a successful append nor an ordinary process recovery test proves device power-loss durability.

## Queries, lineage and retention

Queries bind store, genesis, head and selector identities. Pagination must refuse stale snapshots. Evidence time is distinct from insertion order and the clock of a later verification invocation.

Lineage distinguishes the visited set from the active traversal stack. Missing references, cycles, quotas and incomplete history remain visible. An empty complete result differs from an unavailable or truncated history.

Pruning requires a protected checkpoint, declared retained range and an explicit event. There is no pruning implementation or deletion authority in this foundation.

## Quantum records

Preregistration, amendments and result links remain distinct immutable records. A preregistration claim requires qualified earlier publication and event intervals; equal, overlapping or missing interval bounds cannot establish the required strict ordering. Failed and retried attempts and their spend remain part of the recorded population.

These are implementation requirements. The current repository has no storage engine, consumer, verification adapter or corresponding qualification result.
