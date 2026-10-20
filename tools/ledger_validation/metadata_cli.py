# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Expose repository metadata declarations through the actual public command."""

import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .command import ArgumentParser, Arguments, run
from .inputs import CheckFailure
from .metadata import inventory_bytes, verify


def main(argv: Sequence[str] | None = None) -> int:
    """Check metadata with declaration-scoped reports and native exit codes.

    Parameters
    ----------
    argv : Sequence[str] or None
        Actual argument sequence, or process arguments when absent.

    Returns
    -------
    int
        Zero for a match, two for refusal, three for unavailable input.
        Invalid arguments exit four; help exits zero.
    """
    return run(
        "repository_metadata",
        "local_scaffold_declarations",
        verify,
        argv,
        description="Check Experiment Ledger repository metadata declarations.",
    )


def generate_main(argv: Sequence[str] | None = None) -> int:
    """Emit a reproducible capability inventory without modifying repository files.

    Parameters
    ----------
    argv : Sequence[str] or None
        Actual command arguments, or process arguments when absent.

    Returns
    -------
    int
        Zero with canonical JSON on stdout, two for refused source, or three
        for unavailable source. Failure findings go to stderr, leaving stdout
        empty. Invalid arguments exit four; help exits zero.
    """
    parser = ArgumentParser(
        prog="generate_capability_inventory",
        description="Generate the canonical Experiment Ledger capability inventory.",
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    options = Arguments()
    parser.parse_args(argv, namespace=options)
    try:
        raw = inventory_bytes(options.root)
    except CheckFailure as error:
        print(
            json.dumps({"code": error.code, "location": error.location}, sort_keys=True),
            file=sys.stderr,
        )
        return error.exit_code
    sys.stdout.buffer.write(raw)
    return 0
