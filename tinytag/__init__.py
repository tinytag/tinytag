#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from .tinytag import TinyTag, TinyTagException, ID3, Ogg, Wave, Flac  # noqa: F401


__version__ = '1.9.0'


if __name__ == '__main__':
    print(TinyTag.get(sys.argv[1]))
