# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Qualify the actual interpreter, locked graph and installed development sources."""

import hashlib
import importlib.metadata
import platform
import re
from pathlib import Path

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

from .execution import verify as verify_execution
from .inputs import CheckFailure, Json, read_bytes, read_object
from .metadata import verify as verify_metadata

PROVENANCE = "dependency-provenance.json"
LOCK = "requirements-dev.txt"


def _text(root: Path, name: str) -> str:
    try:
        return read_bytes(root, name, 1048576).decode("utf-8")
    except UnicodeError as error:
        raise CheckFailure("dependency_text_invalid", name) from error


def _requirements(text: str, name: str, *, hashed: bool) -> dict[str, tuple[str, set[str]]]:
    requirements: dict[str, tuple[str, set[str]]] = {}
    for line in text.replace("\\\n", " ").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!-]+)(.*)", line.strip())
        if match is None:
            raise CheckFailure("dependency_pin_invalid", name)
        package, version, tail = match.groups()
        package = canonicalize_name(package)
        hashes = set(re.findall(r" --hash=sha256:([0-9a-f]{64})(?=\s|$)", tail))
        remaining = re.sub(r" --hash=sha256:[0-9a-f]{64}(?=\s|$)", "", tail).strip()
        if package in requirements or remaining or (hashed and not hashes) or (not hashed and tail):
            raise CheckFailure("dependency_pin_invalid", name)
        requirements[package] = (version, hashes)
    if not requirements:
        raise CheckFailure("dependency_graph_empty", name)
    return requirements


def _object(value: Json) -> dict[str, Json]:
    if not isinstance(value, dict):
        raise CheckFailure("dependency_provenance_invalid", PROVENANCE)
    return value


