#!/usr/bin/env python
# pylint: disable=missing-function-docstring,missing-module-docstring

import subprocess
import sys


def release_package():
    # Run tests
    subprocess.check_call([sys.executable, "-m", "pycodestyle"])
    subprocess.check_call([sys.executable, "-m", "pylint", "--recursive=y", "."])
    subprocess.check_call([sys.executable, "-m", "pytest"])

    # Prepare source distribution and wheel
    subprocess.check_call([sys.executable, "-m", "build", "--sdist", "--wheel"])

    # Upload package to PyPi
    subprocess.check_call([sys.executable, "-m", "twine", "upload", "dist/*"])


if __name__ == "__main__":
    release_package()
