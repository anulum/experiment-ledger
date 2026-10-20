# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Exercise installed development provenance and lock refusals through the real CLI."""

import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest

from ledger_validation.inputs import Json

from .metadata_support import INPUTS, SOURCE, _rewrite_metadata


def _invoke(
    root: Path, *arguments: str, metadata_path: Path | None = None
) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    if metadata_path is not None:
        environment["PYTHONPATH"] = str(metadata_path)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "--parallel-mode",
            "--branch",
            "--source=" + str(SOURCE / "tools") + "," + str(SOURCE / "tests"),
            str(SOURCE / "tools/check_dependency_alignment.py"),
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


def _report(root: Path, expected: int, *, metadata_path: Path | None = None) -> dict[str, Json]:
    result = _invoke(root, "--json", metadata_path=metadata_path)
    assert result.returncode == expected, (result.stdout, result.stderr)
    assert not result.stderr
    report = cast(dict[str, Json], json.loads(result.stdout))
    assert report["check"] == "dependency_alignment"
    assert report["scope"] == "local_scaffold_development_environment"
    assert report["exit_code"] == expected
    return report


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """Prepare complete actual dependency declarations without copying the environment.

    Parameters
    ----------
    tmp_path : Path
        Test-owned Samsung scratch directory.

    Returns
    -------
    Path
        Actual declarations consumed by the real installed interpreter.
    """
    workflow_names = tuple(
        path.relative_to(SOURCE).as_posix() for path in (SOURCE / ".github/workflows").iterdir()
    )
    for name in (
        *INPUTS,
        "requirements-dev.in",
        "dependency-provenance.json",
        "dependency-source-selections.json",
        "Makefile",
        ".pre-commit-config.yaml",
        "pyproject.toml",
        "gitleaks.toml",
        *workflow_names,
    ):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((SOURCE / name).read_bytes())
    return tmp_path


def test_actual_installed_environment_qualifies_without_installing(root: Path) -> None:
    """The actual interpreter and all selected installed metadata/licences correspond."""
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert _report(root, 0)["findings"] == []
    assert before == {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize(
    ("member", "value", "code"),
    [
        ("lock_sha256", "0" * 64, "dependency_lock_binding_mismatch"),
        ("python", "3.14.0", "dependency_interpreter_mismatch"),
        ("supported_range", ">=3", "dependency_interpreter_range_mismatch"),
        ("packages", {}, "dependency_provenance_invalid"),
        ("packages", [], "dependency_graph_mismatch"),
        ("packages", [None], "dependency_provenance_invalid"),
        ("packages", [{"name": None}], "dependency_provenance_invalid"),
        ("packages", [{"name": "arrow", "version": None}], "dependency_provenance_invalid"),
    ],
)
def test_changed_top_level_provenance_refuses(
    root: Path, member: str, value: Json, code: str
) -> None:
    """Unbound source, interpreter drift and malformed package declarations refuse."""
    path = root / "dependency-provenance.json"
    data = cast(dict[str, Json], json.loads(path.read_text()))
    data[member] = value
    path.write_text(json.dumps(data))
    assert _report(root, 2)["findings"] == [{"code": code, "location": path.name}]


@pytest.mark.parametrize(
    ("member", "value", "code"),
    [
        ("name", "not-an-installed-selected-package", "dependency_source_mismatch"),
        ("version", "0", "dependency_source_mismatch"),
        ("source_artifact", None, "dependency_provenance_invalid"),
        ("role", "runtime", "dependency_role_mismatch"),
        ("metadata_sha256", "0" * 64, "dependency_installed_source_mismatch"),
        ("license_files", None, "dependency_provenance_invalid"),
        ("license_files", [None], "dependency_provenance_invalid"),
    ],
)
def test_changed_package_sources_refuse(root: Path, member: str, value: Json, code: str) -> None:
    """The actual installed graph cannot be qualified with changed source records."""
    path = root / "dependency-provenance.json"
    data = cast(dict[str, Json], json.loads(path.read_text()))
    packages = data["packages"]
    assert isinstance(packages, list) and isinstance(packages[0], dict)
    packages[0][member] = value
    path.write_text(json.dumps(data))
    assert _report(root, 2)["findings"] == [{"code": code, "location": path.name}]


@pytest.mark.parametrize(
    ("member", "value"),
    [
        ("license_classifiers", []),
        ("license_expression", "UNRELATED-FORGED-LICENCE"),
        ("license_label", "unrelated received label"),
        ("requires_dist", []),
    ],
)
def test_descriptive_metadata_cannot_drift_from_its_installed_source(
    root: Path, member: str, value: Json
) -> None:
    """A correct installed METADATA hash cannot qualify changed descriptive fields."""
    path = root / "dependency-provenance.json"
    data = cast(dict[str, Json], json.loads(path.read_text()))
    packages = data["packages"]
    assert isinstance(packages, list) and isinstance(packages[0], dict)
    assert packages[0][member] != value
    packages[0][member] = value
    path.write_text(json.dumps(data))
    before = path.read_bytes()
    assert _report(root, 2)["findings"] == [
        {"code": "dependency_metadata_projection_mismatch", "location": path.name}
    ]
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "member", ["license_classifiers", "license_expression", "license_label", "requires_dist"]
)
def test_missing_descriptive_metadata_cannot_match_an_absent_installed_label(
    root: Path, member: str
) -> None:
    """Every descriptive field is required even when the original value is null."""
    path = root / "dependency-provenance.json"
    data = cast(dict[str, Json], json.loads(path.read_text()))
    packages = data["packages"]
    assert isinstance(packages, list) and isinstance(packages[0], dict)
    del packages[0][member]
    path.write_text(json.dumps(data))
    assert _report(root, 2)["findings"] == [
        {"code": "dependency_metadata_projection_mismatch", "location": path.name}
    ]


