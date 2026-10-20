# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Read exact development declarations and complete installed licence catalogues."""

import importlib.metadata
import re
from pathlib import Path

from packaging.utils import canonicalize_name

from .inputs import CheckFailure, read_bytes

PROVENANCE = "dependency-provenance.json"


def read_text(root: Path, name: str) -> str:
    """Read original UTF-8 development declarations within their byte bound.

    Parameters
    ----------
    root : Path
        Repository supplying the selected declaration.
    name : str
        Fixed relative input name.

    Returns
    -------
    str
        Complete original decoded text.

    Raises
    ------
    CheckFailure
        For missing, oversized or invalid UTF-8 input.
    """
    try:
        return read_bytes(root, name, 1048576).decode("utf-8")
    except UnicodeError as error:
        raise CheckFailure("dependency_text_invalid", name) from error


def parse_requirements(text: str, name: str, *, hashed: bool) -> dict[str, tuple[str, set[str]]]:
    """Parse the complete exact-pin declaration without admitting unclassified syntax.

    Parameters
    ----------
    text : str
        Original requirements text.
    name : str
        Fixed input location used for failure reports.
    hashed : bool
        Require SHA-256 hashes for a lock; refuse hashes in direct input.

    Returns
    -------
    dict[str, tuple[str, set[str]]]
        Canonical package names mapped to exact versions and selected hashes.

    Raises
    ------
    CheckFailure
        For empty declarations, duplicate names or invalid pins/hash syntax.
    """
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
        When the actual installed file catalogue is unavailable or malformed.
    """
    try:
        files = distribution.files
    except (ValueError, TypeError) as error:
        raise CheckFailure("dependency_licence_catalog_invalid", PROVENANCE) from error
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
