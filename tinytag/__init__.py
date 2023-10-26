#!/usr/bin/python
# -*- coding: utf-8 -*-

__version__ = '1.10.1'

import sys
from .tinytag import TinyTag, TinyTagException, ID3, Ogg, Wave, Flac  # noqa: F401


if __name__ == '__main__':
    print(TinyTag.get(sys.argv[1]))
