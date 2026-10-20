<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
EXPERIMENT-LEDGER — repository identity and validation foundation
-->

# Validation tooling

These commands inspect the local repository foundation. Ledger capabilities, qualified experiment formats and domain dependencies remain empty. Each report qualifies its stated source scope.

| Command | Make target | Scope |
| --- | --- | --- |
| `tools/check_repository_metadata.py` | `metadata` | Complete metadata declarations and exact byte bindings |
| `tools/generate_capability_inventory.py` | `metadata-inventory` | Canonical inventory bytes from validated source declarations |
| `tools/check_source_provenance.py` | `provenance` | Maintained-source ownership and selected originals |
| `tools/check_workflow_policy.py` | `workflow-policy` | Seven classified workflow execution contracts |
| `tools/check_dependency_alignment.py` | `dependencies` | Actual installed development graph and reviewed execution configuration |
| `tools/generate_dependency_provenance.py` | `dependency-provenance` | Complete provenance regenerated from independent selected identities and actual installed bytes |
| `tools/check_documentation.py` | `docs` | Local links, strict rendering and public projection |
| `tools/check_repository_inventory.py` | `inventory` | Required paths, source containment and repository privacy |
| `tools/bootstrap_native_tools.py` | `native-checks`, `native-tools` | Selected native archives and executable identities |
| `tools/check_native_gate.py` | Named native targets below | One classified native quality gate |
| `tools/preflight.py` | `preflight` | Complete local-scaffold validation profile |

Repository check commands accept `--root . --json`. Their JSON includes the check, scope, status, native outcome and fixed finding identifiers. Without `--json`, they print human-readable status; `--help` describes their options.

| Exit | Meaning |
| --- | --- |
| 0 | The complete requested check qualifies its stated scope. |
| 2 | Received content or source correspondence is refused. |
| 3 | Required input, execution or output is unavailable. |
| 4 | Command arguments are invalid. |

## Metadata and original JSON bytes

```sh
python tools/check_repository_metadata.py --root . --json
make metadata
```

The metadata check compares the complete local declarations with the selected project policy, binds the exact schema bytes and development lock digest, and checks the derived capability inventory against the original metadata bytes. Capabilities, claims, qualified formats and domain dependencies must remain empty. Four planned format names are declarations.

`make metadata-inventory` emits deterministic UTF-8 JSON to stdout. The owning generator validates the complete metadata, schema and lock before emitting any output, and can regenerate a missing inventory without reading that output. It uses sorted members, two-space indentation and one trailing newline. `make metadata` compares the original inventory bytes with regeneration and refuses serialization drift as well as content drift. Generation leaves repository files untouched; validate a candidate before replacing the maintained output. This generator owns the capability inventory only. Dependency provenance retains its original source records and separate qualification.

JSON declarations are limited to 65,536 original bytes and the lock to 1,048,576 bytes. Duplicate members, nonfinite numbers, invalid Unicode, excessive nesting and non-object declarations refuse. `decode_object` provides the same strict semantics for original in-memory bytes. `read_object` also retains the original file bytes. Neither rewrites its inputs.

## Maintained-source provenance

```sh
make provenance
```

Native Git enrols tracked files, including deleted tracked paths, and nonignored untracked files. The checker validates complete project notices, conflicting SPDX identifiers, strict source JSON and exact ownership sidecars. Fixed selected-source digests preserve the original AGPL licence texts, branding bytes and REUSE policy. Existing top-level `SPDX-License-Identifier` and `spdx_license_identifier` JSON ownership values must agree with their sidecar; nested component licences retain their separate meaning.

Text sources are bounded at 1,048,576 bytes, source sidecars at 8,192 bytes and selected binary assets at their exact original lengths and digests. Missing required source, sidecar or Git input yields unavailable. Additional third-party material needs explicit source policy that preserves its ownership. The Make target also runs native REUSE classification.

## Workflow execution and dependencies

```sh
make workflow-policy
make dependencies
make workflow-native
make workflow-static
```

The workflow policy classifies every job in seven exact definitions. Correctness CI runs for every push, pull request and manual dispatch and has a final gate tied to the actual validation result. Jobs have bounded timeouts, read-only repository permissions, exact toolchain patches, hash-locked installation, workspace-local caches and explicit hardlinks. GitHub actions use verified commit objects. The prepared Scorecard container uses its selected immutable image digest; its upstream entry point supports pull requests and default-branch refs. Reporting remains disabled. CodeQL analysis disables uploads. Hosted execution and settings require their own evidence. The dependency-inventory workflow uses the pinned CycloneDX generator with explicit schema validation and reproducible output. It removes an inherited source-date timestamp input, so repeated generation of the same selected lock and toolchain retains identical bytes.

REUSE 6.2.0 is selected from its original source distribution. Install commands pass `--build-constraints requirements-dev.txt` alongside `--require-hashes`, so any required isolated build uses the selected Poetry Core 2.5.0 backend and its recorded artifact hashes. This constrains new builds; previously built wheels retain the selected cache's trust boundary. Source-build reproducibility also depends on the recorded timestamp and optional translation compiler.