@pytest.mark.parametrize(
    ("member", "value", "expected", "code"),
    [
        ("path", "../outside", 2, "dependency_licence_path_invalid"),
        ("path", "/outside", 2, "dependency_licence_path_invalid"),
        ("path", "missing-original-licence", 3, "dependency_licence_unavailable"),
        ("sha256", "0" * 64, 2, "dependency_licence_mismatch"),
        ("bytes", 0, 2, "dependency_licence_mismatch"),
    ],
)
def test_original_installed_licence_contracts(
    root: Path, member: str, value: Json, expected: int, code: str
) -> None:
    """Licence paths remain contained, available and bound to their original bytes."""
    path = root / "dependency-provenance.json"
    data = cast(dict[str, Json], json.loads(path.read_text()))
    packages = data["packages"]
    assert isinstance(packages, list) and isinstance(packages[0], dict)
    licences = packages[0]["license_files"]
    assert isinstance(licences, list) and isinstance(licences[0], dict)
    licences[0][member] = value
    path.write_text(json.dumps(data))
    assert _report(root, expected)["findings"] == [{"code": code, "location": path.name}]


@pytest.mark.parametrize(
    "raw",
    [b"", b"arrow>=1.4\n", b"arrow==1.4.0\narrow==1.4.0\n", b"arrow==1.4.0 --hash=bad\n"],
)
def test_invalid_direct_pins_refuse(root: Path, raw: bytes) -> None:
    """Empty graphs, ranges, duplicate pins and lock-only options cannot enter inputs."""
    (root / "requirements-dev.in").write_bytes(raw)
    assert _report(root, 2)["findings"]


