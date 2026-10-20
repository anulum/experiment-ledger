# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Exercise real required-source, Git index and repository privacy boundaries."""

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import pytest

from ledger_validation.inputs import Json

from .provenance_support import SOURCE, source_files


def _invoke(
    root: Path, *arguments: str, without_git: bool = False
) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    if without_git:
        environment["PATH"] = ""
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "--parallel-mode",
            "--branch",
            "--source=" + str(SOURCE / "tools") + "," + str(SOURCE / "tests"),
            str(SOURCE / "tools/check_repository_inventory.py"),
            "--root",
            str(root),
            *arguments,
        ],
        cwd=SOURCE,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
    )


def _report(root: Path, expected: int, *, without_git: bool = False) -> dict[str, Json]:
    process = _invoke(root, "--json", without_git=without_git)
    assert process.returncode == expected, (process.stdout, process.stderr)
    assert not process.stderr
    value = cast(dict[str, Json], json.loads(process.stdout))
    assert value["check"] == "repository_inventory"
    assert value["scope"] == "local_scaffold_source_inventory"
    assert value["exit_code"] == expected
    return value


@pytest.fixture(scope="module")
def source_copy(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Copy the complete actual public cohort for owned native index fault cases.

    Parameters
    ----------
    tmp_path_factory : pytest.TempPathFactory
        Samsung scratch allocator.

    Returns
    -------
    Path
        Actual source copy with an isolated unpublished Git index.
    """
    root = tmp_path_factory.mktemp("inventory-source")
    for name, raw in source_files(SOURCE).items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    subprocess.run(["git", "init", "-q", "--initial-branch=main", str(root)], check=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "--local", "core.excludesFile", "/dev/null"], check=True
    )
    return root


@pytest.fixture
def root(source_copy: Path) -> Iterator[Path]:
    """Restore this case's isolated files and index, preserving all canonical source.

    Parameters
    ----------
    source_copy : Path
        Owned actual-source repository.

    Yields
    ------
    Path
        Original complete inventory candidate.
    """
    before = source_files(source_copy)
    yield source_copy
    subprocess.run(["git", "-C", str(source_copy), "read-tree", "--empty"], check=True)
    for name in source_files(source_copy).keys() - before.keys():
        (source_copy / name).unlink()
    for name, raw in before.items():
        path = source_copy / name
        if path.is_symlink():
            path.unlink()
        if not path.exists() or path.read_bytes() != raw:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)


def test_complete_actual_inventory_preserves_sources_and_index(root: Path) -> None:
    """All original required paths and current maintained sources qualify without mutation."""
    before = source_files(root)
    assert _report(root, 0)["findings"] == []
    assert before == source_files(root)
    assert (
        subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached"], capture_output=True, check=True
        ).stdout
        == b""
    )


@pytest.mark.parametrize(
    "name",
    [
        "README.md",
        "tools/preflight.py",
        "tests/test_preflight.py",
        "dependency-source-selections.json",
        "dependency-source-selections.json.license",
        "tools/generate_dependency_provenance.py",
    ],
)
def test_missing_required_source_cannot_pass(root: Path, name: str) -> None:
    """Required source removal cannot shrink the accepted scaffold denominator."""
    (root / name).unlink()
    assert _report(root, 3)["findings"]


def test_deleted_tracked_source_stays_enrolled(root: Path) -> None:
    """Native Git retains a deleted tracked source and the inspector reports it unavailable."""
    subprocess.run(["git", "-C", str(root), "add", "README.md"], check=True)
    (root / "README.md").unlink()
    assert _report(root, 3)["findings"] == [
        {"code": "source_input_unavailable", "location": "README.md"}
    ]


@pytest.mark.parametrize("name", ["AGENTS.md", ".env", "CREDENTIALS.md", ".coordination"])
def test_actual_forbidden_root_state_refuses_even_when_ignored(root: Path, name: str) -> None:
    """Ignore rules cannot hide actual project-local state or credential paths."""
    path = root / name
    path.write_text("Controlled invalid root input\n")
    try:
        assert _report(root, 2)["findings"]
    finally:
        path.unlink()


@pytest.mark.parametrize("name", ["dist", "build", "site", "target", "node_modules"])
def test_actual_unexpected_generated_tree_refuses(root: Path, name: str) -> None:
    """A forbidden initial package/build tree cannot hide behind the source ignore policy."""
    path = root / name
    path.mkdir()
    try:
        assert _report(root, 2)["findings"] == [
            {"code": "unexpected_generated_state", "location": name}
        ]
    finally:
        path.rmdir()


def test_private_path_enrolment_is_detected_by_actual_index(root: Path) -> None:
    """A real controlled private-path index corruption is refused after ignores are restored."""
    ignore = root / ".gitignore"
    original = ignore.read_bytes()
    ignore.write_bytes(
        original.replace(b"/docs/internal/\n", b"").replace(b"/docs/internal/**\n", b"")
    )
    private = root / "docs/internal/controlled-input.md"
    private.parent.mkdir(parents=True, exist_ok=True)
    private.write_text("Controlled invalid source enrolment\n")
    subprocess.run(["git", "-C", str(root), "add", "docs/internal/controlled-input.md"], check=True)
    ignore.write_bytes(original)
    try:
        assert _report(root, 2)["findings"] == [
            {"code": "private_source_enrolled", "location": "docs/internal/controlled-input.md"}
        ]
    finally:
        private.unlink()


def test_generated_source_in_actual_index_refuses(root: Path) -> None:
    """A tracked generated file is detected even when its normal ignore is restored."""
    ignore = root / ".gitignore"
    original = ignore.read_bytes()
    ignore.write_bytes(original.replace(b"/dist/\n", b""))
    path = root / "dist/generated.txt"
    path.parent.mkdir()
    path.write_text("Controlled generated input\n")
    try:
        subprocess.run(["git", "-C", str(root), "add", "dist/generated.txt"], check=True)
        ignore.write_bytes(original)
        assert _report(root, 2)["findings"] == [
            {"code": "generated_source_enrolled", "location": "dist/generated.txt"}
        ]
    finally:
        ignore.write_bytes(original)
        path.unlink()
        path.parent.rmdir()


def test_missing_private_ignore_cannot_qualify(root: Path) -> None:
    """The actual native ignore query must protect both direct and nested private inputs."""
    path = root / ".gitignore"
    path.write_bytes(
        path.read_bytes().replace(b"/docs/internal/\n", b"").replace(b"/docs/internal/**\n", b"")
    )
    assert _report(root, 2)["findings"] == [
        {"code": "private_ignore_incomplete", "location": ".gitignore"}
    ]


@pytest.mark.parametrize("target", ["inside", "outside"])
def test_actual_source_symlinks_refuse(root: Path, target: str) -> None:
    """Required maintained source must be a regular original even when its target is readable."""
    path = root / "README.md"
    path.unlink()
    path.symlink_to(root / "NOTICE.md" if target == "inside" else SOURCE / "README.md")
    assert _report(root, 2)["findings"] == [
        {"code": "source_path_not_regular", "location": "README.md"}
    ]


@pytest.mark.parametrize("extra", [0, 1])
def test_actual_source_byte_bound(root: Path, extra: int) -> None:
    """An actual newly enrolled source fits its bound and refuses one original byte more."""
    path = root / "docs/bounded-source.md"
    path.write_bytes(b"x" * (1048576 + extra))
    assert _report(root, 2 if extra else 0)["findings"] == (
        [{"code": "source_size_exceeded", "location": "docs/bounded-source.md"}] if extra else []
    )


def test_missing_git_tool_is_unavailable(root: Path) -> None:
    """Removing native Git from PATH cannot produce a qualified inventory."""
    assert _report(root, 3, without_git=True)["findings"]


def test_public_help_arguments_and_human_report(root: Path) -> None:
    """The public native command retains fixed argument semantics and human output."""
    assert _invoke(root, "--help").returncode == 0
    assert _invoke(root, "--unknown").returncode == 4
    result = _invoke(root)
    assert result.returncode == 0 and result.stdout == "repository_inventory: passed\n"


@pytest.mark.parametrize("state", ["missing", "file", "symlink"])
def test_required_directory_must_be_an_actual_directory(root: Path, state: str) -> None:
    """The required tests tree cannot be absent or replaced by a file or symlink."""
    path = root / "tests"
    original = root / ".tool-cache/retained-tests"
    original.parent.mkdir(parents=True, exist_ok=True)
    path.rename(original)
    try:
        if state == "file":
            path.write_text("Controlled invalid directory replacement\n")
        elif state == "symlink":
            path.symlink_to(original, target_is_directory=True)
        assert _report(root, 3)["findings"] == [
            {"code": "required_directory_unavailable", "location": "tests"}
        ]
    finally:
        if state != "missing":
            path.unlink()
        original.rename(path)


def test_unreadable_enrolled_source_reports_unavailable(root: Path) -> None:
    """An actual indexed path with an unreadable ancestor cannot qualify as inspected."""
    directory = root / "docs/controlled-permission"
    directory.mkdir()
    path = directory / "source.md"
    path.write_text("Controlled original source\n")
    subprocess.run(["git", "-C", str(root), "add", str(path.relative_to(root))], check=True)
    directory.chmod(0)
    try:
        assert _report(root, 3)["findings"] == [
            {"code": "source_input_unavailable", "location": "docs/controlled-permission/source.md"}
        ]
    finally:
        directory.chmod(0o700)
        subprocess.run(["git", "-C", str(root), "read-tree", "--empty"], check=True)
        path.unlink()
        directory.rmdir()


@pytest.mark.parametrize(
    "name", ["src/record.py", "native/src/lib.rs", "tools/record.rs", "Cargo.toml"]
)
@pytest.mark.parametrize("tracked", [False, True])
def test_new_source_scope_requires_qualified_gates(root: Path, name: str, tracked: bool) -> None:
    """Actual received source cannot enter an unchecked root or language through Git enrolment."""
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((SOURCE / "tools/check_repository_inventory.py").read_bytes())
    if tracked:
        subprocess.run(["git", "-C", str(root), "add", "--", name], check=True)
    assert _report(root, 2)["findings"] == [{"code": "source_scope_unqualified", "location": name}]


def test_new_python_module_uses_the_existing_qualified_source_scope(root: Path) -> None:
    """An additional actual Python checker stays inside the existing whole tools gate scope."""
    path = root / "tools/additional_inventory_check.py"
    path.write_bytes((SOURCE / "tools/check_repository_inventory.py").read_bytes())
    assert _report(root, 0)["findings"] == []
