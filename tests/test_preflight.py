# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Exercise actual checker supervision, report semantics and incomplete diagnostics."""

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import pytest

from ledger_validation.inputs import Json
from ledger_validation.preflight import read_checker_report, run_check

from .provenance_support import SOURCE, source_files


def _invoke(
    root: Path, *arguments: str, implementation: Path = SOURCE
) -> subprocess.CompletedProcess[str]:
    sources = [SOURCE / "tools", SOURCE / "tests", implementation / "tools"]
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "--parallel-mode",
            "--branch",
            "--source=" + ",".join(str(path) for path in sources),
            str(implementation / "tools/preflight.py"),
            "--root",
            str(root),
            *arguments,
        ],
        cwd=SOURCE,
        env=dict(os.environ),
        capture_output=True,
        text=True,
        timeout=30,
    )


def _report(process: subprocess.CompletedProcess[str], expected: int) -> dict[str, Json]:
    assert process.returncode == expected, (process.stdout, process.stderr)
    assert not process.stderr
    report = cast(dict[str, Json], json.loads(process.stdout))
    assert report["check"] == "preflight" and report["profile"] == "local-scaffold"
    assert report["exit_code"] == expected
    assert report["status"] == {0: "passed", 2: "refused", 3: "unavailable"}[expected]
    return report


@pytest.fixture(scope="module")
def actual_report() -> bytes:
    """Obtain original report bytes from the actual public metadata checker.

    Returns
    -------
    bytes
        Actual native successful report, used as parser input before mutations.
    """
    result = subprocess.run(
        [
            sys.executable,
            str(SOURCE / "tools/check_repository_metadata.py"),
            "--root",
            str(SOURCE),
            "--json",
        ],
        capture_output=True,
        check=True,
    )
    assert not result.stderr
    return result.stdout


