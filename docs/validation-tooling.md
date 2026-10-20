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

The repository metadata declaration checker is available:

```sh
python tools/check_repository_metadata.py --root . --json
make metadata
```

It checks the complete local metadata against the selected project policy, binds the exact schema bytes, checks the development lock digest and verifies the derived capability inventory against the original metadata bytes. Capabilities, claims, qualified formats and domain dependencies must remain empty. The four planned format names are declarations rather than registered or supported formats.

JSON declarations are limited to 65,536 original bytes; the lock is limited to 1,048,576 bytes. Duplicate members, nonfinite values, invalid Unicode and non-object declarations refuse. A deeply nested valid JSON object still needs to match the complete metadata contract. The checker preserves its inputs and does not publish a report file.

| Exit | Meaning |
| --- | --- |
| 0 | The complete declarations and byte bindings match. |
| 2 | Received content or its source correspondence is refused. |
| 3 | A required input is unavailable. |
| 4 | Command arguments are invalid. |

Without `--json`, the command prints the human-readable status. JSON output carries the check name, declaration scope, status, native exit and fixed finding identifiers with repository-relative input locations. Help is available through `--help`.

The checker qualifies declarations. Actual interpreter, installed dependency graph and executable provenance checks remain mandatory in the separate dependency-alignment gate. This command does not establish a finished scaffold, Common verification, scientific evidence, accessibility or a Ledger capability.

`make lint`, `make format-check` and `make types` cover the maintained tooling and test roots. `make test-metadata` exercises the actual declaration CLI and reports statement and branch coverage across the current tooling and test roots. Both test-metadata and test-provenance currently exercise the two named owning test modules because the checks share CLI/report code. The whole maintained tooling/test denominator and the 100% floor are retained. Other infrastructure validators and their full preflight and workflow wiring are still being implemented; unavailable checks do not pass.

## Maintained-source provenance

```sh
python tools/check_source_provenance.py --root . --json
make provenance
make test-provenance
```

This command uses native Git to enrol tracked files, including deleted tracked paths, and nonignored untracked files. It checks complete project-specific seven-line notices, conflicting SPDX identifiers, strictly parsed JSON objects and their exact nine-line sidecars. It preserves the selected original AGPL licence texts, binary asset identities and REUSE annotation policy. Those originals are compared with fixed selected-source digests, rather than accepting any file carrying our own notice.

The command reads each text source within 1,048,576 bytes; source JSON shares this bound and sidecars are limited to 8,192 bytes. Each selected binary asset is bounded by its original exact byte length and digest. The separate metadata-declaration checker retains its 65,536 byte limit. A missing or non-enrolled required source/sidecar, or unavailable Git dependency yields unavailable (exit 3). Invalid received content yields refused (exit 2). Machine reports use source_provenance and local_scaffold_source_provenance; argument/help exits and human reporting follow the table above.

Additional original or third-party material needs an explicit source-policy update that preserves its ownership. The checker never rewrites licence files. The Make provenance target and local hooks additionally run native REUSE classification over the actual source cohort. Ignored development environments, private plans and generated files are outside the Git-maintained cohort. Their exclusion is not proof of privacy, package contents, filesystem containment or a complete inventory audit. Installed dependency qualification, native REUSE results and the remaining gates retain their own scope.

An existing top-level `SPDX-License-Identifier` or `spdx_license_identifier` in JSON must agree with its ownership sidecar. Both spellings are checked when both are present. Nested component licences retain their separate meaning. The checker adds no ownership fields and preserves the received bytes.

## Native validation children

The `ledger_validation.processes.execute` API runs a literal argument sequence in a selected repository, without a shell. It returns the original native exit and output bytes. Callers can provide finite standard input, a positive deadline and a returned-output bound; the defaults are 60 seconds and 1,048,576 bytes per stream.

Output spools live under the repository's ignored `.tool-cache/processes` directory and close on every exit. An unavailable executable or cache yields unavailable (exit 3). An escaping cache or excessive returned output yields refused (exit 2). A deadline stops the owned process group and reaps its direct child before reporting unavailable. Temporary spools may grow until that deadline; the byte limit applies to returned output.

The process API is exercised with actual metadata, native Git and MkDocs help commands. It supervises repository validation and does not establish domain recovery or filesystem-race behaviour. The full preflight profile and additional guards remain under construction.

## Native executable bootstrap

```sh
make native-checks
make native-tools
python tools/bootstrap_native_tools.py --root . --only actionlint --json
```

`native-checks` verifies both cached originals without network access. `native-tools` explicitly retrieves missing originals. The public command accepts `--download` for that retrieval and `--only actionlint` or `--only gitleaks` for a selected check. Each JSON report identifies `native_tools` and `local_scaffold_native_tools`; exits follow the table above. Verification is scoped to the selected tools.

The selected Linux x86-64 releases are actionlint 1.7.12 and Gitleaks 8.30.1. Their official HTTPS archive URLs, exact lengths, SHA-256 archive digests and independent executable digests are frozen in `ledger_validation.native_tools.NATIVE_SOURCES`. Archive identity is checked before parsing; the single selected member is read without extracting received paths. Installation stages verified bytes on the destination filesystem, sets executable mode and atomically publishes inside `.tool-cache/native`. Existing invalid, nonexecutable or nonregular destinations are preserved and refused. A download has a 15-second socket timeout and a bound on the compressed bytes read; an unavailable connection never produces a passing tool.

These binaries support repository validation. The bootstrap verifies their identities without executing them. Owning checks separately exercise their native interfaces. Repository hooks verify both identities; CI installation recipes bootstrap them before running those hooks.

## Native interfaces

::: ledger_validation.metadata.verify

::: ledger_validation.metadata_cli.main

::: ledger_validation.inputs.read_object

::: ledger_validation.inputs.read_bytes

::: ledger_validation.inputs.CheckFailure

::: ledger_validation.provenance.verify

::: ledger_validation.provenance.maintained_sources

::: ledger_validation.provenance_cli.main

::: ledger_validation.command.run

::: ledger_validation.command.Arguments

::: ledger_validation.command.ArgumentParser

::: ledger_validation.processes.execute

::: ledger_validation.native_tools.NativeSource

::: ledger_validation.native_tools.verify_binary

::: ledger_validation.native_tools.unpack_archive

::: ledger_validation.native_tools.ensure_tool

::: ledger_validation.native_cli.main

::: ledger_validation.native_cli.NativeArguments
