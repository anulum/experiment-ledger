# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Verify selected Linux x86-64 native tool archives and executable bytes."""

import hashlib
import io
import os
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import NamedTuple

from .inputs import CheckFailure, read_bytes


class NativeSource(NamedTuple):
    """Immutable selected original download and executable identities.

    Attributes
    ----------
    url : str
        Official versioned HTTPS release archive.
    archive_bytes : int
        Exact original compressed byte count.
    archive_sha256 : str
        Selected official archive digest, checked before parsing.
    binary_bytes : int
        Exact original executable byte count.
    binary_sha256 : str
        Selected executable digest, checked before installation or use.
    member : str
        Reviewed original archive member, read without filesystem extraction.
    """

    url: str
    archive_bytes: int
    archive_sha256: str
    binary_bytes: int
    binary_sha256: str
    member: str


NATIVE_SOURCES = {
    "uv": NativeSource(
        "https://github.com/astral-sh/uv/releases/download/0.12.22/"
        "uv-x86_64-unknown-linux-gnu.tar.gz",
        19916278,
        "b9980552309f09c15172b8be828555e375097f16deb459795ce7bfd200380f0b",
        47991416,
        "96e1603cb62aebb1a804fe9866a5708ee8bba4c39d07202ad29cf256a67366c3",
        "uv-x86_64-unknown-linux-gnu/uv",
    ),
    "actionlint": NativeSource(
        "https://github.com/rhysd/actionlint/releases/download/v1.7.12/"
        "actionlint_1.7.12_linux_amd64.tar.gz",
        2353908,
        "8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8",
        6074530,
        "c872d6db8c6bf83a8eaa704fc93999f027d55dffbc63b8a6abdccb47df5f4cd4",
        "actionlint",
    ),
    "gitleaks": NativeSource(
        "https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/"
        "gitleaks_8.30.1_linux_x64.tar.gz",
        8230402,
        "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb",
        21958840,
        "88f91962aa2f93ac6ab281d553b9e125f5197bbbce38f9f2437f7299c32e5509",
        "gitleaks",
    ),
    "shellcheck": NativeSource(
        "https://github.com/koalaman/shellcheck/releases/download/v0.11.0/"
        "shellcheck-v0.11.0.linux.x86_64.tar.gz",
        3773312,
        "b7af85e41cc99489dcc21d66c6d5f3685138f06d34651e6d34b42ec6d54fe6f6",
        16213136,
        "4da528ddb3a4d1b7b24a59d4e16eb2f5fd960f4bd9a3708a15baddbdf1d5a55b",
        "shellcheck-v0.11.0/shellcheck",
    ),
}


def verify_binary(name: str, raw: bytes) -> None:
    """Require the complete selected native executable bytes.

    Parameters
    ----------
    name : str
        Selected tool name from NATIVE_SOURCES.
    raw : bytes
        Complete actual executable bytes.

    Raises
    ------
    CheckFailure
        When received bytes differ in length or digest from the selected source.
    KeyError
        For an unclassified tool name.
    """
    source = NATIVE_SOURCES[name]
    if len(raw) != source.binary_bytes or hashlib.sha256(raw).hexdigest() != source.binary_sha256:
        raise CheckFailure("native_source_mismatch", name)


def unpack_archive(name: str, raw: bytes) -> bytes:
    """Verify original compressed bytes before reading the one selected archive member.

    Parameters
    ----------
    name : str
        Selected tool and original archive member name.
    raw : bytes
        Complete original compressed release archive.

    Returns
    -------
    bytes
        Complete selected executable, independently verified against its digest.

    Raises
    ------
    CheckFailure
        For an archive or executable identity mismatch. No received path is
        extracted into the filesystem.
    KeyError
        For an unclassified tool name.

    Notes
    -----
    Parsing follows the exact frozen archive digest; this accepts only the selected
    reviewed originals, not arbitrary archives or caller-supplied source policy.
    """
    source = NATIVE_SOURCES[name]
    if len(raw) != source.archive_bytes or hashlib.sha256(raw).hexdigest() != source.archive_sha256:
        raise CheckFailure("native_archive_mismatch", name)
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        stream = archive.extractfile(source.member)
        assert stream is not None
        with stream:
            binary = stream.read(source.binary_bytes + 1)
    verify_binary(name, binary)
    return binary


def ensure_tool(root: Path, name: str, *, download: bool = False) -> None:
    """Verify a cached native tool, optionally downloading a missing selected original.

    Parameters
    ----------
    root : Path
        Actual repository owning the ignored native tool cache.
    name : str
        Selected tool name from NATIVE_SOURCES.
    download : bool
        Explicitly permit retrieval only when the destination does not exist.
        Existing mismatched, nonregular or nonexecutable bytes are refused.

    Raises
    ------
    CheckFailure
        For escaped/nonregular paths, mismatched bytes, a missing unrequested
        download, unavailable HTTPS/cache or failed atomic publication.
    KeyError
        For an unclassified tool name.

    Notes
    -----
    Downloads have a finite socket timeout and read at most one byte beyond
    the original archive length. The caller's ordinary network proxy settings
    apply. The reviewed originals are never executed by this bootstrap.
    """
    root = root.resolve()
    source = NATIVE_SOURCES[name]
    relative = f".tool-cache/native/{name}/{name}"
    destination = root / relative
    if destination.is_symlink() or not destination.resolve().is_relative_to(root):
        raise CheckFailure("native_cache_escape", name)
    if destination.exists():
        verify_binary(name, read_bytes(root, relative, source.binary_bytes))
        if not os.access(destination, os.X_OK):
            raise CheckFailure("native_not_executable", name)
        return
    if not download:
        raise CheckFailure("native_tool_unavailable", name, unavailable=True)
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(source.url, timeout=15) as response:
            binary = unpack_archive(name, response.read(source.archive_bytes + 1))
        with tempfile.TemporaryDirectory(dir=destination.parent) as scratch:
            temporary = Path(scratch) / name
            temporary.write_bytes(binary)
            temporary.chmod(0o755)
            os.replace(temporary, destination)
    except (OSError, urllib.error.URLError) as error:
        raise CheckFailure("native_download_unavailable", name, unavailable=True) from error
