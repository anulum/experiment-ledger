# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Read bounded JSON repository declarations without changing their bytes."""

import json
from pathlib import Path
from typing import cast

type Json = None | bool | int | float | str | list[Json] | dict[str, Json]


class CheckFailure(Exception):
    """An authored refusal or unavailable-input result.

    Attributes
    ----------
    code : str
        Fixed finding identifier selected by the checker.
    location : str
        Fixed repository-relative input name.
    exit_code : int
        Two for refused content, three for an unavailable input.
    """

    def __init__(self, code: str, location: str, *, unavailable: bool = False) -> None:
        """Retain the finding without exposing an underlying exception.

        Parameters
        ----------
        code : str
            Authored finding identifier.
        location : str
            Repository-relative input location.
        unavailable : bool
            Whether the input could not be read.
        """
        super().__init__(code)
        self.code = code
        self.location = location
        self.exit_code = 3 if unavailable else 2


def read_bytes(root: Path, name: str, limit: int) -> bytes:
    """Read at most one byte beyond a declared input limit.

    Parameters
    ----------
    root : Path
        Repository whose fixed input is being checked.
    name : str
        Checker-selected repository-relative file name.
    limit : int
        Maximum admitted byte count.

    Returns
    -------
    bytes
        Complete original bytes when within the limit.

    Raises
    ------
    CheckFailure
        When the file is unavailable or exceeds its declared bound.
    """
    try:
        with (root / name).open("rb") as stream:
            raw = stream.read(limit + 1)
    except OSError as error:
        raise CheckFailure("input_unavailable", name, unavailable=True) from error
    if len(raw) > limit:
        raise CheckFailure("input_too_large", name)
    return raw


def _object_pairs(pairs: list[tuple[str, Json]]) -> dict[str, Json]:
    """Decode one JSON object while refusing duplicate member names.

    Parameters
    ----------
    pairs : list[tuple[str, Json]]
        Original ordered members received from the JSON decoder.

    Returns
    -------
    dict[str, Json]
        Complete object with distinct member names.

    Raises
    ------
    ValueError
        When a member name is repeated.
    """
    result: dict[str, Json] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON member.")
        result[key] = value
    return result


def _nonfinite(value: str) -> None:
    """Refuse a JSON parser extension for a nonfinite number.

    Parameters
    ----------
    value : str
        Received nonfinite literal, which is never emitted.

    Raises
    ------
    ValueError
        Always, because JSON declarations require finite numbers.
    """
    raise ValueError("Nonfinite JSON value.")


def read_object(root: Path, name: str, limit: int = 65536) -> tuple[bytes, dict[str, Json]]:
    """Decode one bounded UTF-8 JSON object with exact member identities.

    Parameters
    ----------
    root : Path
        Repository supplying the declaration.
    name : str
        Fixed repository-relative declaration name.
    limit : int
        Maximum admitted original byte count.

    Returns
    -------
    tuple[bytes, dict[str, Json]]
        Original bytes and the decoded object.

    Raises
    ------
    CheckFailure
        For unavailable, oversized, malformed or non-object inputs, duplicate
        members, nonfinite numbers, excessive nesting or invalid Unicode.
    """
    raw = read_bytes(root, name, limit)
    return raw, decode_object(raw, name, limit)


def decode_object(raw: bytes, name: str, limit: int = 65536) -> dict[str, Json]:
    """Decode bounded original UTF-8 object bytes with exact JSON member semantics.

    Parameters
    ----------
    raw : bytes
        Complete original received bytes, preserved without reserialization.
    name : str
        Caller-selected fixed diagnostic location.
    limit : int
        Maximum admitted original byte count.

    Returns
    -------
    dict[str, Json]
        Complete object with unique members, finite numbers and valid Unicode.

    Raises
    ------
    CheckFailure
        For oversized, malformed or non-object JSON, duplicate members,
        nonfinite numbers, excessive nesting or invalid Unicode.
    """
    if len(raw) > limit:
        raise CheckFailure("input_too_large", name)
    try:
        value = cast(
            Json,
            json.loads(
                raw.decode("utf-8"),
                object_pairs_hook=_object_pairs,
                parse_constant=_nonfinite,
            ),
        )
        json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, RecursionError) as error:
        raise CheckFailure("input_invalid", name) from error
    if not isinstance(value, dict):
        raise CheckFailure("input_invalid", name)
    return value
