# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Prepare complete actual source copies and invoke the real provenance command."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import cast

from ledger_validation.inputs import Json

SOURCE = Path(__file__).resolve().parents[1]
ENTRY = SOURCE / "tools/check_source_provenance.py"


def source_files(root: Path) -> dict[str, bytes]:
    """Read the native Git-maintained source cohort without changing the index.

    Parameters
    ----------
    root : Path
        Repository containing the actual maintained files.

    Returns
    -------
    dict[str, bytes]
        Original relative names and complete file bytes.
    """
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        capture_output=True,
        check=True,
    )
    names = set(result.stdout.decode().split("\0")) - {""}
    return {name: (root / name).read_bytes() for name in names}


def invoke(
    root: Path,
    *arguments: str,
    machine: bool = True,
    explicit_root: bool = True,
    without_git: bool = False,
    isolate_discovery: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Invoke the real public command under native branch measurement.

    Parameters
    ----------
    root : Path
        Actual repository or isolated complete source copy.
    arguments : str
        Additional actual CLI arguments.
    machine : bool
        Request JSON output.
    explicit_root : bool
        Supply the root or rely on the actual current directory.
    without_git : bool
        Exercise the real missing Git dependency with an empty executable PATH.
    isolate_discovery : bool
        Stop native Git parent discovery before the owned test root's parent,
        so a non-repository test cannot inherit the canonical checkout.

    Returns
    -------
    subprocess.CompletedProcess[str]
        Actual native process outcome and unmodified streams.
    """
    command = [
        sys.executable,
        "-m",
        "coverage",
        "run",
        "--parallel-mode",
        "--branch",
        "--source=" + str(SOURCE / "tools") + "," + str(SOURCE / "tests"),
        str(ENTRY),
    ]
    if explicit_root:
        command.extend(("--root", str(root)))
    if machine:
        command.append("--json")
    command.extend(arguments)
    environment = dict(os.environ)
    environment.setdefault("COVERAGE_FILE", str(SOURCE / ".tool-cache/coverage/data"))
    if without_git:
        environment["PATH"] = ""
    if isolate_discovery:
        environment["GIT_CEILING_DIRECTORIES"] = str(root.parent)
    return subprocess.run(
        command,
        cwd=SOURCE if explicit_root else root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
    )


def report(result: subprocess.CompletedProcess[str], expected: int) -> dict[str, Json]:
    """Assert the observed exit/report relationship and return the real report.

    Parameters
    ----------
    result : subprocess.CompletedProcess[str]
        Actual public process result.
    expected : int
        Independently expected native exit.

    Returns
    -------
    dict[str, Json]
        Received machine-readable report.
    """
    assert result.returncode == expected, (result.stdout, result.stderr)
    assert not result.stderr
    value = cast(dict[str, Json], json.loads(result.stdout))
    assert value["check"] == "source_provenance"
    assert value["scope"] == "local_scaffold_source_provenance"
    assert value["exit_code"] == expected
    assert value["status"] == {0: "passed", 2: "refused", 3: "unavailable"}[expected]
    return value
