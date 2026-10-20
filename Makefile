# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

PYTHON ?= .venv/bin/python
COVERAGE_FILE ?= .tool-cache/coverage/metadata/data
TEST_BASETEMP ?= .tool-cache/tests/metadata
export COVERAGE_FILE

.PHONY: metadata provenance lint format-check types docs test-metadata test-provenance

metadata:
	$(PYTHON) tools/check_repository_metadata.py --root . --json

provenance:
	$(PYTHON) tools/check_source_provenance.py --root . --json
	$(PYTHON) -m reuse lint

lint:
	$(PYTHON) -m ruff check --no-respect-gitignore tools tests

format-check:
	$(PYTHON) -m ruff format --check --no-respect-gitignore tools tests

types:
	$(PYTHON) -m mypy --strict tools tests

docs:
	$(PYTHON) -m mkdocs build --strict

test-metadata test-provenance:
	mkdir -p .tool-cache/tmp $(dir $(COVERAGE_FILE))
	$(PYTHON) -m coverage erase
	TMPDIR=$(abspath .tool-cache/tmp) nice -n 19 $(PYTHON) -m coverage run --branch --source=tools,tests --parallel-mode -m pytest -p no:pytest_cov -q -n 0 --basetemp=$(TEST_BASETEMP) tests/test_repository_metadata.py tests/test_source_provenance.py
	$(PYTHON) -m coverage combine $(dir $(COVERAGE_FILE))
	$(PYTHON) -m coverage report --fail-under=100
	$(PYTHON) -m coverage json -o .tool-cache/coverage/metadata/result.json
