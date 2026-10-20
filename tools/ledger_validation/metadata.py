# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Check complete local-scaffold declarations against their selected source policy."""

import hashlib
from pathlib import Path
from typing import Final

from .inputs import CheckFailure, Json, read_bytes, read_object

SCHEMA_SHA256: Final = "038d594980dcc529038e63a4712999fda1d9c0a519c68b3f6076ebbebf032aae"
PROFILE: Final[dict[str, Json]] = {
    "id": "gotm.enterprise-repository-tier0.local-scaffold",
    "revision": "2026-10-04",
    "standard_sha256": "8421674a61444474447fad2f4d2bfc54dc5a1ea12ae988785e57dbcab385938c",
    "profile_sha256": "f453a70eae008c41f8d26a1f495ec3636f64739bcedb9caac0bdf8774300905c",
}
PLANNED_FORMATS: Final[list[Json]] = [
    "experiment_ledger.quantum_amendment.v1",
    "experiment_ledger.quantum_prereg.v1",
    "experiment_ledger.quantum_result_link.v1",
    "experiment_ledger.record.v1",
]


def verify(root: Path) -> None:
    """Verify the complete metadata and its exact derived capability inventory.

    Parameters
    ----------
    root : Path
        Local repository supplying metadata, schema, lock and inventory.

    Raises
    ------
    CheckFailure
        For unavailable or malformed inputs, changed schema policy, an
        incorrect metadata declaration or a mismatched derived inventory.

    Notes
    -----
    This checks declarations and their byte correspondence. It does not
    qualify the running interpreter, installed dependency graph, Common
    verification, scientific evidence or a domain capability. Actual
    environment and dependency qualification belongs to dependency alignment.
    """
    schema_name = "schemas/repository-domain.schema.json"
    schema_raw, _ = read_object(root, schema_name)
    if hashlib.sha256(schema_raw).hexdigest() != SCHEMA_SHA256:
        raise CheckFailure("schema_source_changed", schema_name)
    metadata_name = "repository-domain.json"
    raw, metadata = read_object(root, metadata_name)
    lock = read_bytes(root, "requirements-dev.txt", 1048576)
    expected: dict[str, Json] = {
        "repository_name": "EXPERIMENT-LEDGER",
        "owner_group": "SC-NEUROMORPHIC-COMPUTING-SYSTEMS",
        "lifecycle": "local_scaffold",
        "evidence_maturity": "architecture_only",
        "capabilities": [],
        "claims": [],
        "qualified_owned_schema_ids": [],
        "planned_owned_schema_ids": PLANNED_FORMATS,
        "validation_profile": PROFILE,
        "tooling_python": {
            "design_baseline": "3.13",
            "actual_version": "3.13.16",
            "supported_range": ">=3.13.16,<3.14",
            "development_lock_sha256": hashlib.sha256(lock).hexdigest(),
        },
        "domain_runtime_dependencies": [],
    }
    if metadata != expected:
        raise CheckFailure("metadata_mismatch", metadata_name)
    inventory_name = "capability-inventory.json"
    _, inventory = read_object(root, inventory_name)
    expected_inventory: dict[str, Json] = {
        "repository_name": "EXPERIMENT-LEDGER",
        "lifecycle": "local_scaffold",
        "evidence_maturity": "architecture_only",
        "capabilities": [],
        "claims": [],
        "qualified_owned_schema_ids": [],
        "source_metadata": {
            "path": metadata_name,
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
    }
    if inventory != expected_inventory:
        raise CheckFailure("inventory_mismatch", inventory_name)
