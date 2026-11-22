# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Exercise real provenance generation, independently selected sources and installed faults."""

import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import sysconfig
from pathlib import Path
from typing import cast

import pytest

from ledger_validation.inputs import Json

from .metadata_support import SOURCE, _rewrite_metadata, _snapshot
from .test_dependency_alignment import root as root


def _invoke(
    root: Path,
    *arguments: str,
    metadata_path: Path | None = None,
    alternate_python: bool = False,
    explicit_root: bool = True,
    entrypoint: str = "tools/generate_dependency_provenance.py",
) -> subprocess.CompletedProcess[bytes]:
    environment = dict(os.environ)
    environment.setdefault("COVERAGE_FILE", str(SOURCE / ".tool-cache/coverage/data"))
    if metadata_path is not None:
        environment["PYTHONPATH"] = str(metadata_path)
    executable = sys.executable
    if alternate_python:
        executable = "/usr/bin/python3.12"
        environment["PYTHONPATH"] = sysconfig.get_paths()["purelib"]
        environment["COVERAGE_CORE"] = "pytrace"
    command = [
        executable,
        "-m",
        "coverage",
        "run",
        "--parallel-mode",
        "--branch",
        "--source=" + str(SOURCE / "tools") + "," + str(SOURCE / "tests"),
        str(SOURCE / entrypoint),
    ]
    if explicit_root:
        command.extend(("--root", str(root)))
    command.extend(arguments)
    return subprocess.run(command, cwd=root, env=environment, capture_output=True, timeout=30)


def _failure(
    process: subprocess.CompletedProcess[bytes],
    code: str,
    location: str = "dependency-provenance.json",
    expected: int = 2,
) -> None:
    assert process.returncode == expected, (process.stdout, process.stderr)
    assert process.stdout == b""
    assert json.loads(process.stderr) == {"code": code, "location": location}


def _received_distribution(root: Path, *, metadata: bytes | None = None) -> Path:
    directory = root / "received-metadata/arrow-1.4.0.dist-info"
    directory.mkdir(parents=True)
    original = importlib.metadata.distribution("arrow").read_text("METADATA")
    assert original is not None
    (directory / "METADATA").write_bytes(original.encode() if metadata is None else metadata)
    return directory


def test_regeneration_without_existing_outputs_preserves_all_original_identities(
    root: Path,
) -> None:
    """Two native runs reproduce all103packages/189licences without reading either output."""
    expected = (root / "dependency-provenance.json").read_bytes()
    (root / "dependency-provenance.json").unlink()
    (root / "capability-inventory.json").unlink()
    before = _snapshot(root)
    first, second = _invoke(root), _invoke(root, explicit_root=False)
    assert first.returncode == second.returncode == 0, (first.stderr, second.stderr)
    assert first.stdout == second.stdout == expected
    assert first.stderr == second.stderr == b""
    assert _snapshot(root) == before
    value = json.loads(first.stdout)
    assert len(value["packages"]) == 103
    assert sum(len(item["license_files"]) for item in value["packages"]) == 189
    sources = json.loads((root / "dependency-source-selections.json").read_text())
    assert value["security_audit"] == sources["security_audit"]
    for original in sources["native_tools"]:
        assert original in value["native_tools"]
    for role in ("shellcheck", "uv"):
        native = next(x for x in value["native_tools"] if x["role"] == role)
        assert (
            native["binary_sha256"]
            == hashlib.sha256((SOURCE / native["binary_relative_path"]).read_bytes()).hexdigest()
        )
    assert (
        value["source_selection"]["sha256"]
        == hashlib.sha256((root / "dependency-source-selections.json").read_bytes()).hexdigest()
    )


@pytest.mark.parametrize(
    "name",
    [
        "repository-domain.json",
        "schemas/repository-domain.schema.json",
        "requirements-dev.txt",
        "requirements-dev.in",
        "dependency-source-selections.json",
    ],
)
def test_generator_missing_sources_leave_stdout_empty(root: Path, name: str) -> None:
    """Every required independent source retains an unavailable native outcome."""
    (root / name).unlink()
    _failure(_invoke(root), "input_unavailable", name, 3)


@pytest.mark.parametrize("raw", [b"{", b"\xff", b'{"a":1,"a":2}', b"{}"])
def test_source_selection_requires_its_complete_reviewed_original_bytes(
    root: Path, raw: bytes
) -> None:
    """Malformed selections refuse and any valid changed source needs an owned review."""
    (root / "dependency-source-selections.json").write_bytes(raw)
    code = "dependency_selection_source_changed" if raw == b"{}" else "input_invalid"
    _failure(_invoke(root), code, "dependency-source-selections.json")


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        (b"not-a-pin", "dependency_pin_invalid"),
        (b"uv==0", "dependency_direct_lock_mismatch"),
        (b"unselected==1", "dependency_direct_lock_mismatch"),
        (b"\xff", "dependency_text_invalid"),
    ],
)
def test_direct_inputs_cannot_bypass_the_selected_lock(root: Path, raw: bytes, code: str) -> None:
    """Invalid text, unpinned declarations and missing/wrong direct versions refuse."""
    (root / "requirements-dev.in").write_bytes(raw)
    _failure(_invoke(root), code, "requirements-dev.in")


