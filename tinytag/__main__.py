#!/usr/bin/python
# -*- coding: utf-8 -*-
from tinytag import TinyTag
import sys

if __name__ == '__main__':
    print(TinyTag.get(sys.argv[1]))