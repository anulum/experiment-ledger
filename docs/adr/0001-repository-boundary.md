<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
EXPERIMENT-LEDGER — repository identity and validation foundation
-->

# Repository boundary

Status: accepted architectural boundary; implementation remains pending.

Experiment Ledger is a standalone local-first registry of experiment records and references. Evidence artefacts remain with their producers. The Ledger owns ingestion, embedded transactional storage, query snapshots, lineage and reports.

The Common verification supplier is Evidence Manifest Toolkit. Both Ledger languages use the same installed supplier API and preserve its complete context and report. No second Common verifier or graph database is introduced.

Both Python and Rust own native storage and consumers. A narrow Rust binding for Common verification does not replace native Rust Ledger semantics.

The foundation has no domain package, empty Rust crate, installable entry point, hosted service or deployment workflow. Planned formats remain ownership declarations until their actual source, implementation and qualification are accepted.
