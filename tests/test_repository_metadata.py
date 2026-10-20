# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Exercise the actual repository metadata CLI, declarations and byte bindings."""

import hashlib
import json
from pathlib import Path
from typing import cast

import pytest

from ledger_validation.inputs import CheckFailure, Json, decode_object

from .metadata_support import INPUTS, SOURCE, _generate, _report, _rewrite_metadata, _run, _snapshot


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """Create a complete declaration input set from the actual repository.

    Parameters
    ----------
    tmp_path : Path
        Owned temporary directory on Samsung.

    Returns
    -------
    Path
        Isolated repository input directory.
    """
    for name in INPUTS:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((SOURCE / name).read_bytes())
    return tmp_path


def test_complete_declarations_are_checked_without_mutation(root: Path) -> None:
    """The actual command accepts the complete repository and preserves all bytes.

    Parameters
    ----------
    root : Path
        Complete isolated input directory.
    """
    before = _snapshot(root)
    result = _report(_run(root), 0)
    assert result == {
        "check": "repository_metadata",
        "scope": "local_scaffold_declarations",
        "status": "passed",
        "exit_code": 0,
        "findings": [],
    }
    assert _snapshot(root) == before


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (("repository_name",), "OTHER"),
        (("owner_group",), "OTHER"),
        (("lifecycle",), "public_repository"),
        (("evidence_maturity",), "qualified"),
        (("capabilities",), ["append"]),
        (("claims",), ["durable"]),
        (("qualified_owned_schema_ids",), ["experiment_ledger.record.v1"]),
        (("planned_owned_schema_ids",), ["foreign.record.v1"]),
        (("domain_runtime_dependencies",), ["a-runtime-package"]),
        (("unexpected",), True),
        (("validation_profile", "id"), "another-profile"),
        (("validation_profile", "revision"), "2026-01-01"),
        (("validation_profile", "standard_sha256"), "0" * 64),
        (("validation_profile", "profile_sha256"), "0" * 64),
        (("tooling_python", "actual_version"), "3.14.7"),
        (("tooling_python", "supported_range"), ">=3"),
        (("tooling_python", "development_lock_sha256"), "0" * 64),
    ],
)
def test_incorrect_declarations_refuse(root: Path, field: tuple[str, ...], value: Json) -> None:
    """Changed ownership, lifecycle, claims and source policy cannot pass.

    Parameters
    ----------
    root : Path
        Complete isolated input directory.
    field : tuple[str, ...]
        Public metadata member path being changed.
    value : Json
        Received replacement declaration.
    """
    metadata = cast(dict[str, Json], json.loads((root / "repository-domain.json").read_text()))
    node = metadata
    for member in field[:-1]:
        child = node[member]
        assert isinstance(child, dict)
        node = child
    node[field[-1]] = value
    _rewrite_metadata(root, metadata)
    before = _snapshot(root)
    report = _report(_run(root), 2)
    assert report["status"] == "refused"
    assert report["findings"] == [
        {"code": "metadata_mismatch", "location": "repository-domain.json"}
    ]
    assert _snapshot(root) == before


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        (b"{", "input_invalid"),
        (b"\xff", "input_invalid"),
        (b'{"value":"\\ud800"}', "input_invalid"),
        (b'{"value":NaN}', "input_invalid"),
        (b'{"value":Infinity}', "input_invalid"),
        (b'{"value":-Infinity}', "input_invalid"),
        (b'{"value":1e999}', "input_invalid"),
        (b'{"name":"first","name":"second"}', "input_invalid"),
        (b'{"nested":' + b"[" * 1500 + b"0" + b"]" * 1500 + b"}", "metadata_mismatch"),
        (b"[]", "input_invalid"),
        (b"null", "input_invalid"),
    ],
    ids=[
        "syntax",
        "utf8",
        "surrogate",
        "nan",
        "positive-infinity",
        "negative-infinity",
        "exponent-overflow",
        "duplicate-member",
        "valid-deep-unknown-member",
        "array-root",
        "null-root",
    ],
)
def test_received_json_contracts_refuse(root: Path, raw: bytes, code: str) -> None:
    """Malformed JSON and valid undeclared structures retain their distinct refusals.

    Parameters
    ----------
    root : Path
        Complete isolated input directory.
    raw : bytes
        Original received document.
    code : str
        Expected parser or metadata-contract finding.
    """
    (root / "repository-domain.json").write_bytes(raw)
    before = _snapshot(root)
    report = _report(_run(root), 2)
    assert report["findings"] == [{"code": code, "location": "repository-domain.json"}]
    assert _snapshot(root) == before


