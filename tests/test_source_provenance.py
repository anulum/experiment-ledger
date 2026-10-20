# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Exercise licence provenance through actual source trees and public CLI processes."""

import json
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from .provenance_support import SOURCE, invoke, report, source_files


@pytest.fixture(scope="module")
def source_copy(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create one complete source copy with a real local Git index.

    Parameters
    ----------
    tmp_path_factory : pytest.TempPathFactory
        Owned Samsung test scratch allocator.

    Returns
    -------
    Path
        Isolated actual-source repository; no source implementation is replaced.
    """
    root = tmp_path_factory.mktemp("provenance-source")
    for name, raw in source_files(SOURCE).items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    subprocess.run(["git", "init", "-q", "--initial-branch=main", str(root)], check=True)
    return root


@pytest.fixture
def repository(source_copy: Path) -> Iterator[Path]:
    """Restore only this test's source copy and index after each ordinary case.

    Parameters
    ----------
    source_copy : Path
        Complete repository source copy owned by this module.

    Yields
    ------
    Path
        Original source bytes before the case-specific input change.
    """
    original = source_files(source_copy)
    yield source_copy
    subprocess.run(["git", "-C", str(source_copy), "read-tree", "--empty"], check=True)
    for name in source_files(source_copy).keys() - original.keys():
        (source_copy / name).unlink()
    for name, raw in original.items():
        path = source_copy / name
        if not path.exists() or path.read_bytes() != raw:
            path.write_bytes(raw)


def test_current_sources_are_unchanged() -> None:
    """The complete actual source cohort passes and remains byte-for-byte intact."""
    before = source_files(SOURCE)
    assert report(invoke(SOURCE), 0)["findings"] == []
    assert source_files(SOURCE) == before


@pytest.mark.parametrize(
    "name",
    [
        ".editorconfig",
        ".gitattributes",
        ".gitignore",
        ".github/FUNDING.yml",
        ".pre-commit-config.yaml",
        "Makefile",
        "README.md",
        "pyproject.toml",
        "tools/check_repository_metadata.py",
        "requirements-dev.txt",
    ],
)
def test_missing_header_refuses(repository: Path, name: str) -> None:
    """Each maintained text format requires its project-specific full header."""
    path = repository / name
    path.write_bytes(b"\n".join(path.read_bytes().split(b"\n")[1:]))
    assert report(invoke(repository), 2)["findings"]


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("Commercial license available", "Licensing information"),
        ("EXPERIMENT-LEDGER", "OTHER-PROJECT"),
        ("ORCID: 0009-0009-3560-0851", "ORCID: missing"),
        ("© Concepts 1996–2026", "© Concepts 2026"),
        ("SPDX-" + "License-Identifier: AGPL-3.0-or-later", "SPDX-" + "License-Identifier: MIT"),
    ],
)
def test_changed_notice_refuses(repository: Path, old: str, new: str) -> None:
    """Every required identity/licence notice is checked rather than its presence."""
    path = repository / "README.md"
    path.write_text(path.read_text().replace(old, new))
    assert report(invoke(repository), 2)["findings"]


def test_conflicting_later_spdx_refuses(repository: Path) -> None:
    """A valid first header cannot hide a later conflicting licence identifier."""
    path = repository / "README.md"
    path.write_bytes(path.read_bytes() + b"\nSPDX-" + b"License-Identifier: MIT\n")
    findings = report(invoke(repository), 2)["findings"]
    assert findings == [{"code": "conflicting_spdx", "location": "README.md"}]


@pytest.mark.parametrize("raw", [b"{", b"[]", b'{"x":0,"x":1}', b'{"x":NaN}', b"\xff"])
def test_invalid_json_refuses(repository: Path, raw: bytes) -> None:
    """Source JSON is parsed strictly before its unchanged sidecar can qualify it."""
    (repository / "repository-domain.json").write_bytes(raw)
    assert report(invoke(repository), 2)["findings"]


def test_missing_sidecar_is_unavailable(repository: Path) -> None:
    """Aggregate REUSE coverage cannot replace an absent original JSON sidecar."""
    (repository / "repository-domain.json.license").unlink()
    assert report(invoke(repository), 3)["findings"]


@pytest.mark.parametrize("name", ["additional.JSON", "additional.JsOn"])
def test_json_suffix_case_keeps_exact_sidecar_contract(repository: Path, name: str) -> None:
    """Case variants remain valid JSON and require their exact adjacent ownership path."""
    (repository / name).write_bytes(b"{}\n")
    sidecar = repository / (name + ".license")
    sidecar.write_bytes((repository / "repository-domain.json.license").read_bytes())
    assert report(invoke(repository), 0)["findings"] == []
    sidecar.unlink()
    assert report(invoke(repository), 3)["findings"] == [
        {"code": "json_sidecar_unavailable", "location": name}
    ]


@pytest.mark.parametrize("member", ["SPDX-" + "License-Identifier", "spdx_license_identifier"])
@pytest.mark.parametrize("value", ["MIT", None])
def test_top_level_json_licence_cannot_conflict_with_sidecar(
    repository: Path, member: str, value: str | None
) -> None:
    """An optional received top-level ownership field must agree with its exact sidecar."""
    name = "licence-example.json"
    (repository / name).write_text(json.dumps({member: value}) + "\n")
    (repository / (name + ".license")).write_bytes(
        (repository / "repository-domain.json.license").read_bytes()
    )
    assert report(invoke(repository), 2)["findings"] == [
        {"code": "json_licence_conflict", "location": name}
    ]


@pytest.mark.parametrize("member", ["SPDX-" + "License-Identifier", "spdx_license_identifier"])
def test_matching_json_ownership_keeps_nested_component_licences(
    repository: Path, member: str
) -> None:
    """Matching optional ownership is admitted without relabelling nested third-party metadata."""
    name = "licence-example.json"
    raw = json.dumps({member: "AGPL-3.0-or-later", "components": [{member: "MIT"}]}).encode()
    (repository / name).write_bytes(raw)
    (repository / (name + ".license")).write_bytes(
        (repository / "repository-domain.json.license").read_bytes()
    )
    assert report(invoke(repository), 0)["findings"] == []
    assert (repository / name).read_bytes() == raw


def test_two_json_ownership_members_must_both_match(repository: Path) -> None:
    """One matching ownership spelling cannot hide a conflicting second declaration."""
    name = "licence-example.json"
    (repository / name).write_text(
        json.dumps(
            {"SPDX-" + "License-Identifier": "AGPL-3.0-or-later", "spdx_license_identifier": "MIT"}
        )
    )
    (repository / (name + ".license")).write_bytes(
        (repository / "repository-domain.json.license").read_bytes()
    )
    assert report(invoke(repository), 2)["findings"] == [
        {"code": "json_licence_conflict", "location": name}
    ]


@pytest.mark.parametrize("raw", [b"", b"SPDX-" + b"License-Identifier: MIT\n"])
def test_altered_sidecar_refuses(repository: Path, raw: bytes) -> None:
    """Truncated or conflicting sidecar bytes cannot qualify the original JSON."""
    (repository / "repository-domain.json.license").write_bytes(raw)
    assert report(invoke(repository), 2)["findings"]


@pytest.mark.parametrize("name", ["LICENSE", "LICENSES/AGPL-3.0-or-later.txt"])
def test_original_licence_is_not_relabelled(repository: Path, name: str) -> None:
    """An own-project notice cannot replace an original upstream licence text."""
    raw = (repository / "requirements-dev.in").read_bytes()
    (repository / name).write_bytes(raw)
    assert report(invoke(repository), 2)["findings"] == [
        {"code": "licence_original_changed", "location": name}
    ]


def test_selected_assets_are_bound(repository: Path) -> None:
    """A recognised binary path retains its selected source identity."""
    (repository / "docs/assets/anulum_logo.png").write_bytes(b"altered asset")
    assert report(invoke(repository), 2)["findings"]


def test_reuse_annotation_policy_is_bound(repository: Path) -> None:
    """A valid header cannot hide overwritten aggregate ownership annotations."""
    path = repository / "REUSE.toml"
    path.write_text(path.read_text().replace('precedence = "aggregate"', 'precedence = "override"'))
    assert report(invoke(repository), 2)["findings"]


def test_new_maintained_source_is_enrolled(repository: Path) -> None:
    """A new nonignored source is scanned without a fixed filename allowlist."""
    path = repository / "docs/provenance-example.md"
    path.write_bytes((repository / "README.md").read_bytes())
    assert report(invoke(repository), 0)["findings"] == []
    path.write_bytes(b"unlicensed new source")
    assert report(invoke(repository), 2)["findings"]


def test_invalid_source_encoding_refuses(repository: Path) -> None:
    """Undecodable maintained text is refused without exposing decoder errors."""
    (repository / "README.md").write_bytes(b"\xff")
    assert report(invoke(repository), 2)["findings"]


@pytest.mark.parametrize("name", ["orphan.json.license", "orphan.txt.license"])
def test_orphan_sidecar_refuses(repository: Path, name: str) -> None:
    """Sidecars require an enrolled JSON source, rather than arbitrary text."""
    if name.endswith(".txt.license"):
        (repository / "orphan.txt").write_bytes((repository / "requirements-dev.in").read_bytes())
    (repository / name).write_bytes((repository / "repository-domain.json.license").read_bytes())
    assert report(invoke(repository), 2)["findings"]


@pytest.mark.parametrize("name", ["REUSE.toml", "repository-domain.json"])
def test_required_source_missing(repository: Path, name: str) -> None:
    """Unavailable policy/source anchors do not qualify an incomplete cohort."""
    (repository / name).unlink()
    assert report(invoke(repository), 3)["findings"]


def test_deleted_tracked_source_is_unavailable(repository: Path) -> None:
    """A deleted tracked path remains enrolled through the actual Git index."""
    subprocess.run(["git", "-C", str(repository), "add", "README.md"], check=True)
    (repository / "README.md").unlink()
    assert report(invoke(repository), 3)["findings"]


def test_missing_git_dependency_is_unavailable(repository: Path) -> None:
    """The real command cannot pass when native Git is absent from its PATH."""
    assert report(invoke(repository, without_git=True), 3)["findings"]


def test_non_repository_is_unavailable(tmp_path: Path) -> None:
    """Native Git refusal from a non-repository directory propagates as unavailable."""
    assert report(invoke(tmp_path, isolate_discovery=True), 3)["findings"] == [
        {"code": "git_unavailable", "location": "."}
    ]


def test_default_root_and_human_output(repository: Path) -> None:
    """The actual process cwd and human report share the valid source outcome."""
    result = invoke(repository, machine=False, explicit_root=False)
    assert result.returncode == 0
    assert result.stdout == "source_provenance: passed\n"
    assert not result.stderr


def test_public_help_and_arguments(repository: Path) -> None:
    """Public help succeeds and invalid arguments use the fixed exit-four message."""
    help_result = invoke(repository, "--help", machine=False)
    assert help_result.returncode == 0 and "--root" in help_result.stdout
    bad = invoke(repository, "--unknown-secret-value", machine=False)
    assert bad.returncode == 4
    assert "unknown-secret-value" not in bad.stdout + bad.stderr


@pytest.mark.parametrize("extra", [0, 1])
def test_json_original_byte_limit(repository: Path, extra: int) -> None:
    """Accept the complete stated byte boundary and refuse one original byte more."""
    prefix, suffix = b'{"value":"', b'"}\n'
    raw = prefix + b"x" * (1048576 - len(prefix) - len(suffix) + extra) + suffix
    assert len(raw) == 1048576 + extra
    (repository / "extra.json").write_bytes(raw)
    (repository / "extra.json.license").write_bytes(
        (repository / "repository-domain.json.license").read_bytes()
    )
    assert report(invoke(repository), 2 if extra else 0)["findings"] == (
        [{"code": "input_too_large", "location": "extra.json"}] if extra else []
    )


def test_ignored_sidecar_is_unavailable(repository: Path) -> None:
    """A physical but ignored sidecar is not part of the public source cohort."""
    path = repository / ".gitignore"
    path.write_bytes(path.read_bytes() + b"\n/repository-domain.json.license\n")
    assert (repository / "repository-domain.json.license").exists()
    assert report(invoke(repository), 3)["findings"] == [
        {"code": "json_sidecar_unavailable", "location": "repository-domain.json"}
    ]
