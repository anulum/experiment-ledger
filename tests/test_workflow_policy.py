# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Exercise real workflow inputs and refusal reports through the public CLI."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest

from ledger_validation.inputs import Json

SOURCE = Path(__file__).resolve().parents[1]
WORKFLOWS = SOURCE / ".github/workflows"


def _invoke(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment.setdefault("COVERAGE_FILE", str(SOURCE / ".tool-cache/coverage/data"))
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "--parallel-mode",
            "--branch",
            "--source=" + str(SOURCE / "tools") + "," + str(SOURCE / "tests"),
            str(SOURCE / "tools/check_workflow_policy.py"),
            "--root",
            str(root),
            *arguments,
        ],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )


def _report(root: Path, expected: int) -> dict[str, Json]:
    process = _invoke(root, "--json")
    assert process.returncode == expected, (process.stdout, process.stderr)
    assert not process.stderr
    result = cast(dict[str, Json], json.loads(process.stdout))
    assert result["check"] == "workflow_policy"
    assert result["scope"] == "local_scaffold_workflows"
    assert result["exit_code"] == expected
    assert result["status"] == {0: "passed", 2: "refused", 3: "unavailable"}[expected]
    return result


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """Copy the complete actual workflow cohort into owned Samsung scratch.

    Parameters
    ----------
    tmp_path : Path
        Test-owned directory supplied by pytest.

    Returns
    -------
    Path
        Isolated repository inputs with all original workflow bytes.
    """
    directory = tmp_path / ".github/workflows"
    directory.mkdir(parents=True)
    for path in WORKFLOWS.iterdir():
        (directory / path.name).write_bytes(path.read_bytes())
    return tmp_path


def test_complete_actual_graph_is_read_only(root: Path) -> None:
    """All seven authored workflow graphs qualify without rewriting their inputs."""
    before = {path.name: path.read_bytes() for path in (root / ".github/workflows").iterdir()}
    assert _report(root, 0)["findings"] == []
    assert before == {
        path.name: path.read_bytes() for path in (root / ".github/workflows").iterdir()
    }


@pytest.mark.parametrize(
    ("file", "old", "new"),
    [
        ("ci", "  push:\n", "  push:\n    paths: ['tools/**']\n"),
        ("ci", "  pull_request:\n", "  pull_request_target:\n"),
        ("ci", "  workflow_dispatch:\n", ""),
        ("ci", "contents: read", "contents: write"),
        ("ci", "permissions:\n", "permissions:\n  id-token: write\n"),
        ("ci", "    timeout-minutes: 20\n", ""),
        ("ci", "timeout-minutes: 20", "timeout-minutes: 0"),
        ("ci", "timeout-minutes: 20", "timeout-minutes: 1440"),
        ("ci", "ubuntu-24.04", "self-hosted"),
        ("ci", "jobs:\n", "jobs:\n  unknown-job: {}\n"),
        ("ci", "jobs:\n", "jobs:\n  name: {}\n"),
        ("ci", "contents: read", "contents: read\n  name: write"),
        ("ci", "    steps:\n", "    continue-on-error: true\n    steps:\n"),
        ("ci", "make ci", "make docs"),
        ("ci", 'test "$VALIDATION_RESULT" = success', 'echo "$VALIDATION_RESULT"'),
        ("ci", "${{ always() }}", "${{ success() }}"),
        ("ci", "needs: [validation]", "needs: []"),
        ("ci", "persist-credentials: false", "persist-credentials: true"),
        ("ci", "de0fac2e4500dabe0009e67214ff5f5447ce83dd", "v6"),
        ("ci", "python-version: '3.13.16'", "python-version: '3.13'"),
        ("ci", "--only uv --download", "--only actionlint --download"),
        ("ci", "--require-hashes ", ""),
        ("ci", "--build-constraints requirements-dev.txt ", ""),
        ("ci", "make ci", "curl https://example.invalid/install | sh"),
        ("codeql", "languages: python", "languages: rust"),
        ("codeql", "upload: never", "upload: always"),
        ("codeql", "upload-database: false", "upload-database: true"),
        (
            "codeql",
            "tools: .tool-cache/codeql/codeql-bundle-python-linux64.tar.zst",
            "tools: nightly",
        ),
        ("scorecard", "INPUT_PUBLISH_RESULTS: 'false'", "INPUT_PUBLISH_RESULTS: 'true'"),
        (
            "scorecard",
            "@sha256:2dd6a6d60100f78ef24e14a47941d0087a524b4d3642041558239b1c6097c941",
            ":v2.4.3",
        ),
        ("scorecard", "INPUT_RESULTS_FORMAT: json", "INPUT_RESULTS_FORMAT: sarif"),
        ("scorecard", "INPUT_FILE_MODE: archive", "INPUT_FILE_MODE: git"),
        ("scorecard", "${{ github.event_name == 'pull_request' ||", "${{ false ||"),
        ("ci", "UV_LINK_MODE: hardlink", "UV_LINK_MODE: copy"),
        ("ci", "--link-mode hardlink", "--link-mode copy"),
        (
            "ci",
            "UV_CACHE_DIR: ${{ github.workspace }}/.tool-cache/uv",
            "UV_CACHE_DIR: /tmp/uv",
        ),
        ("ci", "tools/bootstrap_native_tools.py", "tools/unverified_installer.py"),
        ("ci", "--only uv --download", "--only uv"),
        ("ci", ".tool-cache/native/uv/uv venv", "uv venv"),
        ("ci", ".tool-cache/native/uv/uv pip sync", "uv pip sync"),
        ("ci", "--no-python-downloads ", ""),
        (
            "codeql",
            "tools: .tool-cache/codeql/codeql-bundle-python-linux64.tar.zst",
            "tools: linked",
        ),
        (
            "codeql",
            "ea86393c6c812542ae5a3a7122bcc760873707a50b25cc47d2fd7cfd514b0cb0",
            "0000000000000000000000000000000000000000000000000000000000000000",
        ),
        ("codeql", "--proto-redir '=https'", "--proto-redir '=all'"),
        ("codeql", "--retry-max-time 180", "--retry-max-time 1800"),
        (
            "codeql",
            "test ! -L .tool-cache/codeql/codeql-bundle-python-linux64.tar.zst",
            "test -e .tool-cache/codeql/codeql-bundle-python-linux64.tar.zst",
        ),
        ("sbom", "requirements requirements-dev.txt", "requirements requirements.txt"),
        ("sbom", "--output-reproducible ", ""),
        ("sbom", "--validate ", "--no-validate "),
        ("sbom", "env -u SOURCE_DATE_EPOCH ", ""),
        ("docs", "make docs", "mkdocs gh-deploy"),
        ("pre-commit", "--all-files", "--files README.md"),
        ("security-audit", "make source-audit", "echo skipped"),
    ],
)
def test_changed_execution_contracts_refuse(root: Path, file: str, old: str, new: str) -> None:
    """Policy drift cannot omit coverage, activate writes or change trusted executables."""
    path = root / (".github/workflows/" + file + ".yml")
    original = path.read_text()
    assert old in original
    path.write_text(original.replace(old, new))
    assert _report(root, 2)["findings"] == [
        {"code": "workflow_policy_mismatch", "location": ".github/workflows/" + file + ".yml"}
    ]