def _string(value: Json) -> str:
    if not isinstance(value, str):
        raise CheckFailure("dependency_provenance_invalid", PROVENANCE)
    return value


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def verify(root: Path) -> None:
    """Check development declarations against the actual current interpreter graph.

    Parameters
    ----------
    root : Path
        Repository containing the selected hash lock and source provenance.

    Raises
    ------
    CheckFailure
        For unavailable or malformed inputs, drifted lock/interpreter/package
        identities, unpinned requirements, missing hashes, incompatible active
        dependencies, changed installed metadata or licence source bytes.

    Notes
    -----
    No package is installed or imported by this check. The graph is the actual
    interpreter's metadata, including unexpected installed distributions.
    Native workflow tools retain their separate executable-provenance check;
    package metadata cannot establish a native binary's identity.
    """
    verify_metadata(root)
    _, provenance = read_object(root, PROVENANCE, 1048576)
    lock_text = _text(root, LOCK)
    lock = _requirements(lock_text, LOCK, hashed=True)
    direct = _requirements(_text(root, "requirements-dev.in"), "requirements-dev.in", hashed=False)
    if provenance.get("lock_sha256") != _digest(lock_text.encode("utf-8")):
        raise CheckFailure("dependency_lock_binding_mismatch", PROVENANCE)
    actual_python = platform.python_version()
    if provenance.get("python") != actual_python or actual_python != "3.13.16":
        raise CheckFailure("dependency_interpreter_mismatch", PROVENANCE)
    if provenance.get("supported_range") != ">=3.13.16,<3.14":
        raise CheckFailure("dependency_interpreter_range_mismatch", PROVENANCE)
    records = provenance.get("packages")
    if not isinstance(records, list):
        raise CheckFailure("dependency_provenance_invalid", PROVENANCE)
    seen: set[str] = set()
    for value in records:
        record = _object(value)
        name = canonicalize_name(_string(record.get("name")))
        version = _string(record.get("version"))
        artifact = _object(record.get("source_artifact"))
        digest = _string(artifact.get("sha256"))
        if (
            name in seen
            or name not in lock
            or lock[name][0] != version
            or digest not in lock[name][1]
            or not _string(artifact.get("url")).startswith(
                "https://files.pythonhosted.org/packages/"
            )
        ):
            raise CheckFailure("dependency_source_mismatch", PROVENANCE)
        seen.add(name)
        expected_role = "direct" if name in direct else "transitive"
        if record.get("role") != expected_role:
            raise CheckFailure("dependency_role_mismatch", PROVENANCE)
        try:
            distribution = importlib.metadata.distribution(name)
        except importlib.metadata.PackageNotFoundError as error:
            raise CheckFailure(
                "dependency_package_unavailable", PROVENANCE, unavailable=True
            ) from error
        metadata = distribution.read_text("METADATA")
        if (
            distribution.version != version
            or metadata is None
            or _digest(metadata.encode("utf-8")) != record.get("metadata_sha256")
        ):
            raise CheckFailure("dependency_installed_source_mismatch", PROVENANCE)
        installed_metadata = distribution.metadata
        projection: dict[str, object] = {
            "license_classifiers": [
                value
                for value in installed_metadata.get_all("Classifier") or []
                if value.startswith("License ::")
            ],
            "license_expression": installed_metadata.get("License-Expression"),
            "license_label": installed_metadata.get("License"),
            "requires_dist": distribution.requires or [],
        }
        if any(key not in record or record[key] != value for key, value in projection.items()):
            raise CheckFailure("dependency_metadata_projection_mismatch", PROVENANCE)
        required_python = distribution.metadata.get("Requires-Python", "")
        if actual_python not in SpecifierSet(required_python):
            raise CheckFailure("dependency_python_incompatible", PROVENANCE)
        for requirement_text in distribution.requires or []:
            requirement = Requirement(requirement_text)
            if requirement.marker is not None and not requirement.marker.evaluate({"extra": ""}):
                continue
            required = lock.get(canonicalize_name(requirement.name))
            if required is None or required[0] not in requirement.specifier:
                raise CheckFailure("dependency_graph_incompatible", PROVENANCE)
        licences = record.get("license_files")
        if not isinstance(licences, list):
            raise CheckFailure("dependency_provenance_invalid", PROVENANCE)
        declared_licences: set[str] = set()
        for licence in licences:
            source = _object(licence)
            path = Path(_string(source.get("path")))
            if path.is_absolute() or ".." in path.parts:
                raise CheckFailure("dependency_licence_path_invalid", PROVENANCE)
            try:
                raw = distribution.locate_file(path).read_bytes()
            except OSError as error:
                raise CheckFailure(
                    "dependency_licence_unavailable", PROVENANCE, unavailable=True
                ) from error
            if len(raw) != source.get("bytes") or _digest(raw) != source.get("sha256"):
                raise CheckFailure("dependency_licence_mismatch", PROVENANCE)
            declared_licences.add(path.as_posix())
        if len(declared_licences) != len(licences) or declared_licences != installed_licence_names(
            distribution
        ):
            raise CheckFailure("dependency_licence_inventory_mismatch", PROVENANCE)
    installed = {
        canonicalize_name(item.metadata["Name"]) for item in importlib.metadata.distributions()
    }
    if seen != set(lock) or seen != installed:
        raise CheckFailure("dependency_graph_mismatch", PROVENANCE)
    if not direct.keys() <= lock.keys() or any(direct[name][0] != lock[name][0] for name in direct):
        raise CheckFailure("dependency_direct_lock_mismatch", "requirements-dev.in")
    verify_execution(root)


def installed_licence_names(distribution: importlib.metadata.Distribution) -> set[str]:
    """Enumerate original installed licence and attribution files without shrinking their inventory.

    Parameters
    ----------
    distribution : Distribution
        Actual installed distribution and its original file catalogue.

    Returns
    -------
    set[str]
        Relative originals in packaged licence directories, conventional
        licence text files and explicit licence/ABOUT attribution sidecars.

    Raises
    ------
    CheckFailure
        When the actual installed file catalogue is unavailable.
    """
    files = distribution.files
    if files is None:
        raise CheckFailure("dependency_licence_catalog_unavailable", PROVENANCE, unavailable=True)
    names: set[str] = set()
    for path in files:
        in_licences = (
            any(part.endswith(".dist-info") for part in path.parts) and "licenses" in path.parts
        )
        stem = path.name.upper().split(".")[0]
        suffix = path.suffix.lower()
        if (
            in_licences
            or suffix in {".about", ".license"}
            or stem in {"LICENSE", "LICENCE", "COPYING", "COPYRIGHT", "NOTICE", "UNLICENSE"}
            and suffix in {"", ".txt", ".md", ".rst", ".apache", ".bsd", ".unicode", ".lesser"}
        ):
            names.add(str(path))
    return names
