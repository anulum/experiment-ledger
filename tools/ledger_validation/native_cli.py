# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Expose native tool verification and explicit missing-tool retrieval."""

import json
from collections.abc import Sequence
from pathlib import Path

from .command import ArgumentParser, Arguments
from .inputs import CheckFailure
from .native_tools import NATIVE_SOURCES, ensure_tool


class NativeArguments(Arguments):
    """Typed bootstrap invocation options.

    Attributes
    ----------
    only : list[str] or None
        Selected classified tools; None verifies all selected originals.
    download : bool
        Explicit permission to retrieve missing originals.
    """

    only: list[str] | None
    download: bool


def main(argv: Sequence[str] | None = None) -> int:
    """Verify selected native bytes and optionally retrieve missing tools.

    Parameters
    ----------
    argv : Sequence[str] or None
        Public command arguments or the process argument sequence.

    Returns
    -------
    int
        Zero when every selected original qualifies; two for refused bytes,
        three for unavailable input, four for invalid arguments. Help exits zero.
    """
    parser = ArgumentParser(prog="native_tools", description="Verify selected native tool bytes.")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--only", nargs="+", choices=tuple(NATIVE_SOURCES))
    parser.add_argument("--download", action="store_true")
    options = NativeArguments()
    parser.parse_args(argv, namespace=options)
    findings: list[dict[str, str]] = []
    exit_code = 0
    for name in options.only or NATIVE_SOURCES:
        try:
            ensure_tool(options.root, name, download=options.download)
        except CheckFailure as error:
            exit_code = max(exit_code, error.exit_code)
            findings.append({"code": error.code, "location": error.location})
    status = {0: "passed", 2: "refused", 3: "unavailable"}[exit_code]
    report = {
        "check": "native_tools",
        "scope": "local_scaffold_native_tools",
        "status": status,
        "exit_code": exit_code,
        "findings": findings,
    }
    print(json.dumps(report, sort_keys=True) if options.json else "native_tools: " + status)
    return exit_code
