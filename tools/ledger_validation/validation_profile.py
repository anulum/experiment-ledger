# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Declare the complete initial source validation execution graph."""

import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2]
NATIVE_BINARIES = {
    "workflow_syntax": ("actionlint", "shellcheck"),
    "source_credentials": ("gitleaks",),
}

LEAF_CHECKS = {
    "repository_metadata": ("check_repository_metadata.py", "local_scaffold_declarations"),
    "source_provenance": ("check_source_provenance.py", "local_scaffold_source_provenance"),
    "workflow_policy": ("check_workflow_policy.py", "local_scaffold_workflows"),
    "dependency_alignment": (
        "check_dependency_alignment.py",
        "local_scaffold_development_environment",
    ),
    "documentation": ("check_documentation.py", "local_scaffold_documentation"),
    "repository_inventory": ("check_repository_inventory.py", "local_scaffold_source_inventory"),
}


def commands(root: Path) -> dict[str, tuple[str, ...]]:
    """Return every actual command required by the initial source profile.

    Parameters
    ----------
    root : Path
        Actual repository supplying received inputs and the native working directory.
        Checker and native-tool paths remain bound to this implementation.

    Returns
    -------
    dict[str, tuple[str, ...]]
        Ordered checker and native quality commands. No tests or hosted writes
        are launched by the preflight; CI runs the full test gate separately.
    """
    python = sys.executable
    result: dict[str, tuple[str, ...]] = {
        name: (python, str(SOURCE / "tools" / entry), "--root", str(root), "--json")
        for name, (entry, _) in LEAF_CHECKS.items()
    }
    result.update(
        {
            "source_lint": (
                python,
                "-m",
                "ruff",
                "check",
                "--no-respect-gitignore",
                "tools",
                "tests",
            ),
            "source_format": (
                python,
                "-m",
                "ruff",
                "format",
                "--check",
                "--no-respect-gitignore",
                "tools",
                "tests",
            ),
            "strict_types": (python, "-m", "mypy", "--strict", "tools", "tests"),
            "source_licences": (python, "-m", "reuse", "lint"),
            "workflow_syntax": (
                str(SOURCE / ".tool-cache/native/actionlint/actionlint"),
                "-color=false",
                "-shellcheck=" + str(SOURCE / ".tool-cache/native/shellcheck/shellcheck"),
            ),
            "workflow_static_checks": (
                str(Path(sys.executable).parent / "zizmor"),
                "--offline",
                "--no-config",
                "--no-ignores",
                "--no-progress",
                "--persona",
                "pedantic",
                "--min-severity",
                "informational",
                ".github/workflows",
            ),
            "source_patterns": (python, "-m", "bandit", "-r", "tools", "-q", "-f", "json"),
            "source_credentials": (
                str(SOURCE / ".tool-cache/native/gitleaks/gitleaks"),
                "stdin",
                "--redact",
                "--no-banner",
                "--ignore-gitleaks-allow",
                "--gitleaks-ignore-path",
                "/dev/null",
                "--config",
                str(SOURCE / "gitleaks.toml"),
                "--exit-code",
                "1",
            ),
            "dependency_vulnerabilities": (
                python,
                "-m",
                "pip_audit",
                "--require-hashes",
                "--disable-pip",
                "--strict",
                "--progress-spinner",
                "off",
                "--cache-dir",
                ".tool-cache/pip-audit",
                "--timeout",
                "15",
                "-r",
                "requirements-dev.txt",
                "--format",
                "json",
            ),
            "installed_compatibility": (
                str(Path(sys.executable).parent / "uv"),
                "pip",
                "check",
                "--python",
                python,
            ),
        }
    )
    return result
