# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Qualify real selected native originals, cache refusals and explicit HTTPS bootstrap."""

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import cast

import pytest

from ledger_validation.inputs import CheckFailure, Json
from ledger_validation.native_tools import (
    NATIVE_SOURCES,
    ensure_tool,
    unpack_archive,
    verify_binary,
)

from .provenance_support import SOURCE


def _invoke(root: Path, *arguments: str, unavailable_proxy: bool = False) -> dict[str, Json]:
    environment = dict(os.environ)
    if unavailable_proxy:
        environment.update(
            HTTPS_PROXY="http://127.0.0.1:1",
            NO_PROXY="",
            https_proxy="http://127.0.0.1:1",
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
            "--source=" + str(SOURCE / "tools") + "," + str(SOURCE / "tests"),
            str(SOURCE / "tools/bootstrap_native_tools.py"),
            "--root",
            str(root),
            "--json",
            *arguments,
        ],
        cwd=SOURCE,
        env=environment,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert not result.stderr, result.stderr
    report = cast(dict[str, Json], json.loads(result.stdout))
    assert report["exit_code"] == result.returncode
    assert report["status"] == {0: "passed", 2: "refused", 3: "unavailable"}[result.returncode]
    assert report["scope"] == "local_scaffold_native_tools"
    return report


@pytest.fixture(scope="module")
def archives() -> dict[str, bytes]:
    """Retrieve and verify each exact official original once for public archive API cases.

    Returns
    -------
    dict[str, bytes]
        Complete original release archives, independently verified before use.
    """
    originals = {}
    for name, source in NATIVE_SOURCES.items():
        with urllib.request.urlopen(source.url, timeout=15) as response:
            raw = response.read(source.archive_bytes + 1)
        verify_binary(name, unpack_archive(name, raw))
        originals[name] = raw
    return originals


@pytest.mark.parametrize("name", ["actionlint", "gitleaks", "shellcheck", "uv"])
def test_selected_original_archive_and_binary_identities(
    archives: dict[str, bytes], name: str
) -> None:
    """Each actual official archive yields exactly the already qualified native executable."""
    raw = unpack_archive(name, archives[name])
    assert raw == (SOURCE / f".tool-cache/native/{name}/{name}").read_bytes()


@pytest.mark.parametrize("name", ["actionlint", "uv"])
@pytest.mark.parametrize("change", ["length", "digest"])
def test_changed_actual_archive_refuses_before_parsing(
    archives: dict[str, bytes], change: str, name: str
) -> None:
    """Truncation and equal-length alteration of the original cannot enter the archive parser."""
    raw = archives[name]
    changed = raw[:-1] if change == "length" else bytes([raw[0] ^ 1]) + raw[1:]
    with pytest.raises(CheckFailure) as error:
        unpack_archive(name, changed)
    assert error.value.code == "native_archive_mismatch"


@pytest.mark.parametrize("name", ["actionlint", "uv"])
@pytest.mark.parametrize("change", ["length", "digest"])
def test_changed_actual_binary_refuses(change: str, name: str) -> None:
    """Actual executable length and byte identity are both mandatory."""
    raw = (SOURCE / f".tool-cache/native/{name}/{name}").read_bytes()
    changed = raw[:-1] if change == "length" else bytes([raw[0] ^ 1]) + raw[1:]
    with pytest.raises(CheckFailure) as error:
        verify_binary(name, changed)
    assert error.value.code == "native_source_mismatch"


def test_all_actual_cached_tools_qualify_without_network() -> None:
    """Verification alone accepts all selected original executable bytes without retrieving anything."""
    assert _invoke(SOURCE)["findings"] == []


def test_missing_cache_requires_explicit_download(tmp_path: Path) -> None:
    """Default verification cannot implicitly fetch a missing native dependency."""
    report = _invoke(tmp_path)
    assert report["exit_code"] == 3 and not (tmp_path / ".tool-cache").exists()


def test_actual_https_bootstrap_and_repeat_verification(tmp_path: Path) -> None:
    """Explicitly download all selected originals, then verify and execute native version help."""
    assert _invoke(tmp_path, "--download")["findings"] == []
    assert _invoke(tmp_path)["findings"] == []
    for name in NATIVE_SOURCES:
        path = tmp_path / f".tool-cache/native/{name}/{name}"
        assert path.read_bytes() == (SOURCE / f".tool-cache/native/{name}/{name}").read_bytes()
        result = subprocess.run([str(path), "--version"], capture_output=True, timeout=15)
        assert result.returncode == 0 and result.stdout
        assert list(path.parent.iterdir()) == [path]