@pytest.mark.parametrize(
    "raw",
    [
        b"[",
        b"\xff",
        b"",
        b"jobs: {}\njobs: {}\n",
        b"? [complex, key]\n: value\n",
        b"jobs: &jobs\n  cyclic: *jobs\n",
    ],
)
def test_malformed_and_ambiguous_yaml_refuses(root: Path, raw: bytes) -> None:
    """Actual parser failures and ambiguous graphs cannot qualify as workflows."""
    (root / ".github/workflows/ci.yml").write_bytes(raw)
    assert _report(root, 2)["findings"] == [
        {"code": "workflow_yaml_invalid", "location": ".github/workflows/ci.yml"}
    ]


def test_non_mapping_workflow_refuses(root: Path) -> None:
    """A valid YAML scalar still fails the required workflow object contract."""
    (root / ".github/workflows/ci.yml").write_text("not-a-workflow\n")
    assert _report(root, 2)["findings"]


def test_missing_workflow_is_unavailable(root: Path) -> None:
    """Removing an owning workflow cannot result in a smaller passing denominator."""
    (root / ".github/workflows/docs.yml").unlink()
    assert _report(root, 3)["findings"]


def test_absent_workflow_directory_is_unavailable(tmp_path: Path) -> None:
    """An empty scaffold cannot pass the complete required workflow inventory."""
    assert _report(tmp_path, 3)["findings"]


def test_unknown_workflow_refuses(root: Path) -> None:
    """Additional unclassified execution surfaces are refused before qualification."""
    (root / ".github/workflows/publish.yml").write_text("jobs: {}\n")
    assert _report(root, 2)["findings"]


def test_unreadable_workflow_is_unavailable(root: Path) -> None:
    """A directory in place of a workflow is an unavailable required file."""
    path = root / ".github/workflows/ci.yml"
    path.unlink()
    path.mkdir()
    assert _report(root, 3)["findings"]


@pytest.mark.parametrize("extra", [0, 1])
def test_original_workflow_byte_limit(root: Path, extra: int) -> None:
    """A complete workflow fits at its byte limit and refuses one original byte more."""
    path = root / ".github/workflows/ci.yml"
    original = path.read_bytes()
    path.write_bytes(original + b"#" + b" " * (65535 + extra - len(original)))
    assert _report(root, 2 if extra else 0)["findings"] == (
        [{"code": "input_too_large", "location": ".github/workflows/ci.yml"}] if extra else []
    )


def test_help_arguments_and_human_reports(root: Path) -> None:
    """The public command retains fixed argument errors, help and text reporting."""
    help_result = _invoke(root, "--help")
    assert help_result.returncode == 0 and "--root" in help_result.stdout
    invalid = _invoke(root, "--unexpected-value")
    assert invalid.returncode == 4 and "unexpected-value" not in invalid.stderr
    human = _invoke(root)
    assert human.returncode == 0 and human.stdout == "workflow_policy: passed\n"
