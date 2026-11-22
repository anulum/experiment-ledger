# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Bind visible native source-pattern advisories to explicit reviewed source contexts."""

import hashlib
import json
from pathlib import Path

from .inputs import CheckFailure, Json, decode_object, read_bytes
from .provenance import maintained_sources

SOURCE_DISPOSITIONS = {
    "tools/ledger_validation/provenance.py": (
        "0f61acec653869cea1468e4a7329a5e6c555e947467940364aba3169414679e2",
        "ELINFRA-SAST-GIT-001",
    ),
    "tools/ledger_validation/processes.py": (
        "ea87d324166c72cd8aa3e89c44edb1f2cbf92c0922403fa992c454fd9610c434",
        "ELINFRA-SAST-PROCESS-001",
    ),
    "tools/ledger_validation/native_tools.py": (
        "8aefc7cab741d951354470230b566c2759f6903837d9c506630c09a014a9eb4a",
        "ELINFRA-SAST-NATIVE-001",
    ),
    "tools/ledger_validation/workflows.py": (
        "534ce8483be7dbd557fa4c05c2c216cda502975011848656dc34543ca003473b",
        "ELINFRA-SAST-WORKFLOW-001",
    ),
}

FINDING_DIGESTS = frozenset(
    {
        "0244c490886e17b37c1ba1d5e7c54598231d306530502d7a9b18623ba79abbae",  # B101 native_tools.py:146
        "ec6fc0b816e99c500b027ef4d47553aa027a76052edc0b73a1054006e539e182",  # B310 native_tools.py:195
        "9264e6ae37c93e78ac93aa746bf21fb14496509deea522d3f3bc4f3a60277b31",  # B404 processes.py:14
        "149bd792f74b55aa2344d2b2148250a46a8d02557a3354446352cfa1fea37523",  # B603 processes.py:78
        "6925020b56748a2f483cb4c64ba8fe298ee85618b763a4a72d8d803007aee4fc",  # B404 provenance.py:13
        "d83b92c68ebd779e3e7ce8eb8f8b72f2e19454911865daf807b3c5651be3777d",  # B607 provenance.py:65
        "ddff81084988918312211a5340414e967b3435fa6f6d5ca9763c0570210abd14",  # B603 provenance.py:65
        "12aafddd0a64e6528b131a5e13cd722c37836e372d41aa87c8de07776fd1c0dd",  # B105 workflows.py:136
        "fc1c1d896fd856659a72a3c28d4d2321d8840721b43f80905163a345c17847c1",  # B105 workflows.py:137
    }
)


def review_report(root: Path, stdout: bytes, *, native_exit: int) -> dict[str, Json]:
    """Qualify complete native advisories against exact source and finding identities.

    Parameters
    ----------
    root : Path
        Actual Git repository supplying all maintained Python tools.
    stdout : bytes
        Complete original Bandit JSON output from the unfiltered native scan.
    native_exit : int
        Actual native scanner exit, preserved by the caller in its outcome.

    Returns
    -------
    dict[str, Json]
        Original complete native report, including every retained advisory.

    Raises
    ------
    CheckFailure
        For invalid native outcome/report, incomplete scan, suppression,
        missing/changed source, or missing/new/changed finding identities.

    Notes
    -----
    This qualifies explicit author-owned advisory dispositions, not zero
    native warnings or independent security approval. No severity threshold,
    scanner suppression or absent finding can establish acceptance. Source or
    finding changes require a fresh owned review and policy update.
    """
    if native_exit not in (0, 1):
        raise CheckFailure("source_pattern_report_invalid", "bandit")
    report = decode_object(stdout, "bandit_report", 1048576)
    if set(report) != {"errors", "generated_at", "metrics", "results"} or report["errors"] != []:
        raise CheckFailure("source_pattern_report_invalid", "bandit")
    metrics, results = report["metrics"], report["results"]
    if not isinstance(metrics, dict) or not isinstance(results, list):
        raise CheckFailure("source_pattern_report_invalid", "bandit")
    totals = metrics.get("_totals")
    if not isinstance(totals, dict) or any(
        type(totals.get(key)) is not int or totals[key] != 0 for key in ("nosec", "skipped_tests")
    ):
        raise CheckFailure("source_pattern_scan_incomplete", "bandit")
    sources = {
        name
        for name in maintained_sources(root)
        if name.startswith("tools/") and name.endswith(".py")
    }
    if set(metrics) - {"_totals"} != sources:
        raise CheckFailure("source_pattern_scan_incomplete", "bandit")
    for name, (digest, _) in SOURCE_DISPOSITIONS.items():
        if hashlib.sha256(read_bytes(root, name, 1048576)).hexdigest() != digest:
            raise CheckFailure("source_pattern_source_mismatch", name)
    fingerprints = {
        hashlib.sha256(json.dumps(item, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        for item in results
    }
    if native_exit != 1 or len(results) != len(FINDING_DIGESTS) or fingerprints != FINDING_DIGESTS:
        raise CheckFailure("source_pattern_findings_mismatch", "bandit")
    return report
