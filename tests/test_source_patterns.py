# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Exercise complete native scan binding while retaining every original advisory."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest

from ledger_validation.inputs import CheckFailure, Json, decode_object
from ledger_validation.preflight import run_check
from ledger_validation.source_pattern_review import review_report

from .provenance_support import SOURCE, source_files


@pytest.fixture(scope="module")
def native_report() -> bytes:
    """Obtain the complete original all-severity native Bandit report.

    Returns
    -------
    bytes
        Native exit-one report preserving every current advisory.
    """
    result = subprocess.run(
        [sys.executable, "-m", "bandit", "-r", "tools", "-q", "-f", "json"],
        cwd=SOURCE,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 1 and not result.stderr
    assert len(json.loads(result.stdout)["results"]) == 9
    return result.stdout


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """Copy complete actual sources into an isolated unpublished native Git repository.

    Parameters
    ----------
    tmp_path : Path
        Owned Samsung test input directory.

    Returns
    -------
    Path
        Complete native-source input without shared environment/cache mutation.
    """
    for name, raw in source_files(SOURCE).items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    subprocess.run(["git", "init", "-q", "--initial-branch=main", str(tmp_path)], check=True)
    return tmp_path


def test_original_native_report_and_exit_are_preserved(native_report: bytes) -> None:
    """Exact source-bound qualification returns every original native advisory unchanged."""
    assert review_report(SOURCE, native_report, native_exit=1) == json.loads(native_report)
    result = run_check(SOURCE, "source_patterns")
    assert result["status"] == "passed" and result["native_exit"] == 1
    report = result["report"]
    assert isinstance(report, dict) and len(cast(list[Json], report["results"])) == 9
    assert len(cast(list[Json], result["review_dispositions"])) == 4


@pytest.mark.parametrize("native_exit", [0, 2, -9])
def test_actual_report_cannot_replace_its_native_exit(
    native_report: bytes, native_exit: int
) -> None:
    """A zero/special native exit cannot silently dispose the expected visible advisories."""
    with pytest.raises(CheckFailure):
        review_report(SOURCE, native_report, native_exit=native_exit)


@pytest.mark.parametrize("member", ["errors", "metrics", "results", "extra"])
def test_invalid_native_report_shapes_refuse(native_report: bytes, member: str) -> None:
    """A malformed native report or a native scan error cannot qualify source."""
    report = cast(dict[str, Json], json.loads(native_report))
    report[member] = ["controlled native error"] if member == "errors" else None
    with pytest.raises(CheckFailure) as error:
        review_report(SOURCE, json.dumps(report).encode(), native_exit=1)
    assert error.value.code == "source_pattern_report_invalid"


@pytest.mark.parametrize(
    "change", ["totals", "nosec", "skipped_tests", "boolean", "missing_source"]
)
def test_incomplete_or_suppressed_scan_refuses(native_report: bytes, change: str) -> None:
    """Whole-source enrolment and unfiltered native scan counters cannot be reduced."""
    report = cast(dict[str, Json], json.loads(native_report))
    metrics = cast(dict[str, Json], report["metrics"])
    if change == "totals":
        metrics["_totals"] = None
    elif change == "missing_source":
        del metrics["tools/check_repository_metadata.py"]
    else:
        totals = cast(dict[str, Json], metrics["_totals"])
        totals["nosec" if change == "boolean" else change] = True if change == "boolean" else 1
    with pytest.raises(CheckFailure) as error:
        review_report(SOURCE, json.dumps(report).encode(), native_exit=1)
    assert error.value.code == "source_pattern_scan_incomplete"


@pytest.mark.parametrize("change", ["missing", "duplicate", "severity", "code", "wrong_shape"])
def test_changed_advisory_identity_requires_new_review(native_report: bytes, change: str) -> None:
    """Missing, repeated, rewritten or newly severe original findings cannot reuse a disposition."""
    report = cast(dict[str, Json], json.loads(native_report))
    results = cast(list[Json], report["results"])
    if change == "missing":
        results.pop()
    elif change == "duplicate":
        results.append(results[0])
    elif change == "wrong_shape":
        results[0] = None
    else:
        finding = cast(dict[str, Json], results[0])
        finding["issue_severity" if change == "severity" else "code"] = (
            "HIGH" if change == "severity" else "rewritten native excerpt"
        )
    with pytest.raises(CheckFailure) as error:
        review_report(SOURCE, json.dumps(report).encode(), native_exit=1)
    assert error.value.code == "source_pattern_findings_mismatch"


def test_changed_real_source_cannot_reuse_an_original_report(
    root: Path, native_report: bytes
) -> None:
    """Even a harmless original source-byte change invalidates an earlier author disposition."""
    path = root / "tools/ledger_validation/processes.py"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(CheckFailure) as error:
        review_report(root, native_report, native_exit=1)
    assert error.value.code == "source_pattern_source_mismatch"


def test_unreadable_original_source_is_unavailable(root: Path, native_report: bytes) -> None:
    """An unreadable actual source cannot inherit qualification from its earlier report."""
    path = root / "tools/ledger_validation/processes.py"
    path.chmod(0)
    try:
        with pytest.raises(CheckFailure) as error:
            review_report(root, native_report, native_exit=1)
        assert error.value.exit_code == 3
    finally:
        path.chmod(0o600)


def test_new_actual_native_finding_is_visible_and_refused(root: Path) -> None:
    """The real scanner retains a newly enrolled unreviewed assertion finding through the parent."""
    (root / "tools/controlled_native_input.py").write_text("assert False\n")
    result = run_check(root, "source_patterns")
    assert result["status"] == "refused" and result["native_exit"] == 1
    assert result["finding"] == "source_pattern_findings_mismatch"
    report = cast(dict[str, Json], result["report"])
    assert len(cast(list[Json], report["results"])) == 10


def test_real_invalid_native_configuration_cannot_qualify(root: Path) -> None:
    """An actual malformed native configuration remains a failed native scan."""
    (root / "tools/.bandit").write_text("[invalid native configuration\n")
    result = run_check(root, "source_patterns")
    assert result["status"] == "refused"
    assert result["finding"] == "source_pattern_report_invalid"


def test_oversized_received_native_bytes_refuse_before_decoding() -> None:
    """The shared public byte decoder enforces its declared bound without parsing excess input."""
    with pytest.raises(CheckFailure) as error:
        decode_object(b" " * 1048577, "bandit_report", 1048576)
    assert error.value.code == "input_too_large"


def test_actual_public_source_pattern_command_retains_original_advisories() -> None:
    """The native public entry point exposes qualified status alongside native exit one and warnings."""
    command = [
        sys.executable,
        "-m",
        "coverage",
        "run",
        "--parallel-mode",
        "--branch",
        "--source=" + str(SOURCE / "tools") + "," + str(SOURCE / "tests"),
        str(SOURCE / "tools/check_native_gate.py"),
        "--check",
        "source_patterns",
    ]
    for arguments, expected in [(["--json"], 0), ([], 0), (["--help"], 0), (["--unknown"], 4)]:
        result = subprocess.run(
            [*command, *arguments],
            cwd=SOURCE,
            env=dict(os.environ),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == expected
        if arguments == ["--json"]:
            report = json.loads(result.stdout)
            assert report["native_result"]["native_exit"] == 1
            assert len(report["native_result"]["report"]["results"]) == 9
        elif not arguments:
            assert result.stdout == "source_patterns: passed\n"
