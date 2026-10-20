# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Exercise atomic report publication using actual native checker outcomes."""

import json
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest

from ledger_validation.inputs import CheckFailure, Json
from ledger_validation.preflight_reports import write_report

from .provenance_support import SOURCE


@pytest.fixture(scope="module")
def native_report() -> dict[str, Json]:
    """Read the actual native metadata result without inventing a successful report.

    Returns
    -------
    dict[str, Json]
        Complete original public checker report.
    """
    result = subprocess.run(
        [sys.executable, str(SOURCE / "tools/check_repository_metadata.py"), "--json"],
        cwd=SOURCE,
        capture_output=True,
        check=True,
    )
    assert not result.stderr
    return cast(dict[str, Json], json.loads(result.stdout))


@pytest.mark.parametrize("absolute", [False, True])
def test_actual_native_report_replaces_complete_cached_output(
    tmp_path: Path, native_report: dict[str, Json], absolute: bool
) -> None:
    """Both supported destination forms atomically replace old bytes with the full result."""
    relative = Path(".tool-cache/reports/native.json")
    destination = tmp_path / relative
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"previous retained report\n")
    write_report(tmp_path, destination if absolute else relative, native_report)
    assert destination.read_bytes() == (json.dumps(native_report, sort_keys=True) + "\n").encode()
    assert list(destination.parent.iterdir()) == [destination]


@pytest.mark.parametrize("name", ["report.json", ".tool-cache/../../outside.json"])
def test_output_outside_owned_cache_refuses_before_writing(
    tmp_path: Path, native_report: dict[str, Json], name: str
) -> None:
    """Repository source and parent traversal are outside the output capability."""
    with pytest.raises(CheckFailure) as error:
        write_report(tmp_path, Path(name), native_report)
    assert error.value.code == "report_path_refused"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("location", ["cache", "parent", "destination"])
def test_actual_escaping_symlinks_cannot_redirect_report_output(
    tmp_path: Path, native_report: dict[str, Json], location: str
) -> None:
    """Cache, intermediate and final path symlinks cannot expose bytes outside the root."""
    root = tmp_path / "repository"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "retained.json"
    sentinel.write_bytes(b"retained original outside report\n")
    cache = root / ".tool-cache"
    if location == "cache":
        cache.symlink_to(outside, target_is_directory=True)
        path = cache / "retained.json"
    else:
        cache.mkdir()
        if location == "parent":
            (cache / "reports").symlink_to(outside, target_is_directory=True)
            path = cache / "reports/retained.json"
        else:
            path = cache / "report.json"
            path.symlink_to(sentinel)
    with pytest.raises(CheckFailure) as error:
        write_report(root, path, native_report)
    assert error.value.code == "report_path_refused"
    assert list(outside.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b"retained original outside report\n"


def test_failed_native_replacement_preserves_destination_and_removes_temporary_bytes(
    tmp_path: Path, native_report: dict[str, Json]
) -> None:
    """Replacing a real directory fails while preserving old contents and cleaning own spool."""
    cache = tmp_path / ".tool-cache"
    destination = cache / "report.json"
    destination.mkdir(parents=True)
    sentinel = destination / "retained.json"
    sentinel.write_bytes(b"retained original destination contents\n")
    with pytest.raises(CheckFailure) as error:
        write_report(tmp_path, destination, native_report)
    assert error.value.code == "report_unavailable" and error.value.exit_code == 3
    assert list(cache.iterdir()) == [destination]
    assert list(destination.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b"retained original destination contents\n"


def test_unavailable_parent_preserves_original_file(
    tmp_path: Path, native_report: dict[str, Json]
) -> None:
    """A regular file cannot serve as an output directory and is preserved on refusal."""
    cache = tmp_path / ".tool-cache"
    cache.mkdir()
    parent = cache / "reports"
    parent.write_bytes(b"retained original source\n")
    with pytest.raises(CheckFailure) as error:
        write_report(tmp_path, parent / "native.json", native_report)
    assert error.value.code == "report_unavailable" and error.value.exit_code == 3
    assert parent.read_bytes() == b"retained original source\n"
    assert list(cache.iterdir()) == [parent]
