# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Orchestrate the complete initial validation profile without inferring missing passes."""

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path

from .command import ArgumentParser, Arguments
from .execution import verify_sources
from .inputs import CheckFailure, Json, decode_object, read_bytes
from .native_tools import ensure_tool
from .preflight_reports import write_report
from .processes import execute
from .provenance import maintained_sources
from .provenance_policy import BINARY_SOURCES
from .source_pattern_review import SOURCE_DISPOSITIONS, review_report
from .validation_profile import LEAF_CHECKS, NATIVE_BINARIES, SOURCE, commands


class PreflightArguments(Arguments):
    """Typed parser values for the fixed initial validation profile.

    Attributes
    ----------
    profile : str
        Selected local-scaffold profile.
    only : list[str] or None
        Diagnostic subset; omitted gates remain explicitly not_run.
    report : Path or None
        Optional repository-local cache destination for the final JSON report.
    """

    profile: str
    only: list[str] | None
    report: Path | None


def read_checker_report(
    stdout: bytes, stderr: bytes, *, name: str, scope: str, native_exit: int
) -> dict[str, Json] | None:
    """Decode a bounded original checker report with exact native outcome semantics.

    Parameters
    ----------
    stdout : bytes
        Original standard output, limited to one mebibyte.
    stderr : bytes
        Original standard error; structured checkers require an empty stream.
    name : str
        Required owning checker name.
    scope : str
        Required source qualification scope.
    native_exit : int
        Actual observed process exit.

    Returns
    -------
    dict[str, Json] or None
        Complete original object when valid; None for malformed, duplicate,
        nonfinite or inconsistent output. Received diagnostics are not printed.
    """
    if native_exit not in (0, 2, 3) or len(stdout) > 1048576 or stderr:
        return None
    try:
        leaf = decode_object(stdout, "checker_report", 1048576)
    except CheckFailure:
        return None
    if set(leaf) != {
        "check",
        "scope",
        "status",
        "exit_code",
        "findings",
    }:
        return None
    findings = leaf["findings"]
    if (
        leaf["check"] != name
        or leaf["scope"] != scope
        or type(leaf["exit_code"]) is not int
        or leaf["exit_code"] != native_exit
        or leaf["status"] != {0: "passed", 2: "refused", 3: "unavailable"}.get(native_exit)
        or not isinstance(findings, list)
        or (native_exit == 0 and findings)
        or (native_exit != 0 and not findings)
    ):
        return None
    for finding in findings:
        if (
            not isinstance(finding, dict)
            or set(finding) != {"code", "location"}
            or not isinstance(finding["code"], str)
            or not isinstance(finding["location"], str)
        ):
            return None
    return leaf


