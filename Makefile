# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

PYTHON ?= .venv/bin/python
COVERAGE_FILE ?= $(abspath .tool-cache/coverage/complete/data)
TEST_BASETEMP ?= .tool-cache/tests/complete
export COVERAGE_FILE
export TMPDIR := $(abspath .tool-cache/tmp)
export PRE_COMMIT_HOME := $(abspath .tool-cache/pre-commit)
.NOTPARALLEL:

.PHONY: metadata metadata-inventory provenance workflow-policy dependencies inventory documentation
.PHONY: lint format-check types docs test test-metadata test-provenance
.PHONY: native-tools native-checks preflight source-audit ci source-patterns
.PHONY: credentials vulnerabilities workflow-native workflow-static compatibility dependency-provenance

metadata:
	$(PYTHON) tools/check_repository_metadata.py --root . --json

metadata-inventory:
	@$(PYTHON) tools/generate_capability_inventory.py --root .

provenance:
	$(PYTHON) tools/check_source_provenance.py --root . --json
	$(PYTHON) -m reuse lint

workflow-policy:
	$(PYTHON) tools/check_workflow_policy.py --root . --json

dependencies:
	$(PYTHON) tools/check_dependency_alignment.py --root . --json

dependency-provenance:
	@$(PYTHON) tools/generate_dependency_provenance.py --root .

inventory:
	$(PYTHON) tools/check_repository_inventory.py --root . --json

docs documentation:
	$(PYTHON) tools/check_documentation.py --root . --json

lint:
	$(PYTHON) tools/check_native_gate.py --root . --check source_lint --json

format-check:
	$(PYTHON) tools/check_native_gate.py --root . --check source_format --json

types:
	$(PYTHON) tools/check_native_gate.py --root . --check strict_types --json

source-patterns:
	$(PYTHON) tools/check_native_gate.py --root . --check source_patterns --json

credentials:
	$(PYTHON) tools/check_native_gate.py --root . --check source_credentials --json

vulnerabilities:
	$(PYTHON) tools/check_native_gate.py --root . --check dependency_vulnerabilities --json

workflow-native:
	$(PYTHON) tools/check_native_gate.py --root . --check workflow_syntax --json

workflow-static:
	$(PYTHON) tools/check_native_gate.py --root . --check workflow_static_checks --json

compatibility:
	$(PYTHON) tools/check_native_gate.py --root . --check installed_compatibility --json

native-tools:
	mkdir -p $(TMPDIR)
	$(PYTHON) tools/bootstrap_native_tools.py --root . --download --json

native-checks:
	$(PYTHON) tools/bootstrap_native_tools.py --root . --json

preflight: native-checks
	$(PYTHON) tools/preflight.py --root . --profile local-scaffold --json --report .tool-cache/preflight/result.json

source-audit: native-checks provenance workflow-policy dependencies source-patterns credentials vulnerabilities workflow-native workflow-static

ci: native-tools preflight test

test test-metadata test-provenance:
	mkdir -p $(TMPDIR) $(dir $(COVERAGE_FILE))
	$(PYTHON) -m coverage erase
	nice -n 19 $(PYTHON) -m coverage run --branch --source=tools,tests --parallel-mode -m pytest -p no:pytest_cov -q -n 0 --basetemp=$(TEST_BASETEMP) tests
	$(PYTHON) -m coverage combine $(dir $(COVERAGE_FILE))
	$(PYTHON) -m coverage report --fail-under=100
	$(PYTHON) -m coverage json -o $(dir $(COVERAGE_FILE))result.json
