# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Expose actual development provenance regeneration through its public command."""

import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .command import ArgumentParser, Arguments
from .dependency_generation import provenance_bytes
from .inputs import CheckFailure


def main(argv: Sequence[str] | None = None) -> int:
    """Emit complete provenance bytes or a fixed source failure without changing files.

    Parameters
    ----------
    argv : Sequence[str] or None
        Explicit arguments or the actual process arguments when absent.

    Returns
    -------
    int
        Zero with complete JSON on stdout, two for refused inputs, three for
        unavailable inputs. Failures use stderr and leave stdout empty;
        argument errors exit four and help exits zero.
    """
    parser = ArgumentParser(
        prog="generate_dependency_provenance",
        description="Generate Experiment Ledger development provenance from selected original sources.",
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    options = Arguments()
    parser.parse_args(argv, namespace=options)
    try:
        raw = provenance_bytes(options.root)
    except CheckFailure as error:
        print(
            json.dumps({"code": error.code, "location": error.location}, sort_keys=True),
            file=sys.stderr,
        )
        return error.exit_code
    sys.stdout.buffer.write(raw)
    return 0
