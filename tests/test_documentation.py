# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Exercise actual Markdown inputs and strict MkDocs output through the public CLI."""

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

from .provenance_support import SOURCE, source_files


def _invoke(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "--parallel-mode",
            "--branch",
            "--source=" + str(SOURCE / "tools") + "," + str(SOURCE / "tests"),
            str(SOURCE / "tools/check_documentation.py"),
            "--root",
            str(root),
            *arguments,
        ],
        cwd=SOURCE,
        env=dict(os.environ),
        capture_output=True,
        text=True,
        timeout=75,
    )


def _report(root: Path, expected: int) -> dict[str, Json]:
    result = _invoke(root, "--json")
    assert result.returncode == expected, (result.stdout, result.stderr)
    assert not result.stderr
    value = cast(dict[str, Json], json.loads(result.stdout))
    assert value["check"] == "documentation"
    assert value["scope"] == "local_scaffold_documentation"
    assert value["exit_code"] == expected
    return value


@pytest.fixture(scope="module")
def source_copy(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create one actual-source repository for documentation boundary cases.

    Parameters
    ----------
    tmp_path_factory : pytest.TempPathFactory
        Samsung scratch allocator.

    Returns
    -------
    Path
        Single complete public source copy, without copied caches or private state.
    """
    root = tmp_path_factory.mktemp("documentation-source")
    for name, raw in source_files(SOURCE).items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    subprocess.run(["git", "init", "-q", "--initial-branch=main", str(root)], check=True)
    return root


@pytest.fixture
def root(source_copy: Path) -> Iterator[Path]:
    """Restore modified owned inputs after each case while reusing the source cohort.

    Parameters
    ----------
    source_copy : Path
        One isolated actual-source repository.

    Yields
    ------
    Path
        Original public source inputs.
    """
    before = source_files(source_copy)
    yield source_copy
    output = source_copy / ".tool-cache/documentation"
    if output.is_symlink():
        output.unlink()
    for name in source_files(source_copy).keys() - before.keys():
        (source_copy / name).unlink()
    for name, raw in before.items():
        path = source_copy / name
        if not path.exists() or path.read_bytes() != raw:
            path.write_bytes(raw)


def test_actual_public_markdown_and_native_api_render(root: Path) -> None:
    """The complete actual documentation renders without modifying maintained inputs."""
    before = source_files(root)
    assert _report(root, 0)["findings"] == []
    assert before == source_files(root)
    assert (root / ".tool-cache/documentation/index.html").is_file()


def test_additional_actual_document_is_enrolled(root: Path) -> None:
    """A newly maintained page enters the local-link and real renderer graph."""
    path = root / "docs/additional-boundary.md"
    path.write_bytes((root / "docs/ARCHITECTURE.md").read_bytes())
    config = root / "mkdocs.yml"
    config.write_text(
        config.read_text().replace(
            "nav:\n", "nav:\n  - Additional boundary: additional-boundary.md\n"
        )
    )
    assert _report(root, 0)["findings"] == []
    assert (root / ".tool-cache/documentation/additional-boundary/index.html").is_file()


@pytest.mark.parametrize(
    ("extra", "code"),
    [
        ("[missing](missing.md)", "documentation_link_missing"),
        ("[outside](../outside.md)", "documentation_link_missing"),
        ("[broken anchor](README.md#nonexistent-anchor)", "documentation_anchor_missing"),
        ("[asset anchor](docs/assets/anulum_logo.png#missing)", "documentation_anchor_missing"),
        ("[private](docs/internal/current.md)", "documentation_link_private"),
        ("[unearned DOI](https://doi.org/10.1234/unissued)", "documentation_unearned_service"),
        (
            "![unearned status](https://example.invalid/workflow/badge.svg)",
            "documentation_unearned_service",
        ),
        (
            "![unearned coverage](https://img.shields.io/badge/coverage-100-green)",
            "documentation_unearned_service",
        ),
        ("```sh\npip install experiment-ledger\n```", "documentation_unavailable_api"),
        ("```python\nfrom experiment_ledger import append\n```", "documentation_unavailable_api"),
        ("Codex session status", "documentation_private_projection"),
        ("Private details: .coordination/planning/", "documentation_private_projection"),
        ("[malformed](https://[invalid)", "documentation_link_invalid"),
    ],
)
def test_received_public_content_refuses(root: Path, extra: str, code: str) -> None:
    """Broken references, private content and unearned service/API claims cannot pass."""
    private = root / "docs/internal/current.md"
    private.parent.mkdir(parents=True, exist_ok=True)
    private.write_text("Private controlled input\n")
    path = root / "README.md"
    path.write_text(path.read_text() + "\n\n" + extra + "\n")
    try:
        assert _report(root, 2)["findings"] == [{"code": code, "location": "README.md"}]
    finally:
        private.unlink()


def test_visible_provenance_header_refuses(root: Path) -> None:
    """Removing the HTML comment boundary makes the original notice visible and refuses."""
    path = root / "README.md"
    path.write_text(path.read_text().replace("<!--\n", "", 1))
    assert _report(root, 2)["findings"]


def test_non_utf8_document_refuses(root: Path) -> None:
    """Malformed original public Markdown has a fixed content refusal."""
    (root / "README.md").write_bytes(b"\xff")
    assert _report(root, 2)["findings"] == [
        {"code": "documentation_text_invalid", "location": "README.md"}
    ]


def test_actual_local_fragments_and_external_links(root: Path) -> None:
    """Real heading fragments, local images and classified external links remain valid."""
    path = root / "README.md"
    path.write_text(
        path.read_text()
        + "\n## Checked heading\n\n[local](#checked-heading) "
        + "[cross-file](docs/ARCHITECTURE.md#input-and-ownership) "
        + "[external](https://example.invalid/) "
        + '<span hidden id="explicit-anchor"></span> [explicit](#explicit-anchor)\n'
    )
    assert _report(root, 0)["findings"] == []


def test_native_renderer_failure_is_not_passed(root: Path) -> None:
    """A real unavailable theme makes the strict native renderer fail closed."""
    path = root / "mkdocs.yml"
    path.write_text(path.read_text().replace("name: material", "name: unavailable-theme"))
    assert _report(root, 2)["findings"] == [
        {"code": "documentation_renderer_failed", "location": "mkdocs.yml"}
    ]


def test_native_rendered_private_text_refuses(root: Path) -> None:
    """Private text introduced through real renderer configuration cannot escape projection checks."""
    path = root / "mkdocs.yml"
    path.write_text(path.read_text().replace("site_name: Experiment Ledger", "site_name: Codex"))
    findings = _report(root, 2)["findings"]
    assert isinstance(findings, list) and isinstance(findings[0], dict)
    assert findings[0]["code"] == "documentation_private_projection"
    assert str(findings[0]["location"]).startswith("rendered/")


def test_actual_private_rendered_page_refuses(root: Path) -> None:
    """Removing private exclusion in the actual MkDocs configuration is refused."""
    private = root / "docs/internal/current.md"
    private.parent.mkdir(parents=True, exist_ok=True)
    private.write_text("# Private current input\n")
    config = root / "mkdocs.yml"
    text = config.read_text().replace("  /internal/\n", "  /excluded/\n")
    text = text.replace("nav:\n", "nav:\n  - Current: internal/current.md\n")
    config.write_text(text)
    try:
        assert _report(root, 2)["findings"] == [
            {"code": "documentation_render_private", "location": "mkdocs.yml"}
        ]
    finally:
        private.unlink()


def test_missing_native_overview_is_unavailable(root: Path) -> None:
    """A successful native build without the required overview does not qualify the projection."""
    config = root / "mkdocs.yml"
    text = config.read_text().replace("  /internal/\n", "  /internal/\n  /index.md\n")
    config.write_text(text.replace("  - Overview: index.md\n", ""))
    assert _report(root, 3)["findings"] == [
        {"code": "documentation_render_missing", "location": "mkdocs.yml"}
    ]


def test_render_output_cannot_escape_repository(root: Path) -> None:
    """An ordinary received output symlink cannot move generated pages outside the repository."""
    output = root / ".tool-cache/documentation"
    shutil.rmtree(output, ignore_errors=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.symlink_to(root.parent, target_is_directory=True)
    assert _report(root, 2)["findings"] == [
        {"code": "documentation_output_escape", "location": ".tool-cache/documentation"}
    ]


def test_public_help_arguments_and_human_output(root: Path) -> None:
    """Public argument and text-report routes exercise the same actual document check."""
    assert _invoke(root, "--help").returncode == 0
    assert _invoke(root, "--unknown").returncode == 4
    result = _invoke(root)
    assert result.returncode == 0 and result.stdout == "documentation: passed\n"
