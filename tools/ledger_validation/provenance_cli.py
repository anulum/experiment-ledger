# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Expose the maintained-source provenance check through the public command."""

from collections.abc import Sequence

from .command import run
from .provenance import verify


def main(argv: Sequence[str] | None = None) -> int:
    """Check maintained-source provenance without changing repository content.

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
        "source_provenance",
        "local_scaffold_source_provenance",
        verify,
        argv,
        description="Check Experiment Ledger maintained-source provenance.",
    )