Dependency alignment checks the actual Python 3.13.16 interpreter and the complete selected installed distribution set. It validates direct/transitive roles, exact lock versions and source hashes, active dependency compatibility, installed METADATA identities and the complete installed licence/attribution file catalogue with original byte identities. Omitted or repeated licence evidence refuses. Reviewed Make, hook, analysis and credential-scanner configurations are byte-bound in `ledger_validation.execution`; semantic workflow checks bind their installation and execution contracts. Configuration changes require a corresponding owned review and policy update.

Each package's declared licence classifiers, licence expression, original licence label and complete dependency declarations must also match the installed metadata. All four fields are required, including explicit null values when the original label is absent. An unchanged METADATA hash cannot qualify changed or omitted descriptive fields.

`make -s dependency-provenance` emits deterministic original provenance bytes without reading the existing output. The separately authored `dependency-source-selections.json` retains the reviewed original artifact, METADATA and licence identities; its exact source bytes are bound by the generator. A source-selection change requires corresponding review and qualification. The generator reads actual installed METADATA and the complete original licence catalogue, computes their identities and descriptive projections, and refuses missing or altered originals. Current active native descriptors derive from the owning bootstrap pins, including ShellCheck. Original CodeQL and audit records remain historical source observations; generation performs no download, installation, native execution or new security audit. The ordinary dependency check compares the complete original provenance bytes with regeneration after its environment and execution checks. Keep candidate output outside maintained source until generation succeeds and the original source identities are reconciled.

Native Actionlint uses the explicitly selected and independently verified ShellCheck executable. Zizmor runs offline with the pedantic persona, informational severity enabled and configuration/ignore overrides disabled. Native executable identity is checked before launch.

## Documentation and inventory

```sh
make docs
make inventory
```

Documentation checks maintained Markdown links and anchors, excludes private or unearned public content, builds the actual configured Python API with strict MkDocs and inspects generated HTML. Output stays under `.tool-cache/documentation`. The renderer uses the reviewed repository configuration and plugins.

For reproducible documentation bytes, record and reuse the generator's [source-date input](https://reproducible-builds.org/specs/source-date-epoch/) alongside the exact source and locked toolchain. For a committed source tree, use `SOURCE_DATE_EPOCH="$(git log -1 --format=%ct)" make docs`. Rebuilding that same source with the same recorded epoch reproduces the complete site, including the compressed sitemap. A different epoch can change its gzip header even when the uncompressed content is identical. Keep this input in reproduction records rather than treating two builds with different dates as the same build inputs.

Inventory requires the original foundation paths and all Git-enrolled sources to remain available, regular, contained and within their byte bounds. It verifies actual ignore protection and rejects enrolled private/generated material, forbidden workspace or credential state, and unexpected build output. Python tooling and tests are admitted only under `tools/` and `tests/`, which the native lint, type and coverage gates inspect recursively. Other files must belong to the declared foundation inputs, selected licence/configuration files or Markdown already inspected by the documentation gate. An additional executable root, language or build manifest refuses with `source_scope_unqualified` until its owning gates and inventory are extended together. These filesystem inputs are ordinary repository checks; domain recovery and filesystem-race qualification retain separate scope.

## Native executable bootstrap

```sh
make native-checks
make native-tools
python tools/bootstrap_native_tools.py --root . --only shellcheck --json
```

`native-checks` verifies all cached originals without network access. `native-tools` explicitly retrieves missing originals; the public command exposes that permission as `--download`. `--only` selects uv, actionlint, Gitleaks or ShellCheck. Reports identify `native_tools` and `local_scaffold_native_tools` and qualify exactly the selected tools.

The Linux x86-64 releases are actionlint 1.7.12, Gitleaks 8.30.1 and ShellCheck 0.11.0. Official HTTPS archive URLs, exact lengths, archive SHA-256, reviewed member names and independent executable identities are frozen in `NATIVE_SOURCES`. Identity is checked before parsing. The selected member is read without extracting received paths; verified executable bytes are staged on the destination filesystem and atomically installed under `.tool-cache/native`.

The first CI installer step runs `python -S tools/bootstrap_native_tools.py --root . --only uv --download --json`, using the selected Python standard library before any development packages exist. Both environment creation and hash-locked installation invoke that verified native uv path; Python auto-downloads are disabled. Installed compatibility checks verify the same native installer before execution. The bootstrap verifies cached executable bytes and does not retry a failed archive or executable digest through another source. No setup-uv action or restored installer cache is used.

Existing invalid, nonexecutable or nonregular destinations are preserved and refused. Downloads have a 15-second socket timeout and a bound on compressed bytes read. Repository hooks verify native identities, and CI installation recipes bootstrap the selected originals before running those hooks. Downloaded tools retain their upstream licences.

## Native quality gates and retained advisories

```sh
python tools/check_native_gate.py --root . --check source_patterns --json
make source-patterns
make credentials
make vulnerabilities
make compatibility
```