@pytest.fixture(scope="module")
def source_copy(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create one byte-identical actual implementation for incomplete-install cases.

    Parameters
    ----------
    tmp_path_factory : pytest.TempPathFactory
        Samsung scratch allocator.

    Returns
    -------
    Path
        Complete actual public source copy, with no copied cache/environment.
    """
    root = tmp_path_factory.mktemp("preflight-source")
    for name, raw in source_files(SOURCE).items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        assert target.read_bytes() == raw
    subprocess.run(["git", "init", "-q", "--initial-branch=main", str(root)], check=True)
    return root


@pytest.fixture
def root(source_copy: Path) -> Iterator[Path]:
    """Restore only owned case-specific source changes after each native invocation.

    Parameters
    ----------
    source_copy : Path
        Isolated actual implementation.

    Yields
    ------
    Path
        Complete source candidate.
    """
    before = source_files(source_copy)
    yield source_copy
    for name, raw in before.items():
        target = source_copy / name
        if not target.exists() or target.read_bytes() != raw:
            target.write_bytes(raw)


def test_original_native_report_has_exact_outcome_semantics(actual_report: bytes) -> None:
    """Original complete native bytes are accepted for their actual owning scope and exit."""
    value = read_checker_report(
        actual_report,
        b"",
        name="repository_metadata",
        scope="local_scaffold_declarations",
        native_exit=0,
    )
    assert value == json.loads(actual_report)


@pytest.mark.parametrize(
    ("member", "value"),
    [
        ("check", "another_checker"),
        ("scope", "another_scope"),
        ("status", "not_run"),
        ("exit_code", False),
        ("exit_code", 2),
        ("findings", {}),
        ("findings", [{"code": "unexecuted", "location": "."}]),
        ("unexpected", True),
    ],
)
def test_mismatched_native_report_members_refuse(
    actual_report: bytes, member: str, value: Json
) -> None:
    """Actual report mutations cannot change ownership, native exit or complete-pass meaning."""
    data = cast(dict[str, Json], json.loads(actual_report))
    data[member] = value
    assert (
        read_checker_report(
            json.dumps(data).encode(),
            b"",
            name="repository_metadata",
            scope="local_scaffold_declarations",
            native_exit=0,
        )
        is None
    )


@pytest.mark.parametrize(
    "raw", [b"{", b"[]", b"null", b"\xff", b'{"x":1,"x":1}', b'{"x":NaN}', b'{"x":"\\ud800"}']
)
def test_malformed_original_checker_bytes_refuse(raw: bytes) -> None:
    """Malformed, ambiguous or nonfinite received JSON cannot represent checker success."""
    assert (
        read_checker_report(
            raw, b"", name="repository_metadata", scope="local_scaffold_declarations", native_exit=0
        )
        is None
    )


@pytest.mark.parametrize("native_exit", [1, 4, -9])
def test_unreported_native_exit_cannot_pass(actual_report: bytes, native_exit: int) -> None:
    """A successful JSON payload cannot change an actual failed process exit."""
    assert (
        read_checker_report(
            actual_report,
            b"",
            name="repository_metadata",
            scope="local_scaffold_declarations",
            native_exit=native_exit,
        )
        is None
    )


@pytest.mark.parametrize("extra", [0, 1])
def test_original_report_byte_boundary(actual_report: bytes, extra: int) -> None:
    """Whitespace-preserved original reports fit at the exact bound and refuse one more byte."""
    raw = actual_report + b" " * (1048576 + extra - len(actual_report))
    result = read_checker_report(
        raw, b"", name="repository_metadata", scope="local_scaffold_declarations", native_exit=0
    )
    assert (result is None) == bool(extra)


def test_stderr_is_not_silently_dropped(actual_report: bytes) -> None:
    """A structured successful report with an unexpected native diagnostic is refused."""
    assert (
        read_checker_report(
            actual_report,
            b"unexpected diagnostic",
            name="repository_metadata",
            scope="local_scaffold_declarations",
            native_exit=0,
        )
        is None
    )


def test_real_single_checker_and_native_compatibility() -> None:
    """Actual metadata and installed compatibility commands preserve native successful exits."""
    metadata = run_check(SOURCE, "repository_metadata")
    assert metadata["status"] == "passed" and metadata["native_exit"] == 0
    compatibility = run_check(SOURCE, "installed_compatibility")
    assert compatibility["status"] == "passed" and compatibility["native_exit"] == 0


def test_diagnostic_subset_never_reports_complete_pass() -> None:
    """A real successful selected checker leaves all other gates explicitly not_run."""
    report = _report(_invoke(SOURCE, "--only", "repository_metadata", "--json"), 2)
    checks = report["checks"]
    assert isinstance(checks, list) and len(checks) > 6 and isinstance(checks[0], dict)
    assert checks[0]["status"] == "passed"
    assert all(isinstance(item, dict) and item["status"] == "not_run" for item in checks[1:])


def test_missing_checker_in_actual_install_is_unavailable(root: Path) -> None:
    """An incomplete copy of the real implementation cannot replace its missing checker with a pass."""
    (root / "tools/check_repository_metadata.py").unlink()
    report = _report(
        _invoke(root, "--only", "repository_metadata", "--json", implementation=root), 3
    )
    checks = report["checks"]
    assert isinstance(checks, list) and isinstance(checks[0], dict)
    assert checks[0]["finding"] == "checker_unavailable"


def test_missing_native_binary_is_unavailable(root: Path) -> None:
    """A genuine implementation without its selected actionlint binary remains unavailable."""
    path = root / ".tool-cache/native/actionlint/actionlint"
    path.unlink(missing_ok=True)
    report = _report(_invoke(root, "--only", "workflow_syntax", "--json", implementation=root), 3)
    assert report["status"] == "unavailable"


def test_changed_native_binary_is_never_executed(root: Path) -> None:
    """Received executable bytes must match the selected original before launch."""
    path = root / ".tool-cache/native/actionlint/actionlint"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"not the selected executable")
    report = _report(_invoke(root, "--only", "workflow_syntax", "--json", implementation=root), 2)
    checks = report["checks"]
    assert isinstance(checks, list)
    assert any(
        isinstance(item, dict) and item.get("finding") == "native_source_mismatch"
        for item in checks
    )


def test_unavailable_received_input_preserves_native_leaf_report(tmp_path: Path) -> None:
    """A real checker exit-three report remains unavailable through the parent CLI."""
    report = _report(_invoke(tmp_path, "--only", "repository_metadata", "--json"), 3)
    checks = report["checks"]
    assert isinstance(checks, list) and isinstance(checks[0], dict)
    assert checks[0]["status"] == "unavailable" and checks[0]["native_exit"] == 3


def test_unknown_profile_and_public_help() -> None:
    """Unknown profiles/roles use the fixed argument failure and real help remains available."""
    assert _invoke(SOURCE, "--help").returncode == 0
    assert _invoke(SOURCE, "--profile", "unknown").returncode == 4
    assert _invoke(SOURCE, "--only", "unknown").returncode == 4
    human = _invoke(SOURCE, "--only", "repository_metadata")
    assert human.returncode == 2 and human.stdout == "preflight: refused\n"


@pytest.fixture
def refused_report(root: Path) -> bytes:
    """Obtain real refusal bytes from an altered actual metadata input.

    Parameters
    ----------
    root : Path
        Owned actual source copy restored after the case.

    Returns
    -------
    bytes
        Actual metadata checker refusal report with its native nonzero exit.
    """
    (root / "repository-domain.json").write_bytes(b"{")
    result = subprocess.run(
        [
            sys.executable,
            str(SOURCE / "tools/check_repository_metadata.py"),
            "--root",
            str(root),
            "--json",
        ],
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == 2 and not result.stderr
    return result.stdout


def test_original_refusal_report_is_preserved(refused_report: bytes) -> None:
    """An actual native refusal is a valid report and cannot become a pass."""
    assert read_checker_report(
        refused_report,
        b"",
        name="repository_metadata",
        scope="local_scaffold_declarations",
        native_exit=2,
    ) == json.loads(refused_report)


@pytest.mark.parametrize(
    "finding",
    [
        None,
        [],
        {"code": "input_invalid"},
        {"code": 1, "location": "."},
        {"code": "input_invalid", "location": False},
    ],
)
def test_malformed_refusal_finding_is_rejected(refused_report: bytes, finding: Json) -> None:
    """Received findings require the complete original string-valued public shape."""
    data = cast(dict[str, Json], json.loads(refused_report))
    data["findings"] = [finding]
    assert (
        read_checker_report(
            json.dumps(data).encode(),
            b"",
            name="repository_metadata",
            scope="local_scaffold_declarations",
            native_exit=2,
        )
        is None
    )


def test_refusal_without_its_finding_is_rejected(refused_report: bytes) -> None:
    """A nonzero native report cannot discard the diagnostic that explains its refusal."""
    data = cast(dict[str, Json], json.loads(refused_report))
    data["findings"] = []
    assert (
        read_checker_report(
            json.dumps(data).encode(),
            b"",
            name="repository_metadata",
            scope="local_scaffold_declarations",
            native_exit=2,
        )
        is None
    )


def test_actual_failed_leaf_is_preserved_by_parent(root: Path) -> None:
    """Invalid actual metadata stays refused through the orchestrator's public CLI."""
    (root / "repository-domain.json").write_bytes(b"{")
    report = _report(_invoke(root, "--only", "repository_metadata", "--json"), 2)
    checks = report["checks"]
    assert isinstance(checks, list) and isinstance(checks[0], dict)
    assert checks[0]["status"] == "refused" and checks[0]["native_exit"] == 2


def test_missing_leaf_implementation_cannot_masquerade_as_structured_report(root: Path) -> None:
    """A native import failure is refused even when the public entry script still exists."""
    (root / "tools/ledger_validation/metadata.py").unlink()
    report = _report(
        _invoke(root, "--only", "repository_metadata", "--json", implementation=root), 2
    )
    checks = report["checks"]
    assert isinstance(checks, list) and isinstance(checks[0], dict)
    assert checks[0]["finding"] == "checker_report_invalid"
    assert checks[0]["native_exit"] == 1


def test_actual_native_source_tools_keep_their_qualified_outcomes() -> None:
    """Selected original actionlint and Gitleaks bytes inspect actual maintained sources."""
    for name in ("workflow_syntax", "source_credentials"):
        result = run_check(SOURCE, name)
        assert result["status"] == "passed" and result["native_exit"] == 0, result


@pytest.mark.parametrize("destination", [".tool-cache/reports/result.json", "result.json"])
def test_parent_report_output_matches_its_actual_public_outcome(
    root: Path, destination: str
) -> None:
    """The parent writes its complete incomplete-profile outcome only inside owned cache."""
    process = _invoke(root, "--only", "repository_metadata", "--json", "--report", destination)
    report = _report(process, 2)
    path = root / destination
    if destination.startswith(".tool-cache/"):
        assert json.loads(path.read_bytes()) == report
    else:
        assert not path.exists()
        assert report["findings"] == [{"code": "report_path_refused", "location": "report"}]


def test_unavailable_parent_report_output_cannot_keep_refused_exit(root: Path) -> None:
    """A real output directory replacement failure raises parent severity to unavailable."""
    path = root / ".tool-cache/reports/unavailable.json"
    path.mkdir(parents=True)
    report = _report(
        _invoke(root, "--only", "repository_metadata", "--json", "--report", str(path)), 3
    )
    assert report["findings"] == [{"code": "report_unavailable", "location": "report"}]
    assert path.is_dir() and list(path.iterdir()) == []


def test_unavailable_native_process_cache_preserves_owned_refusal(tmp_path: Path) -> None:
    """A real blocked child cache is reported unavailable before any native tool can pass."""
    (tmp_path / ".tool-cache").write_bytes(b"controlled invalid cache type")
    result = run_check(tmp_path, "installed_compatibility")
    assert result == {
        "check": "installed_compatibility",
        "status": "unavailable",
        "native_exit": None,
        "finding": "child_unavailable",
    }


@pytest.mark.parametrize("state", ["changed", "nonexecutable"])
def test_workflow_gate_verifies_shellcheck_before_native_analysis(root: Path, state: str) -> None:
    """Actionlint cannot launch an unqualified ShellCheck dependency from the actual cache."""
    actionlint = root / ".tool-cache/native/actionlint/actionlint"
    actionlint.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE / ".tool-cache/native/actionlint/actionlint", actionlint)
    shellcheck = root / ".tool-cache/native/shellcheck/shellcheck"
    shellcheck.parent.mkdir(parents=True, exist_ok=True)
    shellcheck.write_bytes(
        b"unselected executable"
        if state == "changed"
        else (SOURCE / ".tool-cache/native/shellcheck/shellcheck").read_bytes()
    )
    report = _report(_invoke(root, "--only", "workflow_syntax", "--json", implementation=root), 2)
    checks = cast(list[Json], report["checks"])
    outcomes = [
        item for item in checks if isinstance(item, dict) and item["check"] == "workflow_syntax"
    ]
    expected = "native_source_mismatch" if state == "changed" else "native_not_executable"
    assert outcomes[0]["finding"] == expected and outcomes[0]["native_exit"] is None


@pytest.mark.parametrize("state", ["missing", "changed", "nonexecutable"])
def test_compatibility_verifies_the_installer_before_execution(root: Path, state: str) -> None:
    """Installed compatibility cannot execute absent, changed or nonexecutable uv bytes."""
    installer = root / ".tool-cache/native/uv/uv"
    installer.unlink(missing_ok=True)
    installer.parent.mkdir(parents=True, exist_ok=True)
    if state != "missing":
        installer.write_bytes(
            b"unselected installer"
            if state == "changed"
            else (SOURCE / ".tool-cache/native/uv/uv").read_bytes()
        )
        installer.chmod(0o755 if state == "changed" else 0o644)
    process = _invoke(root, "--only", "installed_compatibility", "--json", implementation=root)
    report = _report(process, 3 if state == "missing" else 2)
    checks = cast(list[Json], report["checks"])
    outcome = next(
        item
        for item in checks
        if isinstance(item, dict) and item["check"] == "installed_compatibility"
    )
    assert isinstance(outcome, dict) and outcome["native_exit"] is None
    expected = {
        "missing": "native_tool_unavailable",
        "changed": "native_source_mismatch",
        "nonexecutable": "native_not_executable",
    }
    assert outcome["finding"] == expected[state]
