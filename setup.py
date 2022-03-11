#!/usr/bin/env python
from os.path import join
from setuptools import setup, find_packages


def get_version():
    with open(join("tinytag", "__init__.py")) as f:
        version_line = next(line for line in f if line.startswith("__version__ ="))
        return version_line.split("=")[1].strip().strip("\"'")


setup(name="tinytag",
      version=get_version(),
      packages=find_packages())
