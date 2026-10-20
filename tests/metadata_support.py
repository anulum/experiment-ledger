# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Native CLI invocation and isolated declaration inputs for metadata tests."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import cast

from ledger_validation.inputs import Json

SOURCE = Path(__file__).resolve().parents[1]
ENTRY = SOURCE / "tools/check_repository_metadata.py"
INPUTS = (
    "repository-domain.json",
    "schemas/repository-domain.schema.json",
    "capability-inventory.json",
    "requirements-dev.txt",
)


def _run(
    root: Path, *arguments: str, machine: bool = True, explicit_root: bool = True
) -> subprocess.CompletedProcess[str]:
    """Invoke the actual CLI in a separately measured interpreter.

    Parameters
    ----------
    root : Path
        Actual input directory.
    arguments : str
        Additional public CLI arguments.
    machine : bool
        Select the documented JSON report.
    explicit_root : bool
        Supply the root option or use the actual current directory.

    Returns
    -------
    subprocess.CompletedProcess[str]
        Native exit and original output streams.
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
    return subprocess.run(
        command,
        cwd=SOURCE if explicit_root else root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )


def _snapshot(root: Path) -> dict[str, bytes]:
    """Retain the complete fixture file bytes to detect unintended changes.

    Parameters
    ----------
    root : Path
        Isolated repository input directory.

    Returns
    -------
    dict[str, bytes]
        Original relative file names and bytes.
    """
    return {
        str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()
    }


def _generate(root: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    """Invoke the real inventory generator with measured original output bytes.

    Parameters
    ----------
    root : Path
        Source declarations passed to the public generator.
    arguments : str
        Additional received command arguments.

    Returns
    -------
    subprocess.CompletedProcess[bytes]
        Native status and unmodified stdout/stderr bytes.
    """
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "--parallel-mode",
            "--branch",
            "--source=" + str(SOURCE / "tools") + "," + str(SOURCE / "tests"),
            str(SOURCE / "tools/generate_capability_inventory.py"),
            "--root",
            str(root),
            *arguments,
        ],
        cwd=root,
        env=dict(os.environ),
        capture_output=True,
        timeout=15,
    )


def _report(result: subprocess.CompletedProcess[str], expected: int) -> dict[str, Json]:
    """Check native exit semantics and return the actual JSON object.

    Parameters
    ----------
    result : subprocess.CompletedProcess[str]
        Actual CLI process result.
    expected : int
        Required native exit code.

    Returns
    -------
    dict[str, Json]
        Original decoded report.
    """
    assert result.returncode == expected, (result.stdout, result.stderr)
    assert result.stderr == ""
    value = cast(dict[str, Json], json.loads(result.stdout))
    assert value["exit_code"] == expected
    assert value["check"] == "repository_metadata"
    assert value["scope"] == "local_scaffold_declarations"
    return value


def _rewrite_metadata(root: Path, data: dict[str, Json]) -> None:
    """Write fixture metadata and independently refresh its inventory digest.

    Parameters
    ----------
    root : Path
        Isolated repository input directory.
    data : dict[str, Json]
        Complete intended metadata object.
    """
    path = root / "repository-domain.json"
    path.write_text(json.dumps(data) + "\n")
    inventory_path = root / "capability-inventory.json"
    inventory = cast(dict[str, Json], json.loads(inventory_path.read_text()))
    source = inventory["source_metadata"]
    assert isinstance(source, dict)
    source["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    inventory_path.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n")
