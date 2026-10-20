# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Check the actual maintained source cohort against its selected licence policy."""

import hashlib
import re
import subprocess
from pathlib import Path

from .inputs import CheckFailure, read_bytes, read_object
from .provenance_policy import (
    BINARY_LENGTHS,
    BINARY_SOURCES,
    HEADER,
    LICENCE_SHA256,
    REUSE_SHA256,
    SIDECAR,
)

REQUIRED = frozenset(
    (
        "LICENSE",
        "LICENSES/AGPL-3.0-or-later.txt",
        "REUSE.toml",
        ".zenodo.json",
        "repository-domain.json",
        "capability-inventory.json",
        "dependency-provenance.json",
        "schemas/repository-domain.schema.json",
        *BINARY_SOURCES,
    )
)


def maintained_sources(root: Path) -> tuple[str, ...]:
    """Enumerate tracked and nonignored untracked sources through native Git.

    Parameters
    ----------
    root : Path
        Repository supplying the public source cohort.

    Returns
    -------
    tuple[str, ...]
        Distinct relative source paths in deterministic order.

    Raises
    ------
    CheckFailure
        For unavailable Git, a non-repository root or missing required sources.

    Notes
    -----
    Ignored development environments, internal plans and generated output are
    outside this cohort. Their exclusion is not an inventory/privacy audit.
    """
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "--full-name",
                "-z",
            ],
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise CheckFailure("git_unavailable", ".", unavailable=True) from error
    if result.returncode:
        raise CheckFailure("git_unavailable", ".", unavailable=True)
    names = tuple(
        sorted(set(result.stdout.decode("utf-8", errors="surrogateescape").split("\0")) - {""})
    )
    if not REQUIRED.issubset(names):
        raise CheckFailure("source_inputs_unavailable", ".", unavailable=True)
    return names


def verify(root: Path) -> None:
    """Verify selected licence originals, project headers and JSON sidecars.

    Parameters
    ----------
    root : Path
        Actual local repository with maintained source material.

    Raises
    ------
    CheckFailure
        For missing or altered original licences/asset identities, incomplete
        project notices, conflicting SPDX, invalid JSON or sidecar mismatch.

    Notes
    -----
    This is current local-scaffold source provenance, not installed dependency,
    copyright adjudication, filesystem-race, packaging or full inventory
    qualification. Additional third-party material needs explicit source policy.
    """
    names = maintained_sources(root)
    for name in names:
        raw = read_bytes(root, name, BINARY_LENGTHS.get(name, 1048576))
        if name in ("LICENSE", "LICENSES/AGPL-3.0-or-later.txt"):
            if hashlib.sha256(raw).hexdigest() != LICENCE_SHA256:
                raise CheckFailure("licence_original_changed", name)
        elif name in BINARY_SOURCES:
            if hashlib.sha256(raw).hexdigest() != BINARY_SOURCES[name]:
                raise CheckFailure("asset_source_changed", name)
        elif name.lower().endswith(".json"):
            _, document = read_object(root, name, 1048576)
            if name + ".license" not in names:
                raise CheckFailure("json_sidecar_unavailable", name, unavailable=True)
            if read_bytes(root, name + ".license", 8192) != SIDECAR:
                raise CheckFailure("json_sidecar_mismatch", name)
            for field in ("SPDX-" + "License-Identifier", "spdx_license_identifier"):
                if field in document and document[field] != "AGPL-3.0-or-later":
                    raise CheckFailure("json_licence_conflict", name)
        elif name.endswith(".license"):
            if name[:-8] not in names or not name[:-8].lower().endswith(".json"):
                raise CheckFailure("orphan_licence_sidecar", name)
        else:
            try:
                text = raw.decode("utf-8")
            except UnicodeError as error:
                raise CheckFailure("source_text_invalid", name) from error
            lines = text.splitlines()
            expected = (
                ["<!--", *HEADER, "-->"] if name.endswith(".md") else ["# " + x for x in HEADER]
            )
            if lines[: len(expected)] != expected:
                raise CheckFailure("source_header_mismatch", name)
            for line in lines[len(expected) :]:
                identifier = re.fullmatch(r"(?:# )?SPDX-" + r"License-Identifier: (.+)", line)
                if identifier and identifier[1] != "AGPL-3.0-or-later":
                    raise CheckFailure("conflicting_spdx", name)
            if name == "REUSE.toml" and hashlib.sha256(raw).hexdigest() != REUSE_SHA256:
                raise CheckFailure("reuse_source_changed", name)
