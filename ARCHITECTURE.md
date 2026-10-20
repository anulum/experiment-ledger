<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
EXPERIMENT-LEDGER — repository identity and validation foundation
-->

# Experiment Ledger architecture

The planned system accepts experiment records from evidence-producing tools, verifies references through Evidence Manifest Toolkit and appends accepted records to a local embedded store. Queries, lineage walks and reports operate over explicit immutable snapshots.

The Ledger owns its storage protocol, record ingestion, query semantics, lineage and reporting. It does not own evidence production, compute scheduling, signing authority or a second Common verifier.

Both native Python and Rust implementations are required to read and append the same provisioned store. The Rust integration with the installed Toolkit is limited to Common verification; it is not a proxy to Python Ledger storage.

The [detailed architecture](docs/ARCHITECTURE.md) describes the planned boundaries. No corresponding runtime is implemented in the current repository foundation.
