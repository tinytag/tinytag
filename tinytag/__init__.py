#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from .tinytag import TinyTag


__version__ = '1.8.0'


if __name__ == '__main__':
    print(TinyTag.get(sys.argv[1]))
