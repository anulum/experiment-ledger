# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Exercise bounded native validation children through the production process API."""

import json
import os
import sys
from pathlib import Path

import pytest

from ledger_validation.inputs import CheckFailure
from ledger_validation.processes import execute

SOURCE = Path(__file__).resolve().parents[1]


def test_actual_metadata_child_exit_and_original_report(tmp_path: Path) -> None:
    """The real owned checker completes, is reaped and returns its original report."""
    result = execute(
        [
            sys.executable,
            str(SOURCE / "tools/check_repository_metadata.py"),
            "--root",
            str(SOURCE),
            "--json",
        ],
        root=tmp_path,
        location="repository-domain.json",
    )
    assert result.returncode == 0 and result.stderr == b""
    assert json.loads(result.stdout)["check"] == "repository_metadata"
    assert list((tmp_path / ".tool-cache/processes").iterdir()) == []
    with pytest.raises(ChildProcessError):
        os.waitpid(-1, os.WNOHANG)


def test_native_git_receives_original_standard_input() -> None:
    """The actual Git ignore query receives finite input without shell processing."""
    result = execute(
        ["git", "check-ignore", "--stdin", "-z"],
        root=SOURCE,
        location=".gitignore",
        input_bytes=b".venv/pyvenv.cfg\0",
    )
    assert result.returncode == 0 and result.stdout == b".venv/pyvenv.cfg\0"


@pytest.mark.parametrize("arguments", [["--version"], ["--unknown-validation-option"]])
def test_actual_native_output_cannot_exceed_returned_bound(
    tmp_path: Path, arguments: list[str]
) -> None:
    """Both genuine native stdout and stderr are rejected beyond the stated byte limit."""
    with pytest.raises(CheckFailure) as caught:
        execute(["git", *arguments], root=tmp_path, location="git", limit=2)
    assert caught.value.code == "child_output_too_large" and caught.value.exit_code == 2


def test_unavailable_executable_is_not_passed(tmp_path: Path) -> None:
    """An actual absent tool yields unavailable and leaves no temporary output."""
    with pytest.raises(CheckFailure) as caught:
        execute([str(tmp_path / "missing-tool")], root=tmp_path, location="native-tool")
    assert caught.value.code == "child_unavailable" and caught.value.exit_code == 3
    assert list((tmp_path / ".tool-cache/processes").iterdir()) == []


def test_wrong_cache_type_is_unavailable(tmp_path: Path) -> None:
    """A file blocking the owned cache directory cannot become a successful check."""
    (tmp_path / ".tool-cache").write_bytes(b"not a directory")
    with pytest.raises(CheckFailure) as caught:
        execute(["git", "--version"], root=tmp_path, location="native-tool")
    assert caught.value.code == "child_unavailable"


def test_escaped_cache_is_refused(tmp_path: Path) -> None:
    """An ordinary symlink input cannot redirect validation output outside its repository."""
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "repository"
    root.mkdir()
    (root / ".tool-cache").symlink_to(outside, target_is_directory=True)
    with pytest.raises(CheckFailure) as caught:
        execute(["git", "--version"], root=root, location="native-tool")
    assert caught.value.code == "child_cache_escape"
    assert list(outside.iterdir()) == []


def test_finite_native_help_obeys_deadline_and_reaps_child(tmp_path: Path) -> None:
    """A genuine MkDocs help invocation exceeding a tiny deadline is stopped and reaped."""
    with pytest.raises(CheckFailure) as caught:
        execute(
            [sys.executable, "-m", "mkdocs", "--help"],
            root=tmp_path,
            location="mkdocs.yml",
            timeout=0.000001,
        )
    assert caught.value.code == "child_timeout" and caught.value.exit_code == 3
    with pytest.raises(ChildProcessError):
        os.waitpid(-1, os.WNOHANG)
    assert list((tmp_path / ".tool-cache/processes").iterdir()) == []


@pytest.mark.parametrize(
    ("command", "timeout", "limit"), [([], 1, 1), (["git"], 0, 1), (["git"], 1, 0)]
)
def test_invalid_process_resource_bounds_refuse(
    tmp_path: Path, command: list[str], timeout: float, limit: int
) -> None:
    """Empty commands and nonpositive deadlines/byte limits are invalid API calls."""
    with pytest.raises(ValueError):
        execute(command, root=tmp_path, location="native-tool", timeout=timeout, limit=limit)
