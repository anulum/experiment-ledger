# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Expose the dependency alignment check through its public command."""

from collections.abc import Sequence

from .command import run
from .dependencies import verify


def main(argv: Sequence[str] | None = None) -> int:
    """Return the actual dependency alignment outcome.

    Parameters
    ----------
    argv : Sequence[str] or None
        Explicit command arguments or the process argument sequence.

    Returns
    -------
    int
        Zero for a match, two for refusal, three for unavailable input.
        Argument errors exit four and help exits zero.
    """
    return run(
        "dependency_alignment",
        "local_scaffold_development_environment",
        verify,
        argv,
        description="Check the actual Experiment Ledger development environment.",
    )
