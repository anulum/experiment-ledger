<!--
SPDX-License-Identifier: AGPL-3.0-or-later
Commercial license available
© Concepts 1996–2026 Miroslav Šotek. All rights reserved.
© Code 2020–2026 Miroslav Šotek. All rights reserved.
ORCID: 0009-0009-3560-0851
Contact: www.anulum.li | protoscience@anulum.li
EXPERIMENT-LEDGER — repository identity and validation foundation
-->

# Contributing

The repository foundation is under construction. The local validation commands are described in [validation tooling](docs/validation-tooling.md); complete foundation acceptance and any distributable Ledger package remain unfinished. Read [the architecture](docs/ARCHITECTURE.md) and [validation scope](VALIDATION.md) before proposing implementation.

Work is local-first on main. Preserve existing tracked, staged and untracked material. Publication and release are separate actions. Keep private plans, research inputs, credentials and session records outside public source.

Development requirements describe validation tooling, not domain dependencies. The selected Python line is 3.13, with the exact patch and complete development lock bound in repository metadata. New environments must use uv and a shared hardlink cache on the same filesystem. Do not install by copied package trees or rebuild an environment used by another process.

The tooling target is Linux x86-64 with Python 3.13.16 and uv 0.13.4. Use the selected Python to verify the native uv installer before creating an isolated environment. Install the complete hash lock using hardlinks, then bootstrap the remaining selected native originals:

```sh
mkdir -p .tool-cache/uv .tool-cache/tmp
python3.13 -S tools/bootstrap_native_tools.py --root . --only uv --download --json
.tool-cache/native/uv/uv venv --python 3.13.16 --no-python-downloads .venv
UV_CACHE_DIR="$PWD/.tool-cache/uv" UV_LINK_MODE=hardlink .tool-cache/native/uv/uv pip sync --python .venv/bin/python --require-hashes --build-constraints requirements-dev.txt requirements-dev.txt
make native-tools
```

Use named pytest modules while developing. `make test` runs the complete tooling/test denominator with the full coverage floor; `make ci` also runs the complete profile. Reviewed execution configuration and source-pattern dispositions must be updated with their corresponding source review when those inputs change.

Python code, tests and tooling require strict typing, native NumPy-style docstrings, Ruff and meaningful full statement and branch coverage for the maintained scope. Rust implementation requires native formatting, strict Clippy, tests and documentation. Both languages must preserve the complete storage and consumer semantics; a Python proxy is not Rust parity.

A contribution must be reachable through its real public surface and include relevant integration, failure, documentation and reproducibility evidence. Do not add placeholder APIs, dormant crates, unearned badges or successful results for unexecuted checks.

Report security-sensitive concerns privately as described in [SECURITY.md](SECURITY.md). By contributing, you agree to the [code of conduct](CODE_OF_CONDUCT.md) and provide material you have the right to license under the repository licence.
