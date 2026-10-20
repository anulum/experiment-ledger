# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Exercise fixed native entry points, reviewed inputs and actual audit-service failure."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest

from ledger_validation.execution import verify_sources
from ledger_validation.inputs import Json
from ledger_validation.preflight import run_check

from .provenance_support import SOURCE, source_files


def _invoke(
    root: Path, name: str, *, implementation: Path = SOURCE, unavailable_proxy: bool = False
) -> dict[str, Json]:
    environment = dict(os.environ)
    if unavailable_proxy:
        environment.update(
            HTTPS_PROXY="http://127.0.0.1:1",
            https_proxy="http://127.0.0.1:1",
            NO_PROXY="",
            no_proxy="",
        )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "--parallel-mode",
            "--branch",
            "--source="
            + ",".join(
                str(path) for path in (SOURCE / "tools", SOURCE / "tests", implementation / "tools")
            ),
            str(implementation / "tools/check_native_gate.py"),
            "--root",
            str(root),
            "--check",
            name,
            "--json",
        ],
        cwd=SOURCE,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert not result.stderr, result.stderr
    report = cast(dict[str, Json], json.loads(result.stdout))
    assert report["scope"] == "local_scaffold_native_check" and report["check"] == name
    assert report["exit_code"] == result.returncode
    assert report["status"] == {0: "passed", 2: "refused", 3: "unavailable"}[result.returncode]
    return report


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """Prepare a complete byte-identical implementation for native configuration failure inputs.

    Parameters
    ----------
    tmp_path : Path
        Owned Samsung source input directory.

    Returns
    -------
    Path
        Complete actual source snapshot in a fresh unpublished native Git context.
    """
    for name, raw in source_files(SOURCE).items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    subprocess.run(["git", "init", "-q", "--initial-branch=main", str(tmp_path)], check=True)
    return tmp_path


def test_actual_fixed_native_lint_gate() -> None:
    """The public single-gate command reaches actual native Ruff with reviewed configuration."""
    report = _invoke(SOURCE, "source_lint")
    result = cast(dict[str, Json], report["native_result"])
    assert report["exit_code"] == 0 and result["native_exit"] == 0


@pytest.mark.parametrize("name", ["source_lint", "source_format", "strict_types"])
def test_changed_real_analysis_configuration_refuses_before_execution(
    root: Path, name: str
) -> None:
    """A copied actual command cannot consume an unreviewed analysis configuration."""
    path = root / "pyproject.toml"
    path.write_bytes(path.read_bytes() + b"\n")
    report = _invoke(root, name, implementation=root)
    native = cast(dict[str, Json], report["native_result"])
    assert report["exit_code"] == 2 and native["native_exit"] is None
    assert native["finding"] == "dependency_execution_mismatch"


def test_changed_gitleaks_configuration_is_refused_before_native_launch(root: Path) -> None:
    """Credential scans cannot silently replace their selected default-only rule configuration."""
    path = root / "gitleaks.toml"
    path.write_bytes(path.read_bytes() + b"\n")
    report = _invoke(root, "source_credentials", implementation=root)
    native = cast(dict[str, Json], report["native_result"])
    assert report["exit_code"] == 2 and native["native_exit"] is None
    assert native["finding"] == "dependency_execution_mismatch"


def test_real_dependency_advisory_audit_is_complete_and_preserved() -> None:
    """The native audit consumes the selected complete hash lock without installing or changing it."""
    outcome = run_check(SOURCE, "dependency_vulnerabilities")
    assert outcome["status"] == "passed" and outcome["native_exit"] == 0, outcome
    report = cast(dict[str, Json], outcome["report"])
    dependencies = cast(list[Json], report["dependencies"])
    assert len(dependencies) == 103
    assert all(isinstance(item, dict) and item["vulns"] == [] for item in dependencies)


def test_real_advisory_service_unavailability_cannot_qualify(root: Path) -> None:
    """A real refused HTTPS connection leaves the audit unavailable with its nonzero native exit."""
    report = _invoke(root, "dependency_vulnerabilities", unavailable_proxy=True)
    result = cast(dict[str, Json], report["native_result"])
    assert report["exit_code"] == 3 and result["native_exit"] != 0
    assert result["finding"] == "input_invalid"


def test_reviewed_configuration_api_refuses_unclassified_names() -> None:
    """A fixed configuration capability cannot be expanded to arbitrary source names."""
    with pytest.raises(KeyError):
        verify_sources(SOURCE, ("README.md",))


def test_advisory_audit_requires_its_actual_dependency_entry_point(root: Path) -> None:
    """An incomplete actual dependency installation cannot be bypassed by the native audit route."""
    (root / "tools/check_dependency_alignment.py").unlink()
    report = _invoke(root, "dependency_vulnerabilities", implementation=root)
    native = cast(dict[str, Json], report["native_result"])
    prerequisite = cast(dict[str, Json], native["prerequisite"])
    assert report["exit_code"] == 3 and native["native_exit"] is None
    assert prerequisite["finding"] == "checker_unavailable"
