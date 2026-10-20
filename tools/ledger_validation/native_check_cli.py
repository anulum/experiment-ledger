# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Expose fixed native quality gates with original exits and complete structured outcomes."""

import json
from collections.abc import Sequence
from pathlib import Path

from .command import ArgumentParser, Arguments
from .preflight import run_check
from .validation_profile import LEAF_CHECKS, commands


class NativeCheckArguments(Arguments):
    """Typed options for one classified native quality gate.

    Attributes
    ----------
    check : str
        Required selected native role from the owned fixed execution profile.
    """

    check: str


def main(argv: Sequence[str] | None = None) -> int:
    """Run one classified native gate and preserve its original exit and outcome.

    Parameters
    ----------
    argv : Sequence[str] or None
        Public command arguments or the process argument sequence.

    Returns
    -------
    int
        Zero for a qualified native gate, two for refusal, three
        for unavailable inputs, four for invalid arguments. Help exits zero.
    """
    parser = ArgumentParser(
        prog="native_gate", description="Run one classified native quality gate."
    )
    parser.add_argument(
        "--check",
        choices=tuple(name for name in commands(Path(".")) if name not in LEAF_CHECKS),
        required=True,
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--json", action="store_true")
    options = NativeCheckArguments()
    parser.parse_args(argv, namespace=options)
    outcome = run_check(options.root.resolve(), options.check)
    exit_code = (
        3 if outcome["status"] == "unavailable" else 0 if outcome["status"] == "passed" else 2
    )
    status = {0: "passed", 2: "refused", 3: "unavailable"}[exit_code]
    report = {
        "check": options.check,
        "scope": "local_scaffold_native_check",
        "status": status,
        "exit_code": exit_code,
        "native_result": outcome,
    }
    print(json.dumps(report, sort_keys=True) if options.json else options.check + ": " + status)
    return exit_code