@pytest.mark.parametrize("name", INPUTS)
def test_unavailable_required_inputs_are_not_passed(root: Path, name: str) -> None:
    """Every missing required source produces unavailable rather than success.

    Parameters
    ----------
    root : Path
        Complete isolated input directory.
    name : str
        Required input removed from this isolated copy.
    """
    (root / name).unlink()
    before = _snapshot(root)
    report = _report(_run(root), 3)
    assert report["status"] == "unavailable"
    assert report["findings"] == [{"code": "input_unavailable", "location": name}]
    assert _snapshot(root) == before


@pytest.mark.parametrize("name", ["schemas/repository-domain.schema.json", "requirements-dev.txt"])
def test_source_byte_drift_refuses(root: Path, name: str) -> None:
    """Whitespace drift still changes the exact selected source or lock identity.

    Parameters
    ----------
    root : Path
        Complete isolated input directory.
    name : str
        Exact source whose bytes change.
    """
    path = root / name
    path.write_bytes(path.read_bytes() + b"\n")
    report = _report(_run(root), 2)
    assert report["findings"] == [
        {
            "code": "schema_source_changed" if name.endswith(".json") else "metadata_mismatch",
            "location": name if name.endswith(".json") else "repository-domain.json",
        }
    ]


@pytest.mark.parametrize("field", ["claims", "source_metadata", "unexpected"])
def test_incomplete_or_unearned_inventory_refuses(root: Path, field: str) -> None:
    """The derived inventory cannot add claims, lose its binding or add members.

    Parameters
    ----------
    root : Path
        Complete isolated input directory.
    field : str
        Inventory member changed in this input.
    """
    path = root / "capability-inventory.json"
    value = cast(dict[str, Json], json.loads(path.read_text()))
    value[field] = ["unexpected"]
    path.write_text(json.dumps(value) + "\n")
    report = _report(_run(root), 2)
    assert report["findings"] == [
        {"code": "inventory_mismatch", "location": "capability-inventory.json"}
    ]


@pytest.mark.parametrize("size", [65536, 65537])
def test_actual_metadata_byte_limit(root: Path, size: int) -> None:
    """A complete declaration fits exactly at its bound and refuses one extra byte.

    Parameters
    ----------
    root : Path
        Complete isolated input directory.
    size : int
        Original received metadata size.
    """
    path = root / "repository-domain.json"
    raw = path.read_bytes()
    path.write_bytes(raw + b" " * (size - len(raw)))
    inventory_path = root / "capability-inventory.json"
    inventory = cast(dict[str, Json], json.loads(inventory_path.read_text()))
    source = inventory["source_metadata"]
    assert isinstance(source, dict)
    source["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    inventory_path.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n")
    expected = 0 if size == 65536 else 2
    report = _report(_run(root), expected)
    if size == 65537:
        assert report["findings"] == [
            {"code": "input_too_large", "location": "repository-domain.json"}
        ]


def test_default_directory_and_text_output(root: Path) -> None:
    """The actual current-directory and human-output route uses the same check.

    Parameters
    ----------
    root : Path
        Complete isolated input directory.
    """
    result = _run(root, machine=False, explicit_root=False)
    assert result.returncode == 0 and result.stdout == "repository_metadata: passed\n"
    assert result.stderr == ""


