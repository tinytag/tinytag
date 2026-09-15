#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 tinytag Contributors
# SPDX-License-Identifier: MIT

# pylint: disable=missing-module-docstring

import os
import sys

BASE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..")
)
NEWS_FILE_PATH = os.path.join(BASE_PATH, "README.md")


def extract_release_notes():
    """Extracts release notes for the specified version from README.md."""

    if len(sys.argv) < 2:
        print("No version provided")
        sys.exit(1)

    output = bytearray()
    version = sys.argv[1]
    reading_notes = False

    with open(NEWS_FILE_PATH, "rb") as file_handle:
        for line in file_handle:
            if reading_notes:
                if line.startswith(b"### "):
                    break

                output += line
                continue

            if line.startswith(f"### {version} ".encode()):
                reading_notes = True

    print(output.decode().strip())


if __name__ == "__main__":
    extract_release_notes()
