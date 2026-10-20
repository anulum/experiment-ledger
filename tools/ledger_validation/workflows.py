# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Check the closed initial workflow graph and its read-only execution contracts."""

from pathlib import Path
from typing import cast

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from .inputs import CheckFailure, Json, read_bytes

type Yaml = str | list[Yaml] | dict[str, Yaml]

CHECKOUT = "actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd"
PYTHON = "actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405"
UV = "astral-sh/setup-uv@37802adc94f370d6bfd71619e3f0bf239e1f3b78"
CODEQL = "github/codeql-action/{}@0d579ffd059c29b07949a3cce3983f0780820c98"
SCORECARD = (
    "docker://ghcr.io/ossf/scorecard-action@sha256:"
    "2dd6a6d60100f78ef24e14a47941d0087a524b4d3642041558239b1c6097c941"
)
UV_CHECKSUM = "b9980552309f09c15172b8be828555e375097f16deb459795ce7bfd200380f0b"
SCORECARD_EVENT = (
    "${{ github.event_name == 'pull_request' || "
    "github.ref == format('refs/heads/{0}', github.event.repository.default_branch) }}"
)
DEVELOPMENT_ENVIRONMENT = {
    "UV_LINK_MODE": "hardlink",
    "UV_CACHE_DIR": "${{ github.workspace }}/.tool-cache/uv",
    "PRE_COMMIT_HOME": "${{ github.workspace }}/.tool-cache/pre-commit",
}
INSTALL = (
    "mkdir -p .tool-cache/tmp\n"
    "uv venv --python 3.13.16 .venv\n"
    "uv pip sync --python .venv/bin/python --require-hashes "
    "--link-mode hardlink requirements-dev.txt\n"
    "make native-tools"
)
COMMANDS = {
    "ci": ("validation", "make ci"),
    "docs": ("documentation", "make docs"),
    "pre-commit": (
        "hooks",
        ".venv/bin/python -m pre_commit run --all-files --show-diff-on-failure",
    ),
    "sbom": (
        "inventory",
        "mkdir -p .tool-cache/sbom\n"
        ".venv/bin/python -m cyclonedx_py requirements requirements-dev.txt "
        "--of JSON -o .tool-cache/sbom/development.cdx.json",
    ),
    "security-audit": ("source-audit", "make source-audit"),
}


def _decode(node: Node | None) -> Yaml:
    if isinstance(node, ScalarNode):
        return cast(str, node.value)
    if isinstance(node, SequenceNode):
        return [_decode(child) for child in node.value]
    if isinstance(node, MappingNode):
        result: dict[str, Yaml] = {}
        for key, value in node.value:
            if not isinstance(key, ScalarNode) or key.value in result:
                raise ValueError("Non-scalar or duplicate YAML member")
            result[key.value] = _decode(value)
        return result
    raise ValueError("Missing YAML document")


def _action(uses: str, options: dict[str, Json]) -> dict[str, Json]:
    return {"uses": uses, "with": options}


def _job(steps: list[Json], timeout: str = "20") -> dict[str, Json]:
    return {"runs-on": "ubuntu-24.04", "timeout-minutes": timeout, "steps": steps}


