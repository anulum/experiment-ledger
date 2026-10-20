# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Inspect the maintained source graph and the initial repository privacy boundary."""

from pathlib import Path

from .inputs import CheckFailure
from .inventory_policy import REQUIRED_DIRECTORIES, REQUIRED_FILES
from .processes import execute
from .provenance import maintained_sources
from .provenance_policy import BINARY_LENGTHS

PRIVATE_PARTS = frozenset(
    {
        ".coordination",
        "04_ARCANE_SAPIENCE",
        "agentic-shared",
        "agentic_project_memory",
        "agentic_group_workspace",
        ".claude",
        ".codex",
        ".gemini",
        ".cursor",
        "AGENTS.md",
        "CLAUDE.md",
        "CODEX.md",
        "GEMINI.md",
        "GROK.md",
        "KIMI.md",
        "CREDENTIALS.md",
    }
)
GENERATED_PARTS = frozenset(
    {".venv", ".tool-cache", "__pycache__", "site", "dist", "build", "target", "node_modules"}
)


def verify(root: Path) -> None:
    """Verify all required paths, source containment and private-path exclusion.

    Parameters
    ----------
    root : Path
        Actual Git repository supplying the current source graph.

    Raises
    ------
    CheckFailure
        For missing required paths, nonregular or escaping source paths,
        private/generated/credential source enrolment, unignored internal
        documentation, actual forbidden root state or excessive source bytes.

    Notes
    -----
    Source inspection includes tracked and nonignored untracked files. There
    is no distribution at this lifecycle; a future package needs its own
    archive-content gate before activation. This ordinary inventory does not
    claim filesystem-race or secret-content qualification.
    """
    ignored = execute(
        ["git", "-C", str(root.resolve()), "check-ignore", "--no-index", "--stdin", "-z"],
        input_bytes=b"docs/internal/current.md\0docs/internal/nested/current.json\0",
        root=root,
        location=".gitignore",
        timeout=15,
    )
    if ignored.returncode != 0 or ignored.stdout != (
        b"docs/internal/current.md\0docs/internal/nested/current.json\0"
    ):
        raise CheckFailure("private_ignore_incomplete", ".gitignore")
    for name in REQUIRED_DIRECTORIES:
        if (root / name).is_symlink() or not (root / name).is_dir():
            raise CheckFailure("required_directory_unavailable", name, unavailable=True)
    names = maintained_sources(root)
    for name in names:
        parts = Path(name).parts
        if (
            PRIVATE_PARTS.intersection(parts)
            or parts[:2] == ("docs", "internal")
            or any(part.startswith(".env") for part in parts)
        ):
            raise CheckFailure("private_source_enrolled", name)
        if GENERATED_PARTS.intersection(parts) or name.endswith((".pyc", ".pyo", ".whl")):
            raise CheckFailure("generated_source_enrolled", name)
        path = root / name
        try:
            if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
                raise CheckFailure("source_path_not_regular", name)
            if not path.is_file():
                raise CheckFailure("source_input_unavailable", name, unavailable=True)
            if path.stat().st_size > BINARY_LENGTHS.get(name, 1048576):
                raise CheckFailure("source_size_exceeded", name)
        except OSError as error:
            raise CheckFailure("source_input_unavailable", name, unavailable=True) from error
    enrolled = set(names)
    for name in REQUIRED_FILES:
        if name not in enrolled:
            raise CheckFailure("required_source_unavailable", name, unavailable=True)
    for path in root.iterdir():
        if path.name in PRIVATE_PARTS or path.name.startswith(".env"):
            raise CheckFailure("forbidden_root_state", path.name)
        if path.name in GENERATED_PARTS - {".venv", ".tool-cache", "__pycache__"}:
            raise CheckFailure("unexpected_generated_state", path.name)