@pytest.mark.parametrize("state", ["wrong-bytes", "nonexecutable", "directory", "symlink"])
def test_existing_invalid_destination_is_never_overwritten(tmp_path: Path, state: str) -> None:
    """Explicit download permission cannot replace an operator's invalid existing input."""
    path = tmp_path / ".tool-cache/native/actionlint/actionlint"
    path.parent.mkdir(parents=True)
    if state == "directory":
        path.mkdir()
    elif state == "symlink":
        path.symlink_to(SOURCE / ".tool-cache/native/actionlint/actionlint")
    else:
        path.write_bytes(
            b"unselected bytes"
            if state == "wrong-bytes"
            else (SOURCE / ".tool-cache/native/actionlint/actionlint").read_bytes()
        )
    report = _invoke(tmp_path, "--only", "actionlint", "--download")
    assert report["exit_code"] in (2, 3) and report["findings"]
    if state == "wrong-bytes":
        assert path.read_bytes() == b"unselected bytes"
    elif state == "nonexecutable":
        assert report["findings"] == [{"code": "native_not_executable", "location": "actionlint"}]


def test_escaping_cache_is_refused(tmp_path: Path) -> None:
    """The bootstrap cannot follow an actual cache symlink outside its repository."""
    root = tmp_path / "repository"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / ".tool-cache").symlink_to(outside, target_is_directory=True)
    report = _invoke(root, "--download")
    assert report["exit_code"] == 2 and list(outside.iterdir()) == []


def test_unavailable_cache_type_is_unavailable(tmp_path: Path) -> None:
    """A file blocking the native cache prevents download and remains intact."""
    (tmp_path / ".tool-cache").write_bytes(b"retained invalid cache")
    assert _invoke(tmp_path, "--download")["exit_code"] == 3
    assert (tmp_path / ".tool-cache").read_bytes() == b"retained invalid cache"


def test_actual_unavailable_https_proxy_cannot_produce_tool_bytes(tmp_path: Path) -> None:
    """A real refused HTTPS connection yields unavailable with no partial native file."""
    report = _invoke(tmp_path, "--download", "--only", "actionlint", unavailable_proxy=True)
    assert report["exit_code"] == 3
    assert list((tmp_path / ".tool-cache/native/actionlint").iterdir()) == []


def test_public_api_rejects_unclassified_tools(tmp_path: Path) -> None:
    """The public implementation cannot bootstrap an arbitrary caller-selected tool URL."""
    with pytest.raises(KeyError):
        ensure_tool(tmp_path, "unknown", download=True)


def test_help_arguments_and_human_report() -> None:
    """The actual public command supplies help, fixed argument refusal and human status."""
    command = [sys.executable, str(SOURCE / "tools/bootstrap_native_tools.py")]
    assert subprocess.run([*command, "--help"], capture_output=True, timeout=15).returncode == 0
    assert (
        subprocess.run([*command, "--only", "unknown"], capture_output=True, timeout=15).returncode
        == 4
    )
    result = subprocess.run([*command, "--root", str(SOURCE)], capture_output=True, timeout=15)
    assert result.returncode == 0 and result.stdout == b"native_tools: passed\n"


def test_actual_make_bootstrap_target_retains_native_success() -> None:
    """The real Make target reaches the bootstrap with all selected cached originals."""
    result = subprocess.run(
        ["make", "--no-print-directory", "native-tools"],
        cwd=SOURCE,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0 and not result.stderr
    assert json.loads(result.stdout.splitlines()[-1])["status"] == "passed"


def test_first_installer_bootstrap_uses_only_the_standard_library(tmp_path: Path) -> None:
    """The first real uv download verifies bytes with site packages disabled, before execution."""
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [
            sys.executable,
            "-S",
            str(SOURCE / "tools/bootstrap_native_tools.py"),
            "--root",
            str(tmp_path),
            "--only",
            "uv",
            "--download",
            "--json",
        ],
        cwd=SOURCE,
        env=environment,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0 and not result.stderr, result.stderr
    assert json.loads(result.stdout)["findings"] == []
    installer = tmp_path / ".tool-cache/native/uv/uv"
    assert installer.read_bytes() == (SOURCE / ".tool-cache/native/uv/uv").read_bytes()
    version = subprocess.run([str(installer), "--version"], capture_output=True, timeout=15)
    assert version.returncode == 0 and version.stdout.startswith(b"uv 0.13.4")