@pytest.mark.parametrize("tail", ["", " --hash=sha256:bad", " --trusted-host example.invalid"])
def test_missing_or_invalid_hashes_refuse(root: Path, tail: str) -> None:
    """Even independently rebound metadata cannot qualify a hashless changed lock."""
    lock = root / "requirements-dev.txt"
    lock.write_text("arrow==1.4.0" + tail + "\n")
    metadata = cast(dict[str, Json], json.loads((root / "repository-domain.json").read_text()))
    tooling = metadata["tooling_python"]
    assert isinstance(tooling, dict)
    tooling["development_lock_sha256"] = hashlib.sha256(lock.read_bytes()).hexdigest()
    _rewrite_metadata(root, metadata)
    assert _report(root, 2)["findings"] == [
        {"code": "dependency_pin_invalid", "location": "requirements-dev.txt"}
    ]


def test_dependency_text_requires_utf8(root: Path) -> None:
    """Invalid original dependency text is refused with a fixed finding."""
    (root / "requirements-dev.in").write_bytes(b"\xff")
    assert _report(root, 2)["findings"]


def test_missing_source_is_unavailable(root: Path) -> None:
    """A missing provenance source never qualifies an installed environment."""
    (root / "dependency-provenance.json").unlink()
    assert _report(root, 3)["findings"]


def test_public_help_and_human_output(root: Path) -> None:
    """Actual help, invalid arguments and human reports retain their native exits."""
    result = _invoke(root, "--help")
    assert result.returncode == 0 and "--root" in result.stdout
    result = _invoke(root, "--unknown")
    assert result.returncode == 4
    result = _invoke(root)
    assert result.returncode == 0 and result.stdout == "dependency_alignment: passed\n"


@pytest.mark.parametrize(
    "replacement", ["absent-selected-package", "incompatible-active-dependency"]
)
def test_rebound_lock_still_requires_available_compatible_packages(
    root: Path, replacement: str
) -> None:
    """Rebinding declarations cannot install a missing package or satisfy an invalid edge."""
    path = root / "dependency-provenance.json"
    data = cast(dict[str, Json], json.loads(path.read_text()))
    packages = data["packages"]
    assert isinstance(packages, list)
    lock = root / "requirements-dev.txt"
    text = lock.read_text()
    if replacement == "absent-selected-package":
        assert isinstance(packages[0], dict) and packages[0]["name"] == "arrow"
        packages[0]["name"] = replacement
        text = text.replace("arrow==1.4.0", replacement + "==1.4.0")
        expected, code = 3, "dependency_package_unavailable"
    else:
        for record in packages:
            assert isinstance(record, dict)
            if record["name"] == "python-dateutil":
                text = text.replace(
                    "python-dateutil==" + str(record["version"]), "python-dateutil==0"
                )
                record["version"] = "0"
        expected, code = 2, "dependency_graph_incompatible"
    lock.write_text(text)
    data["lock_sha256"] = hashlib.sha256(lock.read_bytes()).hexdigest()
    path.write_text(json.dumps(data))
    metadata = cast(dict[str, Json], json.loads((root / "repository-domain.json").read_text()))
    tooling = metadata["tooling_python"]
    assert isinstance(tooling, dict)
    tooling["development_lock_sha256"] = data["lock_sha256"]
    _rewrite_metadata(root, metadata)
    assert _report(root, expected)["findings"] == [{"code": code, "location": path.name}]


@pytest.mark.parametrize("line", ["uv==0", "missing-direct-development-tool==1"])
def test_direct_declarations_must_match_the_complete_lock(root: Path, line: str) -> None:
    """Direct inputs cannot name an unlocked tool or drift from its installed lock version."""
    path = root / "requirements-dev.in"
    original = path.read_text()
    path.write_text(original.replace("uv==0.12.22", line))
    expected = (
        "dependency_role_mismatch"
        if line.startswith("missing-")
        else "dependency_direct_lock_mismatch"
    )
    assert _report(root, 2)["findings"] == [
        {
            "code": expected,
            "location": "dependency-provenance.json" if line.startswith("missing-") else path.name,
        }
    ]


