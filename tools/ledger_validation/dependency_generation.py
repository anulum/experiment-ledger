# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Regenerate development provenance from independent source selections and actual bytes."""

import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
from typing import TypedDict, cast

from packaging.utils import canonicalize_name

from .dependency_inputs import installed_licence_names, parse_requirements, read_text
from .inputs import CheckFailure, read_object
from .metadata import inventory_bytes
from .native_tools import NATIVE_SOURCES

SELECTIONS = "dependency-source-selections.json"
SELECTION_SHA256 = "8dc35fc114c73379e155290a67f4dd7ddd61f8d6f5189fc6d10aba6a06e3f0ae"
PROVENANCE = "dependency-provenance.json"


class _FileIdentity(TypedDict):
    """Reviewed original installed file identity selected by the source owner."""

    path: str
    bytes: int
    sha256: str


class _PackageSource(TypedDict):
    """Independent original artifact, METADATA and licence selections for one package."""

    name: str
    version: str
    metadata_sha256: str
    official_metadata_sha256: str
    source_artifact: dict[str, str | int]
    license_files: list[_FileIdentity]


class _SourceSelections(TypedDict):
    """Exact reviewed source-input layout qualified with SELECTION_SHA256."""

    schema_revision: str
    lock_sha256: str
    source_observation: dict[str, str]
    packages: list[_PackageSource]
    native_tools: list[dict[str, str | int]]
    security_audit: dict[str, str]


def _package(
    selected: _PackageSource, distribution: importlib.metadata.Distribution, *, direct: bool
) -> dict[str, object]:
    raw = distribution.read_text("METADATA")
    if raw is None:
        raise CheckFailure("dependency_metadata_unavailable", PROVENANCE, unavailable=True)
    metadata_sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    if distribution.version != selected["version"] or metadata_sha != selected["metadata_sha256"]:
        raise CheckFailure("dependency_installed_source_mismatch", PROVENANCE)
    expected_licences = {item["path"] for item in selected["license_files"]}
    if installed_licence_names(distribution) != expected_licences:
        raise CheckFailure("dependency_licence_inventory_mismatch", PROVENANCE)
    licences: list[_FileIdentity] = []
    for source in selected["license_files"]:
        try:
            with Path(str(distribution.locate_file(source["path"]))).open("rb") as stream:
                data = stream.read(source["bytes"] + 1)
        except OSError as error:
            raise CheckFailure(
                "dependency_licence_unavailable", PROVENANCE, unavailable=True
            ) from error
        identity: _FileIdentity = {
            "path": source["path"],
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        if identity != source:
            raise CheckFailure("dependency_licence_mismatch", PROVENANCE)
        licences.append(identity)
    metadata = distribution.metadata
    return {
        "name": selected["name"],
        "version": distribution.version,
        "role": "direct" if direct else "transitive",
        "metadata_sha256": metadata_sha,
        "official_metadata_sha256": selected["official_metadata_sha256"],
        "source_artifact": selected["source_artifact"],
        "license_files": licences,
        "license_classifiers": [
            value
            for value in metadata.get_all("Classifier") or []
            if value.startswith("License ::")
        ],
        "license_expression": metadata.get("License-Expression"),
        "license_label": metadata.get("License"),
        "requires_dist": distribution.requires or [],
    }


def provenance_bytes(root: Path) -> bytes:
    """Generate exact development provenance without reading or writing its output.

    Parameters
    ----------
    root : Path
        Repository supplying validated metadata/schema, lock, direct input and
        independently reviewed source selections.

    Returns
    -------
    bytes
        Canonical sorted, indented UTF-8 JSON with one trailing newline.

    Raises
    ------
    CheckFailure
        For unavailable or changed source inputs, interpreter/graph drift,
        changed installed METADATA or incomplete/corrupt original licences.

    Notes
    -----
    The source selection is an authored input, whose complete original bytes
    are bound by the reviewed implementation. Its TypedDict layout describes
    those exact qualified bytes, rather than unchecked received JSON. Artifact
    and official-index digests and historical audit observations are preserved
    source observations; this command does not refetch or rerun them. Current
    active native descriptors derive from their owning bootstrap source pins.
    """
    inventory_bytes(root)
    if platform.python_version() != "3.13.16":
        raise CheckFailure("dependency_interpreter_mismatch", PROVENANCE)
    raw, value = read_object(root, SELECTIONS, 1048576)
    if hashlib.sha256(raw).hexdigest() != SELECTION_SHA256:
        raise CheckFailure("dependency_selection_source_changed", SELECTIONS)
    selected = cast(_SourceSelections, value)
    lock_text = read_text(root, "requirements-dev.txt")
    lock = parse_requirements(lock_text, "requirements-dev.txt", hashed=True)
    direct = parse_requirements(
        read_text(root, "requirements-dev.in"), "requirements-dev.in", hashed=False
    )
    lock_sha = hashlib.sha256(lock_text.encode("utf-8")).hexdigest()
    if lock_sha != selected["lock_sha256"]:
        raise CheckFailure("dependency_lock_binding_mismatch", SELECTIONS)
    if not direct.keys() <= lock.keys() or any(direct[name][0] != lock[name][0] for name in direct):
        raise CheckFailure("dependency_direct_lock_mismatch", "requirements-dev.in")
    installed: dict[str, importlib.metadata.Distribution] = {}
    for distribution in importlib.metadata.distributions():
        try:
            name = distribution.metadata.get("Name")
        except UnicodeError as error:
            raise CheckFailure("dependency_installed_source_mismatch", PROVENANCE) from error
        if not isinstance(name, str) or not name:
            raise CheckFailure("dependency_installed_source_mismatch", PROVENANCE)
        installed.setdefault(canonicalize_name(name), distribution)
    if set(installed) != set(lock):
        raise CheckFailure("dependency_graph_mismatch", PROVENANCE)
    records = [
        _package(source, installed[source["name"]], direct=source["name"] in direct)
        for source in selected["packages"]
    ]
    native = {str(item["role"]): dict(item) for item in selected["native_tools"]}
    for role, source in NATIVE_SOURCES.items():
        native[role] = {
            "role": role,
            "artifact_url": source.url,
            "artifact_sha256": source.archive_sha256,
            "bytes": source.archive_bytes,
            "binary_relative_path": ".tool-cache/native/" + role + "/" + role,
            "binary_sha256": source.binary_sha256,
        }
    output = {
        "schema_revision": "experiment_ledger.local-development-provenance.v1",
        "lock_sha256": lock_sha,
        "python": "3.13.16",
        "supported_range": ">=3.13.16,<3.14",
        "packages": records,
        "native_tools": [native[name] for name in sorted(native)],
        "security_audit": selected["security_audit"],
        "source_selection": {"path": SELECTIONS, "sha256": SELECTION_SHA256},
    }
    return (json.dumps(output, indent=2, sort_keys=True) + "\n").encode("utf-8")