@pytest.mark.parametrize(("argument", "expected"), [("--help", 0), ("--unknown", 4)])
def test_cli_help_and_invalid_invocation(root: Path, argument: str, expected: int) -> None:
    """Actual help and invalid arguments retain their documented native exits.

    Parameters
    ----------
    root : Path
        Complete isolated input directory.
    argument : str
        Public CLI argument.
    expected : int
        Required exit code.
    """
    result = _run(root, argument)
    assert result.returncode == expected
    if expected == 4:
        assert result.stdout == ""
        assert result.stderr == "repository_metadata: invalid command arguments\n"
    else:
        assert "Check Experiment Ledger repository metadata declarations." in result.stdout
        assert result.stderr == ""


@pytest.mark.parametrize("extra", [0, 1])
def test_public_byte_decoder_uses_original_declaration_bound(root: Path, extra: int) -> None:
    """The public in-memory decoder accepts exact original bytes and refuses one byte beyond its bound."""
    raw = (root / "repository-domain.json").read_bytes()
    if extra:
        with pytest.raises(CheckFailure) as error:
            decode_object(raw, "repository-domain.json", len(raw) - extra)
        assert error.value.code == "input_too_large"
    else:
        assert decode_object(raw, "repository-domain.json", len(raw)) == json.loads(raw)


def test_inventory_regeneration_matches_original_bytes_without_existing_output(root: Path) -> None:
    """Two real generator processes reproduce the maintained output without mutating source."""
    inventory = root / "capability-inventory.json"
    expected = inventory.read_bytes()
    inventory.unlink()
    before = _snapshot(root)
    first, second = _generate(root), _generate(root)
    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout == expected
    assert first.stderr == second.stderr == b""
    assert _snapshot(root) == before
    inventory.write_bytes(first.stdout)
    assert _report(_run(root), 0)["status"] == "passed"


@pytest.mark.parametrize("suffix", [b"\n", b" "])
def test_serialization_drift_is_refused(root: Path, suffix: bytes) -> None:
    """Equivalent parsed content cannot hide a noncanonical generated byte sequence."""
    path = root / "capability-inventory.json"
    original = path.read_bytes()
    path.write_bytes(original + suffix)
    assert json.loads(original) == json.loads(path.read_bytes())
    assert _report(_run(root), 2)["findings"] == [
        {"code": "inventory_mismatch", "location": "capability-inventory.json"}
    ]
    assert _generate(root).stdout == original


@pytest.mark.parametrize(
    ("name", "replacement", "expected", "code"),
    [
        ("repository-domain.json", b'{"value":NaN}', 2, "input_invalid"),
        ("repository-domain.json", b"{}", 2, "metadata_mismatch"),
        ("schemas/repository-domain.schema.json", b"{}", 2, "schema_source_changed"),
        ("requirements-dev.txt", None, 3, "input_unavailable"),
    ],
)
def test_generator_invalid_sources_emit_no_partial_inventory(
    root: Path, name: str, replacement: bytes | None, expected: int, code: str
) -> None:
    """Invalid and missing original inputs preserve native errors and empty stdout."""
    path = root / name
    if replacement is None:
        path.unlink()
    else:
        path.write_bytes(replacement)
    before = _snapshot(root)
    result = _generate(root)
    assert result.returncode == expected
    assert result.stdout == b""
    assert json.loads(result.stderr) == {"code": code, "location": name}
    assert _snapshot(root) == before


@pytest.mark.parametrize(("argument", "expected"), [("--help", 0), ("--unknown", 4)])
def test_generator_help_and_invalid_arguments(root: Path, argument: str, expected: int) -> None:
    """The generator exposes normal help and fixed invalid-argument exits."""
    result = _generate(root, argument)
    assert result.returncode == expected
    if expected == 4:
        assert result.stdout == b""
        assert result.stderr == b"generate_capability_inventory: invalid command arguments\n"
    else:
        assert b"Generate the canonical Experiment Ledger capability inventory." in result.stdout
        assert result.stderr == b""