def test_incompatible_original_package_python_requirement_refuses(root: Path) -> None:
    """A corrupted copy of actual distribution metadata cannot bypass Requires-Python."""
    path = root / "dependency-provenance.json"
    data = cast(dict[str, Json], json.loads(path.read_text()))
    packages = data["packages"]
    assert isinstance(packages, list) and isinstance(packages[0], dict)
    original = importlib.metadata.distribution("arrow").read_text("METADATA")
    assert original is not None
    changed = "\n".join(
        "Requires-Python: >=99" if line.startswith("Requires-Python:") else line
        for line in original.split("\n")
    )
    assert changed != original
    metadata_path = root / "received-distribution"
    target = metadata_path / "arrow-1.4.0.dist-info/METADATA"
    target.parent.mkdir(parents=True)
    target.write_text(changed)
    packages[0]["metadata_sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
    path.write_text(json.dumps(data))
    assert _report(root, 2, metadata_path=metadata_path)["findings"] == [
        {"code": "dependency_python_incompatible", "location": path.name}
    ]


@pytest.mark.parametrize(
    "name", ["Makefile", ".pre-commit-config.yaml", "pyproject.toml", "gitleaks.toml"]
)
def test_changed_real_execution_configuration_requires_review(root: Path, name: str) -> None:
    """A changed actual execution configuration cannot retain installed-graph acceptance."""
    path = root / name
    path.write_bytes(path.read_bytes() + b"\n")
    assert _report(root, 2)["findings"] == [
        {"code": "dependency_execution_mismatch", "location": name}
    ]


def test_ci_install_recipe_is_part_of_actual_dependency_alignment(root: Path) -> None:
    """A real CI hash-install bypass fails the same package/execution qualification entry point."""
    path = root / ".github/workflows/ci.yml"
    original = path.read_text()
    assert "--require-hashes" in original
    path.write_text(original.replace("--require-hashes", ""))
    assert _report(root, 2)["findings"] == [
        {"code": "workflow_policy_mismatch", "location": ".github/workflows/ci.yml"}
    ]


def test_missing_actual_hook_configuration_is_unavailable(root: Path) -> None:
    """An absent hook source cannot inherit an otherwise matching installed environment."""
    (root / ".pre-commit-config.yaml").unlink()
    assert _report(root, 3)["findings"] == [
        {"code": "input_unavailable", "location": ".pre-commit-config.yaml"}
    ]


@pytest.mark.parametrize("change", ["omitted", "duplicate"])
def test_original_licence_inventory_cannot_be_omitted_or_padded(root: Path, change: str) -> None:
    """Declared evidence must preserve every actual original licence exactly once."""
    path = root / "dependency-provenance.json"
    provenance = cast(dict[str, Json], json.loads(path.read_text()))
    packages = cast(list[Json], provenance["packages"])
    record = cast(dict[str, Json], packages[0])
    licences = cast(list[Json], record["license_files"])
    assert len(licences) == 1
    record["license_files"] = [] if change == "omitted" else licences * 2
    path.write_text(json.dumps(provenance))
    assert _report(root, 2)["findings"] == [
        {"code": "dependency_licence_inventory_mismatch", "location": path.name}
    ]


def test_missing_actual_installed_file_catalog_is_unavailable(root: Path) -> None:
    """Original metadata and licence bytes cannot qualify an absent installed file catalogue."""
    distribution = importlib.metadata.distribution("arrow")
    metadata = distribution.read_text("METADATA")
    assert metadata is not None
    parent = root / ".tool-cache/metadata-only"
    directory = parent / "arrow-1.4.0.dist-info"
    directory.mkdir(parents=True)
    (directory / "METADATA").write_text(metadata)
    record = json.loads((root / "dependency-provenance.json").read_text())["packages"][0]
    for licence in record["license_files"]:
        path = parent / licence["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(distribution.locate_file(licence["path"]).read_bytes())
    assert _report(root, 3, metadata_path=parent)["findings"] == [
        {"code": "dependency_licence_catalog_unavailable", "location": "dependency-provenance.json"}
    ]
