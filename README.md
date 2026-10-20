<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
EXPERIMENT-LEDGER — repository identity and validation foundation
-->

# Experiment Ledger

Experiment Ledger is being developed as a local registry of experiment records and evidence references. Its purpose is to make the code, data, model, configuration and evidence behind a result traceable across tools.

The repository foundation is under construction. [Metadata, source-provenance checks and native validation child supervision](docs/validation-tooling.md) are available; the remaining executable foundation is unfinished. No Ledger runtime, Python distribution, Rust library, hosted service or qualified experiment result is available. Public capabilities, claims and qualified schema inventories are empty.

## Planned boundary

The Ledger will retain original record bytes, immutable evidence references, append receipts and protected chain checkpoints. Evidence artefacts remain with their producers; this repository will index their identities rather than copy their contents or run experiments.

Both Python and Rust are intended to implement transactional storage and consumers of the same embedded SQLite protocol. Common verification belongs to Evidence Manifest Toolkit. Rust will use a narrow binding to that same installed supplier for Common verification while retaining native Ledger storage and domain semantics.

The intended user operations are record submission, querying, lineage, reporting and chain verification. These operations are planned and are not installation or usage instructions.

## Repository material

- [Architecture](ARCHITECTURE.md) describes ownership and data flow.
- [Validation](VALIDATION.md) separates selected checks from unfinished qualification.
- [Contributing](CONTRIBUTING.md) explains the development boundary.
- [Security](SECURITY.md) provides the private reporting route.
- [Roadmap](ROADMAP.md) distinguishes planned implementation from current material.

Development tools are described by the hash-locked development requirements. These dependencies do not constitute runtime dependencies or a released package. No performance, durability, scientific correctness, device support or external reproducibility claim is made.

## Licence and citation

Source is available under [AGPL-3.0-or-later](LICENSE). Commercial licensing enquiries go to protoscience@anulum.li. See [NOTICE](NOTICE.md), [contributors](CONTRIBUTORS.md) and [citation metadata](CITATION.cff).

## Text and data mining reservation

The rightsholder, Miroslav Šotek (ANULUM), expressly reserves the use of the
works in this repository for text and data mining, including the collection of
this content for, and its use in, training, fine-tuning or evaluating machine
learning and artificial intelligence models, in accordance with Article 4(3) of
Directive (EU) 2019/790 and the national provisions transposing it.

No permission for such use has been granted beyond what the licence in
`LICENSE` grants. This reservation does not change that licence: uses the
licence permits remain permitted on its terms, including its attribution and
share-alike conditions.

Reservation made on 2026-10-19. Requests for permission: contact the
rightsholder through the contact listed in this repository.

This notice was added to this repository on 2026-10-20.
