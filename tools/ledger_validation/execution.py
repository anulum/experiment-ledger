# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Bind reviewed source execution configuration to the actual development graph."""

import hashlib
from collections.abc import Iterable
from pathlib import Path

from .inputs import CheckFailure, read_bytes

# Reviewed configuration identities complement installed-package and semantic
# workflow checks. Any configuration change requires an owned review/update.
EXECUTION_SOURCE_DIGESTS = {
    "Makefile": "39cc4a11eb5a44ecb470667000cbb9cfa82beaff70304962ec790c0f1c0f3a94",
    ".pre-commit-config.yaml": "5689b68352e748d8e38574d3ce31a15669d95fae2c8d793b2b9f0b3164201107",
    "pyproject.toml": "3b23ff08cf054597cc979285b979610d563293e0fd95fc63e98a93ff526b1eec",
    "gitleaks.toml": "b49fb6c68ad107e0dcc00ab27f4948898006e6e5399e1645065883f6566666d2",
}


def verify(root: Path) -> None:
    """Verify the complete reviewed Make, hook, analysis and CI execution graph.

    Parameters
    ----------
    root : Path
        Repository supplying the actual source configuration and workflows.

    Raises
    ------
    CheckFailure
        For missing or changed reviewed configuration or semantic workflow
        drift in triggers, exact toolchain/hash install, native bootstrap,
        permissions, provenance, classified jobs or execution commands.

    Notes
    -----
    Exact configuration identities preserve the reviewed lint/type/coverage
    floor, serial execution and entry-point wiring. Actual installed versions,
    lock hashes, native executable identities and original licence bytes keep
    their separate mandatory checks; configuration bytes do not establish them.
    """
    from .workflows import verify as verify_workflows

    verify_sources(root, EXECUTION_SOURCE_DIGESTS)
    verify_workflows(root)


def verify_sources(root: Path, names: Iterable[str]) -> None:
    """Require selected reviewed native configuration before its consuming command runs.

    Parameters
    ----------
    root : Path
        Actual directory supplying the configuration used by a native command.
    names : Iterable[str]
        Selected declared configuration names from EXECUTION_SOURCE_DIGESTS.

    Raises
    ------
    CheckFailure
        For unavailable or changed configuration bytes.
    KeyError
        For an unclassified source configuration name.
    """
    for name in names:
        digest = EXECUTION_SOURCE_DIGESTS[name]
        if hashlib.sha256(read_bytes(root, name, 1048576)).hexdigest() != digest:
            raise CheckFailure("dependency_execution_mismatch", name)