def _expected_jobs(stem: str) -> dict[str, Json]:
    checkout = _action(CHECKOUT, {"persist-credentials": "false"})
    if stem == "codeql":
        return {
            "python-analysis": _job(
                [
                    checkout,
                    _action(
                        CODEQL.format("init"),
                        {
                            "languages": "python",
                            "build-mode": "none",
                            "tools": "linked",
                            "ram": "2048",
                            "threads": "1",
                        },
                    ),
                    _action(
                        CODEQL.format("analyze"),
                        {
                            "upload": "never",
                            "upload-database": "false",
                            "output": ".tool-cache/codeql-results",
                        },
                    ),
                ]
            )
        }
    if stem == "scorecard":
        return {
            "scorecard": {
                **_job(
                    [
                        checkout,
                        {"run": "mkdir -p .tool-cache/scorecard"},
                        {
                            "uses": SCORECARD,
                            "env": {
                                "INPUT_RESULTS_FILE": ".tool-cache/scorecard/results.json",
                                "INPUT_RESULTS_FORMAT": "json",
                                "INPUT_PUBLISH_RESULTS": "false",
                                "INPUT_FILE_MODE": "archive",
                                "INPUT_REPO_TOKEN": "${{ github.token }}",
                                "INPUT_INTERNAL_DEFAULT_TOKEN": "${{ github.token }}",
                            },
                        },
                    ],
                    "15",
                ),
                "if": SCORECARD_EVENT,
            }
        }
    job, command = COMMANDS[stem]
    jobs = {
        job: _job(
            [
                checkout,
                _action(PYTHON, {"python-version": "3.13.16"}),
                _action(
                    UV,
                    {
                        "version": "0.12.22",
                        "enable-cache": "true",
                        "cache-dependency-glob": "requirements-dev.txt",
                        "cache-local-path": "${{ github.workspace }}/.tool-cache/uv",
                        "checksum": UV_CHECKSUM,
                        "prune-cache": "false",
                    },
                ),
                {"run": INSTALL},
                {"run": command},
            ]
        )
    }
    jobs[job]["env"] = dict(DEVELOPMENT_ENVIRONMENT)
    if stem == "ci":
        jobs["ci-gate"] = {
            **_job(
                [
                    {
                        "env": {"VALIDATION_RESULT": "${{ needs.validation.result }}"},
                        "run": 'test "$VALIDATION_RESULT" = success',
                    }
                ],
                "2",
            ),
            "needs": ["validation"],
            "if": "${{ always() }}",
        }
    return dict(jobs)


def _normalise(value: Yaml, path: tuple[str, ...] = ()) -> Yaml:
    if isinstance(value, dict):
        display_names = (
            not path
            or (len(path) == 2 and path[0] == "jobs")
            or (len(path) == 4 and path[0] == "jobs" and path[2] == "steps")
        )
        return {
            key: _normalise(item, (*path, key))
            for key, item in value.items()
            if key != "name" or not display_names
        }
    if isinstance(value, list):
        return [_normalise(item, (*path, "*")) for item in value]
    return value.removesuffix("\n")


def verify(root: Path) -> None:
    """Verify every initial workflow against the selected source execution policy.

    Parameters
    ----------
    root : Path
        Repository containing all seven maintained workflow definitions.

    Raises
    ------
    CheckFailure
        For unavailable, oversized or malformed input, duplicate YAML members,
        an unknown workflow/job, filtered triggers, altered execution commands,
        changed action/tool pins, write permissions or unbounded jobs.

    Notes
    -----
    This is a closed local-scaffold policy: changing responsibilities requires
    a reviewed policy change. It does not run actions, establish hosted service
    settings or replace native actionlint and zizmor checks.
    """
    directory = root / ".github/workflows"
    required = {*COMMANDS, "codeql", "scorecard"}
    actual = {path.name for path in directory.iterdir()} if directory.is_dir() else set()
    expected = {stem + ".yml" for stem in required}
    if expected - actual:
        raise CheckFailure("workflow_inputs_unavailable", ".github/workflows", unavailable=True)
    if actual - expected:
        raise CheckFailure("workflow_inventory_mismatch", ".github/workflows")
    for stem in sorted(required):
        name = ".github/workflows/" + stem + ".yml"
        raw = read_bytes(root, name, 65536)
        try:
            value = _normalise(_decode(yaml.compose(raw.decode("utf-8"), Loader=yaml.BaseLoader)))
        except (ValueError, RecursionError, yaml.YAMLError) as error:
            raise CheckFailure("workflow_yaml_invalid", name) from error
        wanted: dict[str, Json] = {
            "on": {"push": "", "pull_request": "", "workflow_dispatch": ""},
            "permissions": {"contents": "read"},
            "concurrency": {
                "group": "${{ github.workflow }}-${{ github.ref }}",
                "cancel-in-progress": "true",
            },
            "jobs": _expected_jobs(stem),
        }
        if value != wanted:
            raise CheckFailure("workflow_policy_mismatch", name)
