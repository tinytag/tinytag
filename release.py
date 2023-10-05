#!/usr/bin/env python

import subprocess
import sys


def release_package():
    # Run tests
    subprocess.check_call([sys.executable, "-m", "flake8"])
    subprocess.check_call([sys.executable, "-m", "pytest"])

    # Prepare source distribution and wheel
    subprocess.check_call([sys.executable, "-m", "build", "--sdist", "--wheel"])

    # Upload package to PyPi
    subprocess.check_call([sys.executable, "-m", "twine", "upload", "dist/*"])


if __name__ == "__main__":
    release_package()