def test_rebound_metadata_does_not_reauthor_the_reviewed_source_lock(root: Path) -> None:
    """Even correct source metadata cannot silently change the selected original lock."""
    path = root / "requirements-dev.txt"
    path.write_bytes(path.read_bytes() + b"\n")
    metadata = cast(dict[str, Json], json.loads((root / "repository-domain.json").read_text()))
    tooling = metadata["tooling_python"]
    assert isinstance(tooling, dict)
    tooling["development_lock_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    _rewrite_metadata(root, metadata)
    _failure(_invoke(root), "dependency_lock_binding_mismatch", "dependency-source-selections.json")


def test_actual_other_interpreter_is_refused(root: Path) -> None:
    """The real Ubuntu system Python cannot masquerade as the selected3.13.16 runtime."""
    assert Path("/usr/bin/python3.12").is_file()
    _failure(_invoke(root, alternate_python=True), "dependency_interpreter_mismatch")


@pytest.mark.parametrize("metadata", [b"Version: 1\n", b"Name: \nVersion: 1\n", b"\xff"])
def test_corrupt_actual_distribution_metadata_cannot_crash_generation(
    root: Path, metadata: bytes
) -> None:
    """Missing/empty names and invalid original UTF8 produce structured refusal."""
    directory = _received_distribution(root, metadata=metadata)
    _failure(_invoke(root, metadata_path=directory.parent), "dependency_installed_source_mismatch")


def test_unexpected_actual_distribution_cannot_shrink_the_inventory(root: Path) -> None:
    """A real additional distribution metadata directory invalidates the complete graph."""
    directory = _received_distribution(root, metadata=b"Name: unselected\nVersion: 1\n")
    _failure(_invoke(root, metadata_path=directory.parent), "dependency_graph_mismatch")


@pytest.mark.parametrize("version_change", [False, True])
def test_installed_source_identity_is_checked_before_generation(
    root: Path, version_change: bool
) -> None:
    """Actual changed METADATA/version cannot inherit the selected original artifact identity."""
    original = importlib.metadata.distribution("arrow").read_text("METADATA")
    assert original is not None
    changed = (
        original.replace("Version: 1.4.0", "Version: 0") if version_change else original + "\n"
    )
    directory = _received_distribution(root, metadata=changed.encode())
    _failure(_invoke(root, metadata_path=directory.parent), "dependency_installed_source_mismatch")


def test_original_metadata_file_is_required_even_with_a_fallback_header(root: Path) -> None:
    """A real PKG-INFO fallback cannot replace selected original METADATA bytes."""
    directory = _received_distribution(root)
    (directory / "METADATA").rename(directory / "PKG-INFO")
    _failure(
        _invoke(root, metadata_path=directory.parent), "dependency_metadata_unavailable", expected=3
    )


@pytest.mark.parametrize(
    "mode",
    [
        "absent",
        "invalid",
        "invalid-size",
        "invalid-fields",
        "omitted",
        "missing-file",
        "unreadable-file",
        "corrupt-file",
        "oversized-file",
    ],
)
def test_complete_original_licence_sources_are_required(root: Path, mode: str) -> None:
    """Actual absent/corrupt catalogue or original licence bytes never produce partial output."""
    directory = _received_distribution(root)
    distribution = importlib.metadata.distribution("arrow")
    catalogue = distribution.read_text("RECORD")
    assert catalogue is not None
    record = directory / "RECORD"
    if mode == "invalid":
        record.write_bytes(b"\xff")
    elif mode == "invalid-size":
        record.write_text("original-path,,invalid-size\n")
    elif mode == "invalid-fields":
        record.write_text("original-path,,,extra-field\n")
    elif mode != "absent":
        record.write_text(catalogue)
        if mode == "omitted":
            record.write_text(
                "\n".join(line for line in catalogue.splitlines() if "/licenses/" not in line)
            )
        elif mode in {"unreadable-file", "corrupt-file", "oversized-file"}:
            target = directory / "licenses/LICENSE"
            target.parent.mkdir()
            if mode == "unreadable-file":
                target.mkdir()
            elif mode == "oversized-file":
                original = (
                    SOURCE
                    / ".venv/lib/python3.13/site-packages/arrow-1.4.0.dist-info/licenses/LICENSE"
                )
                target.write_bytes(original.read_bytes() + b"\n")
            else:
                target.write_bytes(b"received corrupt original licence")
    outcomes = {
        "absent": ("dependency_licence_catalog_unavailable", 3),
        "invalid": ("dependency_licence_catalog_invalid", 2),
        "invalid-size": ("dependency_licence_catalog_invalid", 2),
        "invalid-fields": ("dependency_licence_catalog_invalid", 2),
        "omitted": ("dependency_licence_inventory_mismatch", 2),
        "missing-file": ("dependency_licence_inventory_mismatch", 2),
        "unreadable-file": ("dependency_licence_unavailable", 3),
        "corrupt-file": ("dependency_licence_mismatch", 2),
        "oversized-file": ("dependency_licence_mismatch", 2),
    }
    code, exit_code = outcomes[mode]
    _failure(_invoke(root, metadata_path=directory.parent), code, expected=exit_code)


def test_existing_dependency_gate_enforces_generated_byte_drift(root: Path) -> None:
    """Semantically identical but noncanonical output is refused through the ordinary check."""
    path = root / "dependency-provenance.json"
    path.write_bytes(path.read_bytes() + b"\n")
    result = _invoke(root, "--json", entrypoint="tools/check_dependency_alignment.py")
    assert result.returncode == 2 and result.stderr == b""
    assert json.loads(result.stdout)["findings"] == [
        {"code": "dependency_generated_bytes_mismatch", "location": path.name}
    ]


@pytest.mark.parametrize(("argument", "exit_code"), [("--help", 0), ("--unknown", 4)])
def test_public_generator_help_and_invalid_arguments(
    root: Path, argument: str, exit_code: int
) -> None:
    """Actual help and invalid arguments retain their documented native outcome."""
    result = _invoke(root, argument)
    assert result.returncode == exit_code
    if exit_code == 4:
        assert result.stdout == b""
        assert result.stderr == b"generate_dependency_provenance: invalid command arguments\n"
    else:
        assert b"Generate Experiment Ledger development provenance" in result.stdout
        assert result.stderr == b""
