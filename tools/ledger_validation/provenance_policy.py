# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Selected original licence, asset and project notice identities."""

HEADER = [
    "SPDX-" + "License-Identifier: AGPL-3.0-or-later",
    "Commercial license available",
    "© Concepts 1996–2026 Miroslav Šotek. All rights reserved.",
    "© Code 2020–2026 Miroslav Šotek. All rights reserved.",
    "ORCID: 0009-0009-3560-0851",
    "Contact: www.anulum.li | protoscience@anulum.li",
    "EXPERIMENT-LEDGER — repository identity and validation foundation",
]
SIDECAR = (
    "\n".join(
        [
            *HEADER,
            "SPDX-"
            + "FileCopyrightText: 1996-2026 Miroslav Šotek <protoscience@anulum.li> (concepts)",
            "SPDX-" + "FileCopyrightText: 2020-2026 Miroslav Šotek <protoscience@anulum.li> (code)",
        ]
    )
    + "\n"
).encode("utf-8")

LICENCE_SHA256 = "d8a6cc31abc16b6748c7a21f21611f5a1ec33f67d22ca23d7da1c19b95496bee"
REUSE_SHA256 = "0d1dee88410dcdcf327acbd1ff3e230953297574cdf56211b2e405f4943cf477"
BINARY_SOURCES = {
    "docs/assets/anulum_logo_company.jpg": "d98a731a2b4b3b8880979d2e2f2c5cb722cc45d3f75b988e81c301902c7d1143",
    "docs/assets/anulum_logo.png": "fe4b3b24226e87045d4aac09284f30ee8a83bd95f9af0509272a063e284067d3",
    "docs/assets/fortis_studio_logo.jpg": "844c5d764c8ad0a030e8f7b83c7e878bb4ebec42ea6e40223f65f344769568c0",
}

BINARY_LENGTHS = {
    "docs/assets/anulum_logo_company.jpg": 718628,
    "docs/assets/anulum_logo.png": 1132189,
    "docs/assets/fortis_studio_logo.jpg": 46715,
}