The fixed native roles are lint, formatting, strict types, source licences, workflow syntax, workflow static analysis, source patterns, source credentials, dependency vulnerabilities and installed compatibility. Make exposes `lint`, `format-check`, `types`, `source-patterns`, `credentials`, `vulnerabilities`, `workflow-native`, `workflow-static` and `compatibility`; `provenance` also runs REUSE.

Each native-gate report retains the actual native exit and stream digests. Structured audit output is retained in `native_result.report`. Credential scans use the reviewed default-only rule configuration, disable inline allow comments and read only the Git-maintained text cohort. Dependency auditing uses the complete selected hash lock, strict collection and the actual installed graph, with no package mutation.

Bandit scans every maintained Python tool at all severities and confidence levels. Its native exit 1 and nine current advisories remain visible. Qualification binds the complete scan, zero suppression counters, exact warning-bearing source bytes and complete original finding identities. The owned dispositions are:

| Disposition | Reviewed context |
| --- | --- |
| `ELINFRA-SAST-GIT-001` | Literal native Git with fixed argument structure and trusted operator context |
| `ELINFRA-SAST-PROCESS-001` | Deliberate native command API with owned process groups, finite deadlines and no shell |
| `ELINFRA-SAST-NATIVE-001` | Classified HTTPS originals, immutable byte identities and a post-digest internal type invariant |
| `ELINFRA-SAST-WORKFLOW-001` | Literal runner expressions in workflow-policy data |

A missing, new or changed advisory, incomplete scan or changed source requires fresh review. Scanner thresholds and suppression remain unchanged. A qualified advisory disposition is an author-owned source review, not an independent security approval.

## Validation children and complete profile

`processes.execute` receives a literal argument sequence and optional finite standard input. It preserves the actual native exit and original output bytes. Default limits are 60 seconds and 1,048,576 returned bytes per stream. The preflight bounds each native invocation at 120 seconds. Repository-local spools close on exit; a deadline stops the owned process group and reaps its direct child. Spools may grow until the deadline; the byte limit applies to returned output.

```sh
python tools/preflight.py --root . --profile local-scaffold --json
python tools/preflight.py --root . --only repository_metadata --json
```

The full profile requires every declared gate to run and qualify. `--only` is diagnostic: omitted checks remain `not_run` and prevent a complete pass. `--report` atomically writes the complete result inside the repository tool cache. An unsuccessful replacement preserves the prior destination and removes the call's temporary bytes.

`make source-audit` combines source, dependency, licence, credential and workflow checks. `make ci` prepares native tools, runs the complete preflight and then the complete test gate. `make test` discovers the maintained tests and requires 100% executable statement and branch coverage across the tooling and test roots. The retained `test-metadata` and `test-provenance` target names are aliases for that same complete gate. Focused iteration uses named pytest modules. Byte-identical copied implementation fixtures are mapped only from their declared test-cache locations to the canonical tool sources.

## Native interfaces

::: ledger_validation.metadata.verify

::: ledger_validation.metadata.inventory_bytes

::: ledger_validation.metadata_cli.generate_main

::: ledger_validation.metadata_cli.main

::: ledger_validation.inputs.decode_object

::: ledger_validation.inputs.read_object

::: ledger_validation.inputs.read_bytes

::: ledger_validation.inputs.CheckFailure

::: ledger_validation.provenance.verify

::: ledger_validation.provenance.maintained_sources

::: ledger_validation.provenance_cli.main

::: ledger_validation.workflows.verify

::: ledger_validation.workflow_cli.main

::: ledger_validation.dependencies.installed_licence_names

::: ledger_validation.dependencies.verify

::: ledger_validation.dependency_generation.provenance_bytes

::: ledger_validation.dependency_generator_cli.main

::: ledger_validation.dependency_inputs.parse_requirements

::: ledger_validation.dependency_inputs.read_text

::: ledger_validation.dependencies_cli.main

::: ledger_validation.execution.verify

::: ledger_validation.execution.verify_sources

::: ledger_validation.inventory.verify

::: ledger_validation.inventory_cli.main

::: ledger_validation.documentation.Document

::: ledger_validation.documentation.verify

::: ledger_validation.documentation_cli.main

::: ledger_validation.processes.execute

::: ledger_validation.native_tools.NativeSource

::: ledger_validation.native_tools.verify_binary

::: ledger_validation.native_tools.unpack_archive

::: ledger_validation.native_tools.ensure_tool

::: ledger_validation.native_cli.main

::: ledger_validation.native_cli.NativeArguments

::: ledger_validation.native_check_cli.main

::: ledger_validation.native_check_cli.NativeCheckArguments

::: ledger_validation.source_pattern_review.review_report

::: ledger_validation.preflight.read_checker_report

::: ledger_validation.preflight.run_check

::: ledger_validation.preflight.main

::: ledger_validation.preflight.PreflightArguments

::: ledger_validation.preflight_reports.write_report

::: ledger_validation.validation_profile.commands

::: ledger_validation.command.run

::: ledger_validation.command.Arguments

::: ledger_validation.command.ArgumentParser
