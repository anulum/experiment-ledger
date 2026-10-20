<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
EXPERIMENT-LEDGER — repository identity and validation foundation
-->

# Threat model

The planned Ledger handles experiment identities, original evidence references, caller contexts, append receipts, protected heads and reproducibility reports. These assets may include commercially sensitive research metadata.

## Trust boundaries

Producer bytes are untrusted inputs. Record shape, semantic admission, Common verification and actual producer qualification are distinct decisions. Successful parsing cannot establish authenticity, scientific validity, chronology or physical provenance.

The installed verification supplier and its module origins are part of the executable trust boundary. Python and Rust consumers must not load a replacement verifier from received data or fall back to another supplier after an import or API failure.

Store paths, checkpoints and retained ranges require independently provisioned authority. A hash chain alone cannot prove that an unseen suffix was not deleted. A report read from storage must not be mistaken for a current assessment.

## Required controls

The implementation must bound input bytes, references, traversal, numerical sizes, deadlines and resource use. Append and replay semantics must preserve the original bytes and receipts across Python and Rust. Error reports must distinguish refused, unavailable and incomplete states without reflecting arbitrary exception text or sensitive payloads.

Private reporting uses protoscience@anulum.li. Credentials and real sensitive experiment artefacts do not belong in issue reports, fixtures or Git.

## Current assurance

This foundation does not implement ingestion, storage, verification, recovery, signing or a network service. No security certification, tamper-proof storage, provider attestation or power-loss guarantee is asserted. Source review, independent qualification and real boundary checks remain necessary with implementation.