def run_check(root: Path, name: str) -> dict[str, Json]:
    """Run one real named gate and validate its native exit/report relationship.

    Parameters
    ----------
    root : Path
        Actual repository under inspection.
    name : str
        Name from the complete profile command map.

    Returns
    -------
    dict[str, Json]
        Actual native result, redacted outcome and original leaf report when
        valid. Missing tools/checkers, malformed reports and failed exits
        cannot produce passed status.

    Raises
    ------
    KeyError
        When the requested gate is outside the owned profile.
    """
    command = commands(root)[name]
    if name in LEAF_CHECKS and not (SOURCE / "tools" / LEAF_CHECKS[name][0]).is_file():
        return {
            "check": name,
            "status": "unavailable",
            "native_exit": None,
            "finding": "checker_unavailable",
        }
    try:
        if name in ("source_lint", "source_format", "strict_types"):
            verify_sources(root, ("pyproject.toml",))
        if name == "source_credentials":
            verify_sources(SOURCE, ("gitleaks.toml",))
        if name == "dependency_vulnerabilities":
            prerequisite = run_check(root, "dependency_alignment")
            if prerequisite["status"] != "passed":
                return {
                    "check": name,
                    "status": prerequisite["status"],
                    "native_exit": None,
                    "finding": "dependency_alignment_unqualified",
                    "prerequisite": prerequisite,
                }
        for tool in NATIVE_BINARIES.get(name, ()):
            ensure_tool(SOURCE, tool)
        source_input = None
        if name == "source_credentials":
            source_input = b"\n".join(
                path.encode("utf-8") + b"\n" + read_bytes(root, path, 1048576)
                for path in maintained_sources(root)
                if path not in BINARY_SOURCES
            )
        result = execute(command, root=root, location=name, timeout=120, input_bytes=source_input)
    except CheckFailure as error:
        return {
            "check": name,
            "status": "unavailable" if error.exit_code == 3 else "refused",
            "native_exit": None,
            "finding": error.code,
        }
    outcome: dict[str, Json] = {
        "check": name,
        "status": "passed" if result.returncode == 0 else "refused",
        "native_exit": result.returncode,
        "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
    }
    if name == "dependency_vulnerabilities":
        try:
            outcome["report"] = decode_object(result.stdout, "dependency_audit", 1048576)
        except CheckFailure as error:
            outcome["status"] = "unavailable" if result.returncode else "refused"
            outcome["finding"] = error.code
    if name == "source_patterns":
        try:
            if result.stderr:
                raise CheckFailure("source_pattern_report_invalid", "bandit")
            outcome["report"] = decode_object(result.stdout, "bandit_report", 1048576)
            review_report(root, result.stdout, native_exit=result.returncode)
            outcome["review_dispositions"] = [value[1] for value in SOURCE_DISPOSITIONS.values()]
            outcome["status"] = "passed"
        except CheckFailure as error:
            outcome["status"] = "unavailable" if error.exit_code == 3 else "refused"
            outcome["finding"] = error.code
    if name in LEAF_CHECKS:
        leaf = read_checker_report(
            result.stdout,
            result.stderr,
            name=name,
            scope=LEAF_CHECKS[name][1],
            native_exit=result.returncode,
        )
        if leaf is not None:
            outcome["status"] = leaf["status"]
            outcome["report"] = leaf
        else:
            outcome["status"] = "refused"
            outcome["finding"] = "checker_report_invalid"
    return outcome


def main(argv: Sequence[str] | None = None) -> int:
    """Run the actual profile or an explicitly incomplete diagnostic subset.

    Parameters
    ----------
    argv : Sequence[str] or None
        Public command arguments, or the process arguments when absent.

    Returns
    -------
    int
        Zero only when every profile gate actually passed; two for refusals
        or not_run gates, three for unavailable inputs/output. Argument
        errors exit four and help exits zero.
    """
    parser = ArgumentParser(
        prog="preflight", description="Run the actual Experiment Ledger validation profile."
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--profile", choices=("local-scaffold",), default="local-scaffold")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--only", nargs="+", choices=tuple(commands(Path("."))))
    parser.add_argument("--report", type=Path)
    options = PreflightArguments()
    parser.parse_args(argv, namespace=options)
    root = options.root.resolve()
    results: list[Json] = []
    for name in commands(root):
        if options.only is not None and name not in options.only:
            results.append({"check": name, "status": "not_run", "native_exit": None})
        else:
            results.append(run_check(root, name))
    states = {item["status"] for item in results if isinstance(item, dict)}
    exit_code = 3 if "unavailable" in states else 0 if states == {"passed"} else 2
    report: dict[str, Json] = {
        "check": "preflight",
        "profile": options.profile,
        "status": {0: "passed", 2: "refused", 3: "unavailable"}[exit_code],
        "exit_code": exit_code,
        "checks": results,
        "findings": [],
    }
    if options.report is not None:
        try:
            write_report(root, options.report, report)
        except CheckFailure as error:
            exit_code = max(exit_code, error.exit_code)
            report["status"] = "unavailable" if exit_code == 3 else "refused"
            report["exit_code"] = exit_code
            report["findings"] = [{"code": error.code, "location": error.location}]
    print(
        json.dumps(report, sort_keys=True)
        if options.json
        else "preflight: " + str(report["status"])
    )
    return exit_code
