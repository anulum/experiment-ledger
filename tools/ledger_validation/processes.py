# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Run bounded native checks with owned child groups and repository-local output."""

import contextlib
import os
import signal
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path

from .inputs import CheckFailure


def execute(
    command: Sequence[str],
    *,
    root: Path,
    location: str,
    timeout: float = 60,
    limit: int = 1048576,
    input_bytes: bytes | None = None,
) -> subprocess.CompletedProcess[bytes]:
    """Execute and reap one owned process group with bounded returned output.

    Parameters
    ----------
    command : Sequence[str]
        Native executable and literal arguments; no shell evaluation.
    root : Path
        Actual working repository and owner of temporary output storage.
    location : str
        Fixed caller-selected location used in a refusal finding.
    timeout : float
        Positive wall-clock deadline in seconds.
    limit : int
        Maximum returned bytes per output stream.
    input_bytes : bytes or None
        Optional finite standard input, passed without shell interpretation.

    Returns
    -------
    subprocess.CompletedProcess[bytes]
        Actual native exit and bounded original stdout and stderr.

    Raises
    ------
    ValueError
        For an empty command or nonpositive resource limits.
    CheckFailure
        For unavailable process/cache, a timeout, escaped temporary storage
        or output beyond its declared bound. Timed-out owned groups are
        stopped and their direct child is reaped before the call returns.

    Notes
    -----
    Output spools stay on the repository filesystem and close on every exit.
    This supervises validation children; it does not qualify power loss,
    filesystem races or domain recovery behaviour.
    """
    if not command or timeout <= 0 or limit <= 0:
        raise ValueError("A command and positive resource bounds are required")
    cache = root / ".tool-cache/processes"
    if not cache.resolve().is_relative_to(root.resolve()):
        raise CheckFailure("child_cache_escape", location)
    try:
        cache.mkdir(parents=True, exist_ok=True)
        with (
            tempfile.TemporaryFile(dir=cache) as stdout,
            tempfile.TemporaryFile(dir=cache) as stderr,
            subprocess.Popen(
                command,
                cwd=root,
                stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            ) as process,
        ):
            try:
                process.communicate(input=input_bytes, timeout=timeout)
            except subprocess.TimeoutExpired as error:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
                raise CheckFailure("child_timeout", location, unavailable=True) from error
            stdout.seek(0)
            stderr.seek(0)
            output, errors = stdout.read(limit + 1), stderr.read(limit + 1)
            if len(output) > limit or len(errors) > limit:
                raise CheckFailure("child_output_too_large", location)
            return subprocess.CompletedProcess(command, process.returncode, output, errors)
    except OSError as error:
        raise CheckFailure("child_unavailable", location, unavailable=True) from error
