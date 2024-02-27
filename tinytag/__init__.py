#!/usr/bin/python
# pylint: disable=missing-module-docstring

import sys
from .tinytag import TinyTag, TinyTagException  # noqa: F401


if __name__ == '__main__':
    print(TinyTag.get(sys.argv[1]))
