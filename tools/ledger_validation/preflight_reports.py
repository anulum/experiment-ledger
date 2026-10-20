# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Write actual preflight outcomes without publishing or exposing partial reports."""

import json
import os
import tempfile
from pathlib import Path

from .inputs import CheckFailure, Json


def write_report(root: Path, path: Path, report: dict[str, Json]) -> None:
    """Atomically replace one requested report inside the owned repository cache.

    Parameters
    ----------
    root : Path
        Resolved actual repository directory.
    path : Path
        Absolute or repository-relative destination within its tool cache.
    report : dict[str, Json]
        Complete actual serialisable validation result.

    Raises
    ------
    CheckFailure
        For an escaped destination or an unavailable output. An unsuccessful
        replacement preserves the existing destination and removes temporary
        bytes written by this call.
    """
    destination = path if path.is_absolute() else root / path
    cache = (root / ".tool-cache").resolve()
    if not cache.is_relative_to(root) or not destination.resolve().is_relative_to(cache):
        raise CheckFailure("report_path_refused", "report")
    temporary: str | None = None
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=destination.parent, delete=False
        ) as stream:
            temporary = stream.name
            json.dump(report, stream, sort_keys=True)
            stream.write("\n")
        os.replace(temporary, destination)
        temporary = None
    except OSError as error:
        raise CheckFailure("report_unavailable", "report", unavailable=True) from error
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)
